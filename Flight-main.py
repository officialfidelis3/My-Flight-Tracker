```python
import streamlit as st
import requests
import pandas as pd
import folium
import sqlite3
import time
import smtplib
from twilio.rest import Client
from streamlit_folium import folium_static

# OpenSky API URL
API_URL = "https://opensky-network.org/api/states/all"
WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
WEATHER_API_KEY = "your_weather_api_key"
AIRLINE_INFO_API = "https://aviation-edge.com/v2/public/airlineDatabase"
AIRLINE_API_KEY = "your_airline_api_key"
AIRPORT_INFO_API = "https://aviation-edge.com/v2/public/airportDatabase"

# Twilio Credentials
TWILIO_ACCOUNT_SID = "your_account_sid"
TWILIO_AUTH_TOKEN = "your_auth_token"
TWILIO_PHONE_NUMBER = "your_twilio_phone_number"

# Initialize SQLite database
conn = sqlite3.connect("flights.db", check_same_thread=False)
cursor = conn.cursor()

# Create flight tracking table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS flights (
        icao24 TEXT PRIMARY KEY,
        callsign TEXT,
        airline TEXT,
        latitude REAL,
        longitude REAL,
        altitude REAL,
        velocity REAL,
        departure TEXT,
        arrival TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

# Streamlit UI
st.markdown(
    """
    <style>
    .main {
        background-color: orange;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("✈️ Passenger Flight Tracker")
st.write("Real-time flight tracking for passengers.")

# User selects country
def get_country_list():
    return ["Worldwide", "Nigeria", "United States", "United Kingdom", "Canada", "India", "Germany", "France", "China", "Brazil"]

selected_country = st.selectbox("Select Your Country", get_country_list())

# User inputs
flight_number = st.text_input("Enter Flight Number or Callsign")
airline_name = st.text_input("Enter Airline Name")
departure_city = st.text_input("Enter Departure City")
passenger_email = st.text_input("Enter Your Email for Alerts")
passenger_phone = st.text_input("Enter Your Phone Number for SMS Alerts")
destination_city = st.text_input("Enter Destination City for Weather Info")

# Fetch airline details
def fetch_airline_info(airline_name):
    params = {"key": AIRLINE_API_KEY, "name": airline_name}
    response = requests.get(AIRLINE_INFO_API, params=params)
    if response.status_code == 200:
        try:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0]  # Return first matching airline
            else:
                st.warning("No airline details found.")
        except ValueError:
            st.error("Invalid response from airline API.")
    else:
        st.error(f"Failed to fetch airline info. Status code: {response.status_code}")
    return None

# Fetch flight data
def fetch_flight_data():
    response = requests.get(API_URL)
    if response.status_code == 200:
        return response.json().get("states", [])
    return []

def filter_flights(flights):
    filtered = []
    for flight in flights:
        if flight[1] and flight_number in flight[1] and flight[6] is not None and flight[5] is not None:
            filtered.append({
                "icao24": flight[0],
                "callsign": flight[1].strip(),
                "latitude": flight[6],
                "longitude": flight[5],
                "altitude": flight[7],
                "velocity": flight[9]
            })
    return filtered

# Fetch weather information
def fetch_weather(city):
    if not city:
        return None
    params = {"q": city, "appid": WEATHER_API_KEY, "units": "metric"}
    response = requests.get(WEATHER_API_URL, params=params)
    if response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            st.error("Invalid weather data received.")
    return None

def fetch_airport_info(city):
    params = {"nameCity": city, "key": AIRLINE_API_KEY}
    response = requests.get(AIRPORT_INFO_API, params=params)
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0]
    return None

# Send SMS alerts
def send_sms_alert(to_phone, message):
    if not to_phone:
        st.warning("Please enter a valid phone number for SMS alerts.")
        return
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=message, from_=TWILIO_PHONE_NUMBER, to=to_phone)
        st.success("SMS Alert Sent Successfully!")
    except Exception as e:
        st.error(f"Failed to send SMS: {e}")

flights = fetch_flight_data()
filtered_flights = filter_flights(flights)

if filtered_flights:
    df = pd.DataFrame(filtered_flights)
    st.dataframe(df)
    
    # Display Map
    m = folium.Map(location=[9.08, 8.68], zoom_start=6)
    for flight in filtered_flights:
        if flight["latitude"] is not None and flight["longitude"] is not None:
            folium.Marker(
                location=[flight["latitude"], flight["longitude"]],
                popup=f'Callsign: {flight["callsign"]}\nAltitude: {flight["altitude"]}m',
                icon=folium.Icon(color="blue", icon="plane", prefix="fa")
            ).add_to(m)
    folium_static(m)
    
    # Fetch weather info
    if destination_city:
        weather_data = fetch_weather(destination_city)
        if weather_data:
            st.subheader(f"🌤️ Weather at {destination_city}")
            st.write(f"Temperature: {weather_data['main']['temp']}°C")
            st.write(f"Weather: {weather_data['weather'][0]['description'].title()}")
        else:
            st.error("Could not fetch weather information.")
    
    # Send SMS alert
    if passenger_phone:
        sms_message = f"Flight {flight_number} is currently in the air. Stay updated!"
        send_sms_alert(passenger_phone, sms_message)
else:
    st.warning("No matching flights found.")
```