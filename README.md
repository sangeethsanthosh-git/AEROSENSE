Air Quality & Weather App






Overview
The Air Quality & Weather App is a web application designed to provide users with real-time air quality and weather information for cities in India. Built using Flask, this app features a modern, dark-mode interface inspired by minimalist weather widgets, with dynamic background images that change based on weather conditions and time of day. Users can search for weather data, view air quality metrics, and explore historical pollution data through an intuitive table interface.

This project was developed to enhance awareness of environmental conditions, combining air quality data (e.g., PM2.5, PM10, AQI) with weather forecasts in a visually appealing and user-friendly way.

Features
Dynamic Backgrounds: Background images or GIFs change based on weather conditions (e.g., sunny, rainy, stormy) and time of day (day/night), creating an immersive user experience.
Weather Information: Displays current weather details including temperature, humidity, wind speed, and chance of rain for a selected city (default: Delhi).
Air Quality Data: Provides detailed air quality metrics (PM2.5, PM10, NO2, O3, CO, SO2, AQI) in a scrollable table, with historical data for the last 15 days.
City and Year Selection: Users can select a city and year to view corresponding air quality data via a dropdown form.
Responsive Design: Features a minimalist sidebar navigation and a responsive layout that adapts to different screen sizes.
Dark-Mode Interface: A sleek, dark-themed UI with semi-transparent elements for better readability over dynamic backgrounds.
Screenshots
Home Page (Weather Widget)


Displays current weather and a 5-day forecast with a dynamic background.

Pollution Data Page


Shows air quality data in a table with city and year selection.

Technologies Used
Backend: Flask (Python) for routing and template rendering.
Frontend: HTML, CSS, JavaScript for dynamic background updates and UI.
Templating: Jinja2 for dynamic content rendering.
Styling: Custom CSS with a dark-mode theme, flexbox for layout.
Assets: Images/GIFs stored in the static folder for dynamic backgrounds.
Installation
Prerequisites
Python 3.8 or higher
pip (Python package manager)
Git
Steps
Clone the Repository:
bash

Copy
cd air-quality-weather-app
Create a Virtual Environment:
bash

Copy
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install Dependencies:
bash

Copy
pip install -r requirements.txt
Set Up Background Images:
Place weather-specific images in the static folder. Required files:
sunny-day.jpg
cloudy-day.jpg
rainy-day.jpg
stormy-day.jpg
clear-night.jpg
cloudy-night.jpg
rainy-night.jpg
stormy-night.jpg
default.jpg
Optionally, use GIFs (e.g., sunny-day.gif) for animated backgrounds.
Run the Application:
bash

Copy
python app.py
The app will be available at http://127.0.0.1:5000.
Project Structure
text

Copy
air-quality-weather-app/
├── static/
│   ├── style.css           # Custom CSS (optional)
│   ├── sunny-day.jpg       # Background images
│   ├── cloudy-day.jpg
│   ├── rainy-day.jpg
│   ├── stormy-day.jpg
│   ├── clear-night.jpg
│   ├── cloudy-night.jpg
│   ├── rainy-night.jpg
│   ├── stormy-night.jpg
│   └── default.jpg
├── templates/
│   ├── home.html           # Home page with weather widget
│   └── pollution.html      # Pollution data page with table
├── app.py                  # Flask application
├── requirements.txt        # Python dependencies
└── README.md               # Project documentation
Usage
Home Page (/):
Displays current weather and a 5-day forecast for the selected city (default: Delhi).
Use the search bar to enter a different city.
Background changes based on weather (e.g., sunny, rainy) and time of day (day/night).
Pollution Data Page (/pollution):
View air quality data for the last 15 days.
Select a city and year from the dropdown menus to filter the data.
Includes current weather details for the selected city.
Future Enhancements
Integrate a real weather API (e.g., OpenWeatherMap) for live weather data.
Add color-coded AQI indicators for better visualization.
Implement user authentication for personalized city preferences.
Optimize background GIFs for better performance on mobile devices.
Add a toggle to disable animated backgrounds for accessibility.
Contributing
Contributions are welcome! Please follow these steps:

Fork the repository.
Create a new branch (git checkout -b feature-name).
Make your changes and commit (git commit -m "Add feature").
Push to your branch (git push origin feature-name).
Create a pull request.
License
This project is licensed under the MIT License. See the  file for details.

Contact
For questions or suggestions, feel free to open an issue or contact me at [sangeethsanthosh80@gmail.com].

Notes for Customization
Screenshots: You’ll need to add actual screenshots to the screenshots folder and update the links in the README.
Repository URL: Replace yourusername with your actual GitHub username.
Email: Add your contact email or remove the contact section if not needed.
Weather API: If you’ve integrated an API, mention it in the "Technologies Used" and "Future Enhancements" sections.
Requirements File: Ensure you have a requirements.txt with at least Flask (e.g., Flask==2.0.1).
