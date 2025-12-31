# HK Bus Travel Time Explorer

[**Live Website**](https://hk-bus-eta-482904.web.app)

A web application to visualize and compare estimated travel times between bus stops in Hong Kong, leveraging historical data to provide "ripple" effect travel time calculations.

## Features

- **Route Visualization**: See travel times between stops for any bus route.
- **Dynamic "Ripple" Calculation**: Estimates arrival times at each stop based on the departure time from the previous stop, accounting for changing traffic conditions over the course of a journey.
- **Route Comparison**: Compare travel times of different routes that share the same start and end stops.
- **Hourly Analysis**: View how travel times fluctuate throughout the day.
- **Overnight Support**: Automatically handles trips that span across midnight.

## Technical Overview

- **Backend**: Python (`server.py`) with `http.server` for a lightweight API.
- **Frontend**: Vanilla HTML/JS (`dashboard.html`, `dashboard_data.js`).
- **Data Analysis**: `analyze_route.py` processes raw ETA data to compute average intervals.
- **Deployment**: hosted on Firebase (Frontend on Hosting, Backend on Cloud Run).

## Local Development

To run the application locally:

1. **Install Dependencies**:
   Ensure you have Python 3 installed. No external packages are strictly required for the basic server, as it uses standard libraries.

2. **Run Server**:
   ```bash
   python3 server.py
   ```

3. **Open Access**:
   Navigate to `http://localhost:8000` in your browser.

## Deployment

The project is configured for Firebase.
- `deploy.sh`: Script to build the Docker container and deploy to Cloud Run and Firebase Hosting.
- `firebase.json`: Firebase configuration.

## Credits
Many thanks to `HK Bus Crawling@2021` (https://github.com/hkbus/hk-bus-crawling) for the underlying data structures.
