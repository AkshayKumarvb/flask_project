import csv
from flask import Response


from flask import Flask, render_template, request, jsonify
import requests
import datetime

app = Flask(__name__)

# Function to get latitude and longitude from the place name
def get_lat_lon(place):
    """Fetch latitude and longitude using Open-Meteo API."""
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={place}&count=1&language=en&format=json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if "results" in data:
            lat = data["results"][0]["latitude"]
            lon = data["results"][0]["longitude"]
            return lat, lon
    return None, None

# Function to fetch solar irradiance data from NASA POWER API
def fetch_solar_irradiance(lat, lon, year):
    """Fetch hourly solar irradiance for a given year from NASA POWER API by splitting requests."""
    full_data = {}

    # NASA POWER API only allows fetching ~5000 records at once, so we split into two requests
    split_1_start = f"{year}0101"
    split_1_end = f"{year}0701"  # First half (Jan - June)
    split_2_start = f"{year}0702"
    split_2_end = f"{year}1231"  # Second half (July - Dec)

    urls = [
        f"https://power.larc.nasa.gov/api/temporal/hourly/point?latitude={lat}&longitude={lon}&parameters=ALLSKY_SFC_SW_DWN&start={split_1_start}&end={split_1_end}&format=JSON&community=re",
        f"https://power.larc.nasa.gov/api/temporal/hourly/point?latitude={lat}&longitude={lon}&parameters=ALLSKY_SFC_SW_DWN&start={split_2_start}&end={split_2_end}&format=JSON&community=re"
    ]

    for url in urls:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            try:
                full_data.update(data['properties']['parameter']['ALLSKY_SFC_SW_DWN'])
            except KeyError:
                print("API Response Error: Missing 'properties' or 'parameter' fields")
                return None
        else:
            print(f"❌ Failed to fetch data from NASA POWER API. Response: {response.content.decode()}")
            return None

    return full_data

# Route for the homepage (renders the form)
@app.route('/')
def index():
    return render_template('index.html')  # This renders your HTML form

# Route to handle the form submission and fetch solar irradiance data
@app.route('/get_solar_irradiance', methods=['GET'])
def get_solar_irradiance():
    place = request.args.get('place')  # Get place from the query string
    year = request.args.get('year')  # Get year from the query string

    if not place or not year:
        return jsonify({'error': 'Place and Year are required parameters.'}), 400

    # Get latitude and longitude for the place
    lat, lon = get_lat_lon(place)
    if lat is None or lon is None:
        return jsonify({'error': 'Could not fetch coordinates for the given place.'}), 400

    # Fetch solar irradiance data from NASA POWER API
    irradiance_data = fetch_solar_irradiance(lat, lon, year)

    if irradiance_data:
        # Prepare the data in a format for frontend display
        data = []
        for time, irradiance in irradiance_data.items():
            if irradiance != -999.0:  # Skip invalid data points
                date_time = datetime.datetime.strptime(time, "%Y%m%d%H")
                data.append({"time": date_time.strftime("%Y-%m-%d %H:%M:%S"), "irradiance": irradiance})

        return jsonify(data)  # Send the data back as JSON response

    return jsonify({'error': 'Failed to fetch solar irradiance data.'}), 500

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)

