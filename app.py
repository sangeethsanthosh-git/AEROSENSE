from flask import Flask, render_template, request, session, flash
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = '***REPLACE WITH YOUR OPENWEATHER API***'  # Replace with your actual OpenWeatherMap API key

# Function to fetch current weather, 5-day forecast, and air pollution data
def get_weather_and_pollution(city=None, api_key="***REPLACE WITH YOUR OPENWEATHER API***", lat=None, lon=None, display_city=None):
    def process_weather_data(data, city_name):
        if data["cod"] == 200:
            T = data["main"]["temp"]
            H = data["main"]["humidity"]
            SLP = data.get("main", {}).get("pressure", 1013.25)
            weather_desc = data["weather"][0]["description"].lower()
            VV = 10 if "clear" in weather_desc else 5 if "clouds" in weather_desc else 3
            V = data["wind"]["speed"]
            current_time_utc = datetime.utcnow().timestamp()
            timezone_offset = data.get("timezone", 0)
            current_time_local = current_time_utc + timezone_offset
            sunrise = data["sys"]["sunrise"]
            sunset = data["sys"]["sunset"]
            is_day = sunrise <= current_time_local <= sunset
            description = data["weather"][0]["description"]
            return {
                "city": city_name,
                "temp": round(T),
                "description": description,
                "humidity": H,
                "wind_speed": V,
                "pressure": SLP,
                "visibility": VV,
                "is_day": is_day
            }
        else:
            print(f"Error in weather data: {data.get('message', 'Unknown error')}")
            return {
                "city": city_name,
                "temp": 25,
                "description": "unknown",
                "humidity": 50,
                "wind_speed": 0,
                "pressure": 1013.25,
                "visibility": 5,
                "is_day": True
            }

    def process_air_pollution_data(data, city_name):
        if data.get("list"):
            latest = data["list"][0]["components"]
            aqi = data["list"][0]["main"]["aqi"]
            aqi_bucket = {
                1: "Good",
                2: "Fair",
                3: "Moderate",
                4: "Poor",
                5: "Very Poor"
            }.get(aqi, "Unknown")
            return {
                "city": city_name,
                "aqi": aqi,
                "aqi_bucket": aqi_bucket,
                "pm2_5": latest.get("pm2_5", 0),
                "pm10": latest.get("pm10", 0),
                "no2": latest.get("no2", 0),
                "o3": latest.get("o3", 0),
                "co": latest.get("co", 0),
                "so2": latest.get("so2", 0)
            }
        else:
            print(f"Error in air pollution data: {data.get('message', 'Unknown error')}")
            return {
                "city": city_name,
                "aqi": None,
                "aqi_bucket": "Unknown",
                "pm2_5": 0,
                "pm10": 0,
                "no2": 0,
                "o3": 0,
                "co": 0,
                "so2": 0
            }

    def process_forecast_data(data, city_name):
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
            return forecast_list[:5]
        else:
            print(f"Error in forecast data: {data.get('message', 'Unknown error')}")
            return []

    fallback_cities = {"kattakkada": "Thiruvananthapuram"}

    if lat is not None and lon is not None:
        print(f"Fetching data by coordinates: lat={lat}, lon={lon}")
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        pollution_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={api_key}"
        try:
            weather_response = requests.get(weather_url)
            weather_response.raise_for_status()
            weather_data = process_weather_data(weather_response.json(), display_city if display_city else "Unknown Location")

            forecast_response = requests.get(forecast_url)
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()
            daily_forecast = process_forecast_data(forecast_data, display_city if display_city else "Unknown Location")

            pollution_response = requests.get(pollution_url)
            pollution_response.raise_for_status()
            pollution_data = process_air_pollution_data(pollution_response.json(), display_city if display_city else "Unknown Location")

            weather_data["forecast"] = daily_forecast
            weather_data["pollution"] = pollution_data
            print(f"Successfully fetched data for {weather_data['city']}")
            return weather_data
        except requests.exceptions.RequestException as e:
            print(f"HTTP error in API call: {e}")
            flash("Error fetching data. Please try again.", "error")
            return process_weather_data({"cod": 404}, display_city or "Unknown Location")

    if city:
        original_city = city
        city_lower = city.lower()
        if city_lower in fallback_cities:
            city = fallback_cities[city_lower]
            print(f"City '{original_city}' not found; using '{city}'")
        print(f"Fetching data by city: {city}")
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
        # Get coordinates for air pollution API
        try:
            coord_response = requests.get(f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={api_key}")
            coord_response.raise_for_status()
            coord_data = coord_response.json()
            if not coord_data:
                raise requests.exceptions.HTTPError(status_code=404)
            lat = coord_data[0]["lat"]
            lon = coord_data[0]["lon"]
            pollution_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={api_key}"

            weather_response = requests.get(weather_url)
            weather_response.raise_for_status()
            weather_data = process_weather_data(weather_response.json(), original_city if city_lower in fallback_cities else city)

            forecast_response = requests.get(forecast_url)
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()
            daily_forecast = process_forecast_data(forecast_data, original_city if city_lower in fallback_cities else city)

            pollution_response = requests.get(pollution_url)
            pollution_response.raise_for_status()
            pollution_data = process_air_pollution_data(pollution_response.json(), original_city if city_lower in fallback_cities else city)

            weather_data["forecast"] = daily_forecast
            weather_data["pollution"] = pollution_data
            print(f"Successfully fetched data for {city}")
            return weather_data
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"City '{city}' not found")
                flash(f"City '{original_city}' not found. Try a nearby city.", "error")
            else:
                print(f"HTTP error for {city}: {e}")
                flash(f"Error fetching data for {original_city}. Try again later.", "error")
            return process_weather_data({"cod": 404}, original_city)
        except Exception as e:
            print(f"Error in API call for {city}: {e}")
            flash(f"Error fetching data for {original_city}. Try again later.", "error")
            return process_weather_data({"cod": 500}, original_city)

    print("Failed to fetch data")
    flash("Unable to fetch data. Try a different city.", "error")
    return process_weather_data({"cod": 500}, "Unknown Location")

@app.route("/", methods=['GET', 'POST'])
def home():
    weather_data = None
    location_source = None

    if request.method == 'POST':
        if 'city' in request.form and request.form['city'].strip():
            city = request.form['city'].strip()
            print(f"Search input received: {city}")
            weather_data = get_weather_and_pollution(city=city)
            location_source = "search"
            if weather_data:
                print(f"Successfully fetched data for {city}: {weather_data}")
                session['city'] = city
                session['weather_data'] = weather_data
                session['weather_timestamp'] = datetime.now().isoformat()
                session['geolocation_attempted'] = True
                session['location_source'] = location_source

        elif 'lat' in request.form and 'lon' in request.form:
            lat = float(request.form['lat'])
            lon = float(request.form['lon'])
            print(f"Geolocation received: lat={lat}, lon={lon}")
            geocode_url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid={app.secret_key}"
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
                weather_data = get_weather_and_pollution(city=city, lat=lat, lon=lon, display_city=city)
                location_source = "geolocation"
                if weather_data:
                    session['city'] = city
                    session['weather_data'] = weather_data
                    session['weather_timestamp'] = datetime.now().isoformat()
                    session['geolocation_attempted'] = True
                    session['location_source'] = location_source
                else:
                    session['geolocation_attempted'] = True

        elif 'geolocation_failed' in request.form:
            print("Geolocation failed, marking as attempted")
            session['geolocation_attempted'] = True
            flash("Geolocation failed. Please search for a city manually.", "error")

    else:
        if 'weather_timestamp' in session and 'weather_data' in session:
            last_update = datetime.fromisoformat(session['weather_timestamp'])
            if datetime.now() - last_update < timedelta(minutes=3):
                weather_data = session['weather_data']
                location_source = session.get('location_source', 'search')
                city = session['city']
                print(f"Using cached data for {city}: {weather_data}")
            else:
                print("Cache expired, attempting geolocation")
                session['geolocation_attempted'] = False

    if not session.get('geolocation_attempted', False) and weather_data is None:
        print("Triggering geolocation on initial load")
        session['geolocation_attempted'] = False

    print(f"Rendering home.html with weather_data: {weather_data}")
    return render_template(
        "home.html",
        weather=weather_data,
        forecast=weather_data.get("forecast", []) if weather_data else [],
        pollution=weather_data.get("pollution", None) if weather_data else None,
        geolocation_attempted=session.get('geolocation_attempted', False),
        location_source=location_source
    )

@app.route("/index", methods=['GET', 'POST'])
def index():
    weather_data = None
    location_source = None
    if request.method == 'POST':
        if 'city' in request.form and request.form['city'].strip():
            city = request.form['city'].strip()
            weather_data = get_weather_and_pollution(city=city)
            location_source = "search"
            if weather_data:
                session['city'] = city
                session['weather_data'] = weather_data
                session['weather_timestamp'] = datetime.now().isoformat()
                session['location_source'] = location_source
        elif 'lat' in request.form and 'lon' in request.form:
            lat = float(request.form['lat'])
            lon = float(request.form['lon'])
            print(f"Geolocation received: lat={lat}, lon={lon}")
            geocode_url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid={app.secret_key}"
            try:
                geocode_response = requests.get(geocode_url)
                geocode_response.raise_for_status()
                geocode_data = geocode_response.json()
                if geocode_data and len(geocode_data) > 0:
                    city = geocode_data[0]['name']
                    print(f"City from geolocation: {city}")
                    weather_data = get_weather_and_pollution(city=city, lat=lat, lon=lon, display_city=city)
                    location_source = "geolocation"
                    if weather_data:
                        session['city'] = city
                        session['weather_data'] = weather_data
                        session['weather_timestamp'] = datetime.now().isoformat()
                        session['location_source'] = location_source
                else:
                    flash("Could not determine city from geolocation.", "error")
            except requests.exceptions.RequestException as e:
                print(f"HTTP error in reverse geocoding: {e}")
                flash("Error determining city from geolocation.", "error")
    elif 'weather_data' in session and 'weather_timestamp' in session:
        last_update = datetime.fromisoformat(session['weather_timestamp'])
        if datetime.now() - last_update < timedelta(minutes=3):
            weather_data = session['weather_data']
            location_source = session.get('location_source', 'search')
            print(f"Using cached data for {session['city']}: {weather_data}")
        else:
            print("Cache expired on /index, clearing session data")
            session.pop('weather_data', None)
            session.pop('weather_timestamp', None)
            session.pop('city', None)
            session.pop('location_source', None)

    print(f"Rendering result.html with weather_data: {weather_data}")
    return render_template(
        'result.html',
        weather=weather_data,
        prediction=weather_data.get("pollution", {}).get("aqi") if weather_data else None,
        aqi_bucket=weather_data.get("pollution", {}).get("aqi_bucket") if weather_data else None,
        location_source=location_source
    )

if __name__ == "__main__":
    app.run(debug=True)
