# hk-bus-time-between-stops
 
This repository hosts an **experimental attempt** to fetch and calculate the estimated journey times between bus stops, MTR Stations and Light Rail stops where ETA services are available in Hong Kong. The results seems to be quite close to the official estimates from the transport operators.

It essentially works by looking at the distance between stops/stations and the ETA difference between them on services the stops at them consecutively. Values are averaged out over time in hopes of getting more and more accurate.

The code is being executed on an external server 24/7 and its results are pushed to the [`pages`](https://github.com/LOOHP/hk-bus-time-between-stops/tree/pages) branch at around minute 0 every hour (might be slightly delayed). The files are indexed with the first 2 characters (or the first character if there isn't a 2nd one) to strike a balance between not having one big data file and not having a few thousand small files.

### Example request
Get the journey times to all next stops from Battery Street Jordan (**07**6E1E9D5874C41D)<br>
Request: https://timeinterval.hkbuseta.com/times/07.json

Alternatively, you can fetch the page that contains all journey times<br>
Request: https://timeinterval.hkbuseta.com/times/all.json

### Example hourly request 
**Missing journey times for hourly requests are normal, you are advised to fallback to the average journey time using the regular request above.**

Get the journey times to all next stops from Battery Street Jordan (**07**6E1E9D5874C41D) **on Monday from 10:00 - 10:59**<br>
Request: https://timeinterval.hkbuseta.com/times_hourly/1/10/07.json

Alternatively, you can fetch the page that contains all journey times in that hour<br>
Request: https://timeinterval.hkbuseta.com/times_hourly/1/10/all.json

## Disclaimer
As this is an **experimental attempt**, please **expect inaccuracies**, especially to highly frequent & busy services, although the results seems to be quite close to offical estimates.

## Key Features
### Dynamic "Ripple" Travel Time Calculation
Travel times are calculated cumulatively to account for the passage of time during a journey. Instead of fetching traffic data for all stops at a single static hour (e.g., 8:00 AM), the system estimates the arrival time at each stop and looks up the relevant traffic data for that specific time. This "ripple effect" ensures that long routes reflect changing traffic conditions (e.g., a bus transitioning from off-peak to rush hour).

### Overnight Day Wrapping
For trips that start late at night and extend past midnight, the system automatically detects the date change and switches to fetching data from the next day's source. This ensures that a Friday night bus arriving Saturday morning uses Saturday morning traffic data for the latter part of the journey.

## Credits
Many thanks to `HK Bus Crawling@2021, https://github.com/hkbus/hk-bus-crawling`
