from flask import Flask, render_template, request, session, flash
import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import csv
import warnings
import requests
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

app = Flask(__name__)
app.secret_key = 'ENTER YOUR OPEN WHEATHER API'  # api secret key

# Print pandas version for debugging
print(f"Current pandas version: {pd.__version__}")

# Load pickle files with error handling
def load_pickle(file_path, use_pandas=False, critical=True):
    try:
        if use_pandas:
            return pd.read_pickle(file_path)
        else:
            with open(file_path, 'rb') as f:
                return pickle.load(f)
    except AttributeError as e:
        print(f"Failed to load {file_path}: {e}")
        if ('_unpickle_block' in str(e) or 'new_block' in str(e)) and use_pandas:
            print(f"Recreating {file_path} from city1_day.csv (assuming pandas DataFrame)...")
            pest = pd.read_csv(r'city_air\city1_day.csv')
            df = pest.copy()
            def preprocessing(df):
                print(f"Columns before preprocessing: {df.columns.tolist()}")
                print("First few rows of the dataset:")
                print(df.head())
                indian_cities = [
                    'Ahmedabad', 'Aizawl', 'Amaravati', 'Amritsar', 'Bengaluru', 'Bhopal', 'Brajrajnagar',
                    'Chandigarh', 'Chennai', 'Coimbatore', 'Delhi', 'Ernakulam', 'Gurugram', 'Guwahati',
                    'Hyderabad', 'Jaipur', 'Jorapokhar', 'Kochi', 'Kolkata', 'Lucknow', 'Mumbai', 'Patna',
                    'Shillong', 'Talcher', 'Thiruvananthapuram', 'Visakhapatnam', 'Nagaon', 'Silchar', 'Byrnihat'
                ]
                df = df[df['city'].isin(indian_cities)]
                print(f"After filtering for Indian cities, df shape: {df.shape}")
                df = df.rename(columns={'city': 'City', 'last_update': 'Date', 'OZONE': 'O3'})
                df_pivot = df.pivot_table(
                    index=['City', 'Date', 'station', 'country', 'state', 'latitude', 'longitude'],
                    columns='pollutant_id',
                    values='pollutant_avg',
                    aggfunc='first'
                ).reset_index()
                print(f"Columns after pivoting: {df_pivot.columns.tolist()}")
                print("First few rows after pivoting:")
                print(df_pivot.head())
                if 'OZONE' in df_pivot.columns:
                    df_pivot = df_pivot.rename(columns={'OZONE': 'O3'})
                required_pollutants = ['PM2.5', 'PM10', 'NO2', 'O3', 'CO', 'SO2']
                missing_pollutants = [p for p in required_pollutants if p not in df_pivot.columns]
                if missing_pollutants:
                    print(f"Warning: The following pollutant columns are missing: {missing_pollutants}")
                    df_pivot['AQI'] = np.nan
                    df_pivot['AQI_Bucket'] = np.nan
                else:
                    def calculate_sub_index(concentration, bp_lo, bp_hi, i_lo, i_hi):
                        if pd.isna(concentration):
                            return None
                        concentration = float(concentration)
                        if concentration <= bp_lo:
                            return i_lo
                        if concentration >= bp_hi:
                            return i_hi
                        return ((concentration - bp_lo) / (bp_hi - bp_lo)) * (i_hi - i_lo) + i_lo

                    breakpoints = {
                        'PM2.5': [(0, 30, 0, 50), (31, 60, 51, 100), (61, 90, 101, 200), (91, 120, 201, 300), (121, 250, 301, 400), (251, float('inf'), 401, 500)],
                        'PM10': [(0, 50, 0, 50), (51, 100, 51, 100), (101, 250, 101, 200), (251, 350, 201, 300), (351, 430, 301, 400), (431, float('inf'), 401, 500)],
                        'NO2': [(0, 40, 0, 50), (41, 80, 51, 100), (81, 180, 101, 200), (181, 280, 201, 300), (281, 400, 301, 400), (401, float('inf'), 401, 500)],
                        'O3': [(0, 50, 0, 50), (51, 100, 51, 100), (101, 168, 101, 200), (169, 208, 201, 300), (209, 748, 301, 400), (749, float('inf'), 401, 500)],
                        'CO': [(0, 1.0, 0, 50), (1.1, 2.0, 51, 100), (2.1, 10.0, 101, 200), (10.1, 17.0, 201, 300), (17.1, 34.0, 301, 400), (34.1, float('inf'), 401, 500)],
                        'SO2': [(0, 40, 0, 50), (41, 80, 51, 100), (81, 380, 101, 200), (381, 800, 201, 300), (801, 1600, 301, 400), (1601, float('inf'), 401, 500)]
                    }

                    sub_indices = []
                    for pollutant in required_pollutants:
                        if pollutant in df_pivot.columns:
                            df_pivot[f'{pollutant}_sub_index'] = df_pivot[pollutant].apply(
                                lambda x: None if pd.isna(x) else max(
                                    [sub_index for sub_index in [calculate_sub_index(x, bp_lo, bp_hi, i_lo, i_hi) for bp_lo, bp_hi, i_lo, i_hi in breakpoints[pollutant]] if sub_index is not None],
                                    default=None
                                )
                            )
                            sub_indices.append(f'{pollutant}_sub_index')

                    if sub_indices:
                        df_pivot['AQI'] = df_pivot[sub_indices].max(axis=1)
                    else:
                        df_pivot['AQI'] = np.nan

                    def assign_aqi_bucket(aqi):
                        try:
                            aqi = float(aqi)
                            if aqi <= 50: return 'Good'
                            elif aqi <= 100: return 'Satisfactory'
                            elif aqi <= 200: return 'Moderate'
                            elif aqi <= 300: return 'Poor'
                            elif aqi <= 400: return 'Very Poor'
                            else: return 'Severe'
                        except (ValueError, TypeError):
                            return None

                    df_pivot['AQI_Bucket'] = df_pivot['AQI'].apply(assign_aqi_bucket)
                    df_pivot = df_pivot.drop(columns=sub_indices, errors='ignore')

                expected_columns = ['City', 'Date', 'station', 'PM2.5', 'PM10', 'NO', 'NO2', 'NOx', 'NH3', 'CO', 'SO2', 'O3', 'Benzene', 'Toluene', 'AQI', 'AQI_Bucket', 'Year', 'Month']
                for col in expected_columns:
                    if col not in df_pivot.columns:
                        df_pivot[col] = np.nan
                df_pivot['Year'] = np.nan
                df_pivot['Month'] = np.nan
                df_pivot = df_pivot[expected_columns]
                return df_pivot
            data = preprocessing(df)
            data.to_pickle(file_path)
            print(f"Recreated {file_path} successfully.")
            return data
        if not critical:
            print(f"Skipping non-critical file {file_path}...")
            return None
        raise

try:
    model = load_pickle('model.pkl', critical=False)
    pest_model = load_pickle('classifier.pkl', critical=False)
    pest_data = load_pickle('index.pkl', use_pandas=True, critical=True)
    pest_solution = load_pickle('solution.pkl', use_pandas=True, critical=False)
    crop_rec = load_pickle('crop.pkl', use_pandas=True, critical=False)
    fertile = load_pickle('soil.pkl', critical=False)
    pestTable = load_pickle('pesttable.pkl', use_pandas=True, critical=False)
    pestTable2 = load_pickle('pesttable2.pkl', use_pandas=True, critical=False)
    pestTable3 = load_pickle('pesttable3.pkl', use_pandas=True, critical=False)
    pestTable4 = load_pickle('pesttable4.pkl', use_pandas=True, critical=False)
    modelFor = load_pickle('tree_gridcv.pkl', critical=True)
except Exception as e:
    print(f"Error loading pickle files: {e}")
    raise

# Load and preprocess air quality data
print("Loading city1_day.csv...")
pest = pd.read_csv(r'city_air\city1_day.csv')
df = pest.copy()

def preprocessing(df):
    print(f"Columns before preprocessing: {df.columns.tolist()}")
    print("First few rows of the dataset:")
    print(df.head())
    indian_cities = [
        'Ahmedabad', 'Aizawl', 'Amaravati', 'Amritsar', 'Bengaluru', 'Bhopal', 'Brajrajnagar',
        'Chandigarh', 'Chennai', 'Coimbatore', 'Delhi', 'Ernakulam', 'Gurugram', 'Guwahati',
        'Hyderabad', 'Jaipur', 'Jorapokhar', 'Kochi', 'Kolkata', 'Lucknow', 'Mumbai', 'Patna',
        'Shillong', 'Talcher', 'Thiruvananthapuram', 'Visakhapatnam', 'Nagaon', 'Silchar', 'Byrnihat'
    ]
    df = df[df['city'].isin(indian_cities)]
    print(f"After filtering for Indian cities, df shape: {df.shape}")
    df = df.rename(columns={'city': 'City', 'last_update': 'Date', 'OZONE': 'O3'})
    df_pivot = df.pivot_table(
        index=['City', 'Date', 'station', 'country', 'state', 'latitude', 'longitude'],
        columns='pollutant_id',
        values='pollutant_avg',
        aggfunc='first'
    ).reset_index()
    print(f"Columns after pivoting: {df_pivot.columns.tolist()}")
    print("First few rows after pivoting:")
    print(df_pivot.head())
    if 'OZONE' in df_pivot.columns:
        df_pivot = df_pivot.rename(columns={'OZONE': 'O3'})
    required_pollutants = ['PM2.5', 'PM10', 'NO2', 'O3', 'CO', 'SO2']
    missing_pollutants = [p for p in required_pollutants if p not in df_pivot.columns]
    if missing_pollutants:
        print(f"Warning: The following pollutant columns are missing: {missing_pollutants}")
        df_pivot['AQI'] = np.nan
        df_pivot['AQI_Bucket'] = np.nan
    else:
        def calculate_sub_index(concentration, bp_lo, bp_hi, i_lo, i_hi):
            if pd.isna(concentration):
                return None
            concentration = float(concentration)
            if concentration <= bp_lo:
                return i_lo
            if concentration >= bp_hi:
                return i_hi
            return ((concentration - bp_lo) / (bp_hi - bp_lo)) * (i_hi - i_lo) + i_lo

        breakpoints = {
            'PM2.5': [(0, 30, 0, 50), (31, 60, 51, 100), (61, 90, 101, 200), (91, 120, 201, 300), (121, 250, 301, 400), (251, float('inf'), 401, 500)],
            'PM10': [(0, 50, 0, 50), (51, 100, 51, 100), (101, 250, 101, 200), (251, 350, 201, 300), (351, 430, 301, 400), (431, float('inf'), 401, 500)],
            'NO2': [(0, 40, 0, 50), (41, 80, 51, 100), (81, 180, 101, 200), (181, 280, 201, 300), (281, 400, 301, 400), (401, float('inf'), 401, 500)],
            'O3': [(0, 50, 0, 50), (51, 100, 51, 100), (101, 168, 101, 200), (169, 208, 201, 300), (209, 748, 301, 400), (749, float('inf'), 401, 500)],
            'CO': [(0, 1.0, 0, 50), (1.1, 2.0, 51, 100), (2.1, 10.0, 101, 200), (10.1, 17.0, 201, 300), (17.1, 34.0, 301, 400), (34.1, float('inf'), 401, 500)],
            'SO2': [(0, 40, 0, 50), (41, 80, 51, 100), (81, 380, 101, 200), (381, 800, 201, 300), (801, 1600, 301, 400), (1601, float('inf'), 401, 500)]
        }

        sub_indices = []
        for pollutant in required_pollutants:
            if pollutant in df_pivot.columns:
                df_pivot[f'{pollutant}_sub_index'] = df_pivot[pollutant].apply(
                    lambda x: None if pd.isna(x) else max(
                        [sub_index for sub_index in [calculate_sub_index(x, bp_lo, bp_hi, i_lo, i_hi) for bp_lo, bp_hi, i_lo, i_hi in breakpoints[pollutant]] if sub_index is not None],
                        default=None
                    )
                )
                sub_indices.append(f'{pollutant}_sub_index')

        if sub_indices:
            df_pivot['AQI'] = df_pivot[sub_indices].max(axis=1)
        else:
            df_pivot['AQI'] = np.nan

        def assign_aqi_bucket(aqi):
            try:
                aqi = float(aqi)
                if aqi <= 50: return 'Good'
                elif aqi <= 100: return 'Satisfactory'
                elif aqi <= 200: return 'Moderate'
                elif aqi <= 300: return 'Poor'
                elif aqi <= 400: return 'Very Poor'
                else: return 'Severe'
            except (ValueError, TypeError):
                return None

        df_pivot['AQI_Bucket'] = df_pivot['AQI'].apply(assign_aqi_bucket)
        df_pivot = df_pivot.drop(columns=sub_indices, errors='ignore')

    expected_columns = ['City', 'Date', 'station', 'PM2.5', 'PM10', 'NO', 'NO2', 'NOx', 'NH3', 'CO', 'SO2', 'O3', 'Benzene', 'Toluene', 'AQI', 'AQI_Bucket', 'Year', 'Month']
    for col in expected_columns:
        if col not in df_pivot.columns:
            df_pivot[col] = np.nan
    df_pivot['Year'] = np.nan
    df_pivot['Month'] = np.nan
    df_pivot = df_pivot[expected_columns]
    return df_pivot

df = preprocessing(df)
print(f"Final DataFrame shape after preprocessing: {df.shape}")
cities = df['City'].unique()
print(f"Cities available: {cities}")

# Function to fetch current weather and forecast
def get_weather_forecast(city=None, api_key="31dc051843b6c8ba7f4a770a2b3237f8", lat=None, lon=None, display_city=None):
    # Helper function to process current weather data
    def process_weather_data(data, city_name):
        if data["cod"] == 200:
            T = data["main"]["temp"]
            TM = T + 2
            Tm = T - 2
            SLP = 1013.25
            H = data["main"]["humidity"]
            VV = 10 if "clear" in data["weather"][0]["description"].lower() else 5
            V = data["wind"]["speed"]
            VM = V + 1
            current_time_utc = datetime.utcnow().timestamp()
            timezone_offset = data.get("timezone", 0)  # Seconds offset from UTC
            current_time_local = current_time_utc + timezone_offset
            sunrise = data["sys"]["sunrise"]
            sunset = data["sys"]["sunset"]
            is_day = sunrise <= current_time_local <= sunset
            description = data["weather"][0]["description"]
            print(f"Processing weather for {city_name}: Description={description}, Is Day={is_day}, Local Time={datetime.fromtimestamp(current_time_local)}, Sunrise={datetime.fromtimestamp(sunrise)}, Sunset={datetime.fromtimestamp(sunset)}")
            return {
                "city": city_name,
                "temp": round(T),
                "description": description,
                "humidity": H,
                "wind_speed": V,
                "model_inputs": [T, TM, Tm, SLP, H, VV, V, VM],
                "is_day": is_day
            }
        else:
            print(f"Error in weather data: {data.get('message', 'Unknown error')}")
            # Return a fallback weather object
            return {
                "city": city_name,
                "temp": 25,
                "description": "unknown",
                "humidity": 50,
                "wind_speed": 0,
                "model_inputs": [25, 27, 23, 1013.25, 50, 5, 0, 1],
                "is_day": True
            }

    # Helper function to process short-term forecast data (3-hour intervals)
    def process_short_term_forecast(data, city_name):
        if data["cod"] == "200":
            forecast_list = []
            for item in data["list"][:5]:  # Next 5 entries (15 hours)
                date = datetime.fromtimestamp(item["dt"]).strftime("%Y-%m-%d %H:%M")
                temp = round(item["main"]["temp"])
                description = item["weather"][0]["description"]
                forecast_list.append({
                    "date": date,
                    "temp": temp,
                    "description": description
                })
            return forecast_list
        else:
            print(f"Error in short-term forecast data: {data.get('message', 'Unknown error')}")
            return []

    # Helper function to process daily forecast data (up to 5 days with free API)
    def process_daily_forecast(data, city_name):
        if data["cod"] == "200":
            daily_forecast = {}
            for item in data["list"]:
                date = datetime.fromtimestamp(item["dt"]).strftime("%Y-%m-%d")
                temp = round(item["main"]["temp"])
                description = item["weather"][0]["description"]
                if date not in daily_forecast:
                    daily_forecast[date] = {"temp": temp, "description": description}
                else:
                    if temp > daily_forecast[date]["temp"]:
                        daily_forecast[date] = {"temp": temp, "description": description}
            forecast_list = [{"date": date, "temp": info["temp"], "description": info["description"]} for date, info in daily_forecast.items()]
            return forecast_list[:5]  # Limit to 5 days
        else:
            print(f"Error in daily forecast data: {data.get('message', 'Unknown error')}")
            return []

    # Fallback city mapping
    fallback_cities = {"kattakkada": "Thiruvananthapuram"}

    # Fetch by coordinates
    if lat is not None and lon is not None:
        print(f"Attempting to fetch weather by coordinates: lat={lat}, lon={lon}")
        coord_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        try:
            coord_response = requests.get(coord_url)
            coord_response.raise_for_status()
            coord_data = coord_response.json()
            weather_data = process_weather_data(coord_data, display_city if display_city else coord_data.get("name", "Unknown Location"))

            forecast_response = requests.get(forecast_url)
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()
            short_term_forecast = process_short_term_forecast(forecast_data, display_city if display_city else coord_data.get("name", "Unknown Location"))
            daily_forecast = process_daily_forecast(forecast_data, display_city if display_city else coord_data.get("name", "Unknown Location"))

            weather_data["forecast"] = short_term_forecast
            weather_data["daily_forecast"] = daily_forecast
            print(f"Successfully fetched weather and forecasts by coordinates for {weather_data['city']}")
            return weather_data
        except requests.exceptions.RequestException as e:
            print(f"HTTP error in weather/forecast API call by coordinates: {e}")
            return process_weather_data({"cod": 404}, display_city or "Unknown Location")

    # Fetch by city name
    if city:
        original_city = city
        city_lower = city.lower()
        if city_lower in fallback_cities:
            city = fallback_cities[city_lower]
            print(f"City '{original_city}' not found in API; falling back to '{city}'")

        print(f"Attempting to fetch weather by city name: {city}")
        current_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
        try:
            current_response = requests.get(current_url)
            current_response.raise_for_status()
            current_data = current_response.json()
            weather_data = process_weather_data(current_data, original_city if city_lower in fallback_cities else city)

            forecast_response = requests.get(forecast_url)
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()
            short_term_forecast = process_short_term_forecast(forecast_data, original_city if city_lower in fallback_cities else city)
            daily_forecast = process_daily_forecast(forecast_data, original_city if city_lower in fallback_cities else city)

            weather_data["forecast"] = short_term_forecast
            weather_data["daily_forecast"] = daily_forecast
            print(f"Successfully fetched weather and forecasts by city name for {city}")
            return weather_data
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"City '{city}' not found in OpenWeatherMap API")
                flash(f"City '{original_city}' not found. Please try a nearby city like 'Thiruvananthapuram'.", "error")
            else:
                print(f"HTTP error in weather/forecast API call for {city}: {e}")
                flash(f"Error fetching weather data for {original_city}. Please try again later.", "error")
            return process_weather_data({"cod": 404}, original_city)
        except Exception as e:
            print(f"Error in weather/forecast API call for {city}: {e}")
            flash(f"Error fetching weather data for {original_city}. Please try again later.", "error")
            return process_weather_data({"cod": 500}, original_city)

    print("Failed to fetch weather data by both coordinates and city name")
    flash("Unable to fetch weather data. Please try again with a different city.", "error")
    return process_weather_data({"cod": 500}, "Unknown Location")

@app.route("/", methods=['GET', 'POST'])
def home():
    weather_data = None

    if request.method == 'POST':
        if 'city' in request.form and request.form['city'].strip():
            city = request.form['city'].strip()
            print(f"Search input received: {city}")
            weather_data = get_weather_forecast(city=city)
            if weather_data:
                print(f"Successfully fetched weather for {city}: {weather_data}")
                session['city'] = city
                session['weather_data'] = weather_data
                session['weather_timestamp'] = datetime.now().isoformat()
                session['geolocation_attempted'] = True

        elif 'lat' in request.form and 'lon' in request.form:
            lat = float(request.form['lat'])
            lon = float(request.form['lon'])
            print(f"Geolocation received: lat={lat}, lon={lon}")
            geocode_url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid=31dc051843b6c8ba7f4a770a2b3237f8"
            city = None
            try:
                geocode_response = requests.get(geocode_url)
                geocode_response.raise_for_status()
                geocode_data = geocode_response.json()
                print(f"Reverse geocoding response: {geocode_data}")
                if geocode_data and len(geocode_data) > 0:
                    city = geocode_data[0]['name']
                    print(f"City from geolocation: {city}")
                else:
                    flash("Could not determine city from geolocation. Please search for a city manually.", "error")
            except requests.exceptions.RequestException as e:
                print(f"HTTP error in reverse geocoding: {e}")
                flash("Error determining city from geolocation. Please search for a city manually.", "error")
            except Exception as e:
                print(f"Error in reverse geocoding: {e}")
                flash("Error determining city from geolocation. Please search for a city manually.", "error")

            if city:
                weather_data = get_weather_forecast(city=city, lat=lat, lon=lon, display_city=city)
                if weather_data:
                    session['city'] = city
                    session['weather_data'] = weather_data
                    session['weather_timestamp'] = datetime.now().isoformat()
                    session['geolocation_attempted'] = True
                else:
                    session['geolocation_attempted'] = True

        elif 'geolocation_failed' in request.form:
            print("Geolocation failed, marking as attempted")
            session['geolocation_attempted'] = True
            flash("Geolocation failed. Please search for a city manually.", "error")

    else:
        if 'weather_timestamp' in session and 'weather_data' in session:
            last_update = datetime.fromisoformat(session['weather_timestamp'])
            if datetime.now() - last_update < timedelta(seconds=10):
                weather_data = session['weather_data']
                city = session['city']
                print(f"Using cached weather data for {city}: {weather_data}")
            else:
                print("Cache expired, attempting geolocation")
                session['geolocation_attempted'] = False

    # Force geolocation 
    if not session.get('geolocation_attempted', False) and weather_data is None:
        print("Triggering geolocation on initial load")
        session['geolocation_attempted'] = False

    print(f"Rendering home.html with weather_data: {weather_data}")
    return render_template(
        "home.html",
        weather=weather_data,
        short_term_forecast=weather_data.get("forecast", []) if weather_data else [],
        daily_forecast=weather_data.get("daily_forecast", []) if weather_data else [],
        geolocation_attempted=session.get('geolocation_attempted', False)
    )

@app.route("/table", methods=['GET', 'POST'])
def table():
    weather_data = None
    if request.method == 'POST' and 'city' in request.form and request.form['city'].strip():
        city = request.form['city'].strip()
        weather_data = get_weather_forecast(city=city)
        if weather_data:
            session['city'] = city
            session['weather_data'] = weather_data
            session['weather_timestamp'] = datetime.now().isoformat()
    elif 'weather_data' in session and 'weather_timestamp' in session:
        last_update = datetime.fromisoformat(session['weather_timestamp'])
        if datetime.now() - last_update < timedelta(minutes=3):
            weather_data = session['weather_data']
            print(f"Using cached weather data for {session['city']}: {weather_data}")
        else:
            print("Cache expired on /table, clearing session weather data")
            session.pop('weather_data', None)
            session.pop('weather_timestamp', None)
            session.pop('city', None)

    with open("Airquality_index.csv") as file:
        reader = csv.reader(file)
        header = next(reader)
        print(f"Rendering table.html with weather_data: {weather_data}")
        return render_template("table.html", header=header, rows=reader, weather=weather_data)

@app.route('/air', methods=['GET', 'POST'])
def datas():
    weather_data = None
    if request.method == 'POST' and 'city' in request.form and request.form['city'].strip():
        city = request.form['city'].strip()
        weather_data = get_weather_forecast(city=city)
        if weather_data:
            session['city'] = city
            session['weather_data'] = weather_data
            session['weather_timestamp'] = datetime.now().isoformat()
    elif 'weather_data' in session and 'weather_timestamp' in session:
        last_update = datetime.fromisoformat(session['weather_timestamp'])
        if datetime.now() - last_update < timedelta(minutes=3):
            weather_data = session['weather_data']
            print(f"Using cached weather data for {session['city']}: {weather_data}")
        else:
            print("Cache expired on /air, clearing session weather data")
            session.pop('weather_data', None)
            session.pop('weather_timestamp', None)
            session.pop('city', None)
    print(f"Rendering indexx.html with weather_data: {weather_data}")
    return render_template('indexx.html', weather=weather_data)

@app.route('/index', methods=['GET', 'POST'])
def index():
    weather_data = None
    AQI_predict = None
    if request.method == 'POST' and 'city' in request.form and request.form['city'].strip():
        city = request.form['city'].strip()
        weather_data = get_weather_forecast(city=city)
        if weather_data:
            session['city'] = city
            session['weather_data'] = weather_data
            session['weather_timestamp'] = datetime.now().isoformat()
            if 'model_inputs' in weather_data:
                AQI_predict = modelFor.predict([weather_data['model_inputs']])
    elif 'weather_data' in session and 'weather_timestamp' in session:
        last_update = datetime.fromisoformat(session['weather_timestamp'])
        if datetime.now() - last_update < timedelta(minutes=3):
            weather_data = session['weather_data']
            print(f"Using cached weather data for {session['city']}: {weather_data}")
            if 'model_inputs' in weather_data:
                AQI_predict = modelFor.predict([weather_data['model_inputs']])
        else:
            print("Cache expired on /index, clearing session weather data")
            session.pop('weather_data', None)
            session.pop('weather_timestamp', None)
            session.pop('city', None)
    print(f"Rendering result.html with weather_data: {weather_data}, prediction: {AQI_predict}")
    return render_template('result.html', weather=weather_data, prediction=AQI_predict)

@app.route("/predictions", methods=['GET', 'POST'])
def predictions():
    weather_data = None
    if request.method == 'POST' and 'city' in request.form and request.form['city'].strip():
        city = request.form['city'].strip()
        weather_data = get_weather_forecast(city=city)
        if weather_data:
            session['city'] = city
            session['weather_data'] = weather_data
            session['weather_timestamp'] = datetime.now().isoformat()
    elif 'weather_data' in session and 'weather_timestamp' in session:
        last_update = datetime.fromisoformat(session['weather_timestamp'])
        if datetime.now() - last_update < timedelta(minutes=3):
            weather_data = session['weather_data']
            print(f"Using cached weather data for {session['city']}: {weather_data}")
        else:
            print("Cache expired on /predictions, clearing session weather data")
            session.pop('weather_data', None)
            session.pop('weather_timestamp', None)
            session.pop('city', None)
    print(f"Rendering prediction.html with weather_data: {weather_data}")
    return render_template("prediction.html", weather=weather_data)

@app.route("/about", methods=['GET', 'POST'])
def about():
    weather_data = None
    if request.method == 'POST' and 'city' in request.form and request.form['city'].strip():
        city = request.form['city'].strip()
        weather_data = get_weather_forecast(city=city)
        if weather_data:
            session['city'] = city
            session['weather_data'] = weather_data
            session['weather_timestamp'] = datetime.now().isoformat()
    elif 'weather_data' in session and 'weather_timestamp' in session:
        last_update = datetime.fromisoformat(session['weather_timestamp'])
        if datetime.now() - last_update < timedelta(minutes=3):
            weather_data = session['weather_data']
            print(f"Using cached weather data for {session['city']}: {weather_data}")
        else:
            print("Cache expired on /about, clearing session weather data")
            session.pop('weather_data', None)
            session.pop('weather_timestamp', None)
            session.pop('city', None)
    print(f"Rendering about.html with weather_data: {weather_data}")
    return render_template("about.html", weather=weather_data)

@app.route("/pollution", methods=['POST', 'GET'])
def pollution():
    weather_data = None
    if 'weather_data' in session and 'weather_timestamp' in session:
        last_update = datetime.fromisoformat(session['weather_timestamp'])
        if datetime.now() - last_update < timedelta(minutes=3):
            weather_data = session['weather_data']
            print(f"Using cached weather data for {session['city']}: {weather_data}")
        else:
            print("Cache expired on /pollution, clearing session weather data")
            session.pop('weather_data', None)
            session.pop('weather_timestamp', None)
            session.pop('city', None)
    print(f"Rendering pollution.html with weather_data: {weather_data}")
    return render_template("pollution.html", city=cities, weather=weather_data)

@app.route('/select', methods=['POST', 'GET'])
def select():
    city = request.form.get('operator')
    date = request.form.get('operator2')
    weather_data = None
    if 'weather_data' in session and 'weather_timestamp' in session:
        last_update = datetime.fromisoformat(session['weather_timestamp'])
        if datetime.now() - last_update < timedelta(minutes=3):
            weather_data = session['weather_data']
            print(f"Using cached weather data for {session['city']}: {weather_data}")
        else:
            print("Cache expired on /select, clearing session weather data")
            session.pop('weather_data', None)
            session.pop('weather_timestamp', None)
            session.pop('city', None)
    
    city_data = df[df['City'] == city]
    city_year = city_data[city_data['Date'].astype(str).str.contains(date, na=False)]
    city_year = city_year.sort_values(by='Date', ascending=False)
    city_last_10_days = city_year.head(10)
    data_list = city_last_10_days.to_dict('records')
    
    print(f"Rendering pollution.html with weather_data: {weather_data}")
    return render_template(
        "pollution.html",
        city=cities,
        data_list=data_list,
        new=f"{city}: Last 10 Entries (Year {date})",
        weather=weather_data
    )

if __name__ == "__main__":
    app.run(debug=True)