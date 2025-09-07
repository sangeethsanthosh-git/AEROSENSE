# 🌦️ AEROSENSE – Weather & Air Quality Monitoring App  

[![Python](https://img.shields.io/badge/Python-3.9-blue?logo=python)](https://www.python.org/)  
[![Flask](https://img.shields.io/badge/Flask-2.x-green?logo=flask)](https://flask.palletsprojects.com/)  
[![OpenWeather](https://img.shields.io/badge/API-OpenWeatherMap-orange?logo=openstreetmap)](https://openweathermap.org/)  
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)  

AEROSENSE is a **Flask web application** that provides real-time **weather data**, a **5-day forecast**, and **air pollution levels** for any city or your current location.  
It integrates with the [OpenWeatherMap API](https://openweathermap.org/api) to deliver accurate and up-to-date environmental insights.  

---

## ✨ Features  
- 🌍 Search weather and air quality by **city name**  
- 📍 Detect location automatically using **geolocation (lat/lon)**  
- 🌡️ Current weather details:  
  - Temperature  
  - Humidity  
  - Pressure  
  - Wind Speed  
  - Visibility  
  - Day/Night status  
- 📅 **5-Day Weather Forecast**  
- 🏭 **Air Pollution Data** (AQI, PM2.5, PM10, CO, SO₂, NO₂, O₃)  
- ⚡ **Session-based caching** to minimize API calls  

---

## 🛠️ Tech Stack  
- **Backend:** Python, Flask  
- **Frontend:** Jinja2 Templates (HTML, CSS, JS)  
- **API Services:** OpenWeatherMap (Weather, Forecast, Air Pollution, Geocoding)  
- **Others:** Requests, Sessions  

---

## 🚀 Installation & Setup  

1. **Clone this repository**
   ```bash
   git clone https://github.com/sangeethsanthosh-git/AEROSENSE.git
   cd AEROSENSE
2. **Create and activate a virtual environment**

python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows


3. ***Install dependencies**

pip install -r requirements.txt


4. **Get your OpenWeatherMap API Key**

Sign up at OpenWeatherMap

Replace the placeholder inside app.py:

app.secret_key = "REPLACE WITH YOUR OPENWEATHER API"


5. **Run the app**

python app.py



📸 Screenshots

### 🖼️ UI Image
![UI](assets/ui.png)

⚠️ Notes

Cached data expires after 3 minutes to reduce API calls.

If a city is not found, fallback logic suggests nearby valid cities.

Requires a valid OpenWeatherMap API Key with access to Weather, Forecast, Air Pollution & Geocoding APIs.

📌 Roadmap / Future Enhancements

📝 License

This project is licensed under the MIT License – free to use and modify for educational or personal purposes.