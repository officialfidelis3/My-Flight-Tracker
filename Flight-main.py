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
SEAT_LAYOUT_API = "https://api.seatguru.com/flight/seat-layout"

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
st.title("✈️ Passenger Flight Tracker")
st.write("Real-time flight tracking for passengers.")

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
        data = response.json()
        if data:
            return data[0]  # Return first matching airline
    return None

def fetch_flight_data():
    response = requests.get(API_URL)
    if response.status_code == 200:
        return response.json().get("states", [])
    return []

def filter_flights(flights):
    filtered = []
    for flight in flights:
        if flight[1] and flight_number in flight[1]:
            filtered.append({
                "icao24": flight[0],
                "callsign": flight[1].strip(),
                "latitude": flight[6],
                "longitude": flight[5],
                "altitude": flight[7],
                "velocity": flight[9]
            })
    return filtered

def fetch_weather(city):
    params = {"q": city, "appid": WEATHER_API_KEY, "units": "metric"}
    response = requests.get(WEATHER_API_URL, params=params)
    if response.status_code == 200:
        return response.json()
    return None

def fetch_airport_info(city):
    params = {"nameCity": city, "key": AIRLINE_API_KEY}
    response = requests.get(AIRPORT_INFO_API, params=params)
    if response.status_code == 200:
        return response.json()
    return None

def fetch_seat_layout(flight_number):
    response = requests.get(f"{SEAT_LAYOUT_API}/{flight_number}")
    if response.status_code == 200:
        return response.json()
    return None

flights = fetch_flight_data()
filtered_flights = filter_flights(flights)

if filtered_flights:
    df = pd.DataFrame(filtered_flights)
    st.dataframe(df)
    
    # Display Map
    m = folium.Map(location=[9.08, 8.68], zoom_start=6)
    for flight in filtered_flights:
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
    
    # Fetch airline info
    if airline_name:
        airline_info = fetch_airline_info(airline_name)
        if airline_info:
            st.subheader("🛫 Airline Information")
            st.write(f"**Airline Name:** {airline_info['name']}\n")
            st.write(f"**Country:** {airline_info['country']}\n")
            st.write(f"**IATA Code:** {airline_info['iataCode']}\n")
            st.write(f"**ICAO Code:** {airline_info['icaoCode']}\n")
        else:
            st.warning("Airline details not found.")
    
    # Fetch airport navigation
    airport_info = fetch_airport_info(destination_city)
    if airport_info:
        st.subheader("🏢 Airport Terminal Information")
        st.write(f"**Airport Name:** {airport_info[0]['nameAirport']}\n")
        st.write(f"**Terminal Services:** {airport_info[0]['services']}\n")
    else:
        st.warning("No airport details found.")
    
    # Fetch seat layout
    seat_layout = fetch_seat_layout(flight_number)
    if seat_layout:
        st.subheader("💺 Seat Layout Information")
        st.image(seat_layout['seatMapUrl'], caption="Seat Map", use_column_width=True)
    else:
        st.warning("No seat layout found for this flight.")
else:
    st.warning("No matching flights found.")

# Email & SMS Alerts
if st.button("Subscribe for Flight Alerts"):
    if passenger_email or passenger_phone:
        st.success("You will receive flight updates via email and SMS.")
        # Placeholder for sending alerts
        # You would integrate Twilio for SMS and SMTP for emails here.
    else:
        st.error("Please enter a valid email or phone number.")

