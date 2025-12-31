import json
import os
import urllib.request
import webbrowser
import sys

# Configuration
PAGES_DIR = 'hk-bus-time-between-stops-pages'
HOURLY_BASE = os.path.join(PAGES_DIR, 'times_hourly')
OUTPUT_JS_FILE = 'dashboard_data.js'
BRIDGE_DB_URL = "https://raw.githubusercontent.com/hkbus/hk-bus-crawling/refs/heads/gh-pages/routeFareList.min.json"

DAYS = {
    '0': 'Sunday',
    '1': 'Monday',
    '2': 'Tuesday',
    '3': 'Wednesday',
    '4': 'Thursday',
    '5': 'Friday',
    '6': 'Saturday'
}

def get_json(url):
    try:
        print(f"Downloading route database from {url}...")
        req = urllib.request.Request(url, headers={'User-Agent': "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            return json.loads(data)
    except Exception as e:
        print(f"Error fetching DB: {e}")
        return None

def find_route_stops(db, route_num, variant_index=0, target_dest=None):
    print(f"Searching for Route {route_num}...")
    
    candidates = []
    for key, val in db['routeList'].items():
        # Check for KMB or CTB in company list
        company_list = val.get('co', [])
        if val.get('route') == route_num and ('kmb' in company_list or 'ctb' in company_list):
            dest = val.get('dest', {}).get('en', 'Unknown')
            candidates.append((key, val, dest))
            
    if not candidates:
        print(f"Route {route_num} not found in database.")
        return None, None, None, []

    # Sort candidates to ensure stable ordering (e.g. by key or dest)
    candidates.sort(key=lambda x: x[0])
    
    # Prepare variants list for frontend
    variants_info = []
    for idx, (key, val, dest) in enumerate(candidates):
        variants_info.append({
            "index": idx,
            "dest": dest,
            "key": key
        })
        
    # Smart Direction Selection
    if target_dest:
        # Try to find the variant that matches the requested destination
        # Normalize comparison (case-insensitive) just in case
        clean_target = target_dest.strip().lower()
        for idx, (key, val, dest) in enumerate(candidates):
            if dest.strip().lower() == clean_target:
                variant_index = idx
                print(f"  Matched target destination '{target_dest}' to variant {idx}")
                break
        
    # specific variant selection (default to 0)
    if variant_index < 0 or variant_index >= len(candidates):
        variant_index = 0
        
    selected_key, selected_val, dest = candidates[variant_index]
    freq_data = selected_val.get('freq')
    print(f"Selected: {selected_key} (To: {dest})")
    
    # Try getting KMB stops first, then CTB
    stop_ids = selected_val['stops'].get('kmb')
    if not stop_ids:
        stop_ids = selected_val['stops'].get('ctb')
    
    if not stop_ids:
        print("No stop list found for Key:", selected_key)
        return None, None, None, []
    
    # Enrich with names
    enriched_stops = []
    stop_list_db = db.get('stopList', {})
    
    for sid in stop_ids:
        info = stop_list_db.get(sid, {})
        name = info.get('name', {}).get('en', sid)
        enriched_stops.append({
            "id": sid,
            "name": name
        })
        
    return enriched_stops, f"{route_num} to {dest}", stop_ids, variants_info, freq_data

def find_overlapping_routes(db, start_id, end_id, exclude_route=None):
    """
    Finds all routes that contain start_id followed eventually by end_id.
    Returns a list of route numbers.
    """
    matches = []
    
    for val in db['routeList'].values():
        route_num = val.get('route')
        
        # Optimization: Skip if it's the same route we are already on
        if exclude_route and route_num == exclude_route:
            continue
            
        # Try both KMB and CTB stop lists
        stops = val.get('stops', {}).get('kmb', [])
        if not stops:
            stops = val.get('stops', {}).get('ctb', [])
        
        if start_id in stops and end_id in stops:
            # Check order: Start must come before End
            idx_start = stops.index(start_id)
            idx_end = stops.index(end_id)
            
            if idx_start < idx_end:
                 # Check 'co' to ensure it's KMB or CTB
                 company_list = val.get('co', [])
                 if 'kmb' in company_list or 'ctb' in company_list:
                     matches.append(route_num)
                     
    # Remove duplicates and sort
    matches = sorted(list(set(matches)))
    return matches

def load_local_json(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except:
        return {}

MAX_DAY_CODE = 6

def get_next_day(day_code):
    """Returns the next day code string (e.g. '0'->'1', '6'->'0')"""
    # Assuming day_code is a string '0'-'6'
    try:
        d = int(day_code)
        next_d = (d + 1) % 7
        return str(next_d)
    except:
        return day_code

def get_valid_hours_for_day(freq_data, day_code):
    """
    Parses freq_data to return a set of valid hours (0-23) for the given day.
    freq_data format example: 
    {'287': {'0600': ['0620', ...], ...}} 
    The keys '287' are DayMasks. 
    1=Mon, 2=Tue, 4=Wed, 8=Thu, 16=Fri, 32=Sat, 64=Sun.
    287 = 1+2+4+8+16+256(Holiday) = Mon-Fri + Hol? No wait.
    Actually standard is: 1=Mon, 2=Tue, 4=Wed, 8=Thu, 16=Fri, 32=Sat, 64=Sun, 128=Holiday.
    287 = 1+2+4+8+16+256 is 111110001?
    
    Let's stick to simple day checking.
    DAYS map: 0=Sun(64), 1=Mon(1), 2=Tue(2), 3=Wed(4), 4=Thu(8), 5=Fri(16), 6=Sat(32).
    """
    if not freq_data:
        return set(range(24)) # If no data, allow all
        
    # Map our day_code '0'-'6' to bitmask
    # 0=Sun=64, 1=Mon=1, 2=Tue=2, 3=Wed=4, 4=Thu=8, 5=Fri=16, 6=Sat=32
    # But wait, holidays might complicate. Let's look for matching mask.
    
    target_mask = 0
    d_int = int(day_code)
    if d_int == 0: target_mask = 64
    elif d_int == 1: target_mask = 1
    elif d_int == 2: target_mask = 2
    elif d_int == 3: target_mask = 4
    elif d_int == 4: target_mask = 8
    elif d_int == 5: target_mask = 16
    elif d_int == 6: target_mask = 32
        
    valid_hours = set()
    
    for mask_str, timings in freq_data.items():
        try:
            mask = int(mask_str)
            if (mask & target_mask) > 0:
                # This timetable applies to this day
                # timings is dict: start_time -> [end_time, interval]
                # We care about the valid range [start_time, end_time + buffer]
                
                # Find min start and max end
                min_t = 2400
                max_t = 0
                
                for start_t_str, vals in timings.items():
                    # start_t_str like '0600'
                    end_t_str = vals[0] # '0620'
                    
                    s = int(start_t_str)
                    e = int(end_t_str)
                    
                    if s < min_t: min_t = s
                    if e > max_t: max_t = e
                
                # Add buffer (e.g. 120 mins) to max_t to allow completion
                # max_t is HHMM format. This is tricky.
                # Convert to minutes from midnight
                def to_mins(hhmm):
                    h = hhmm // 100
                    m = hhmm % 100
                    return h * 60 + m
                
                start_min = to_mins(min_t)
                end_min = to_mins(max_t) + 120 # 2 hours buffer
                
                # Convert back to hours arguments
                # For simplicity, we just check if hour H starts within [start_min, end_min]
                
                for h in range(24):
                    # Check if H:00 is within range
                    # Allow logical day overlap (e.g. 2500)
                    # If start_min is 0600 (360m) and end_min is 2500 (1500 + 120 = 1620m)
                    # hour 4 (240m) -> No
                    # hour 6 (360m) -> Yes
                    # hour 23 (1380m) -> Yes
                    # hour 0 (0m) -> treated as 24? No, standard day loop.
                    
                    # Normal day check
                    h_mins = h * 60
                    if start_min <= h_mins <= end_min:
                        valid_hours.add(h)
                    
                    # Next day wrap check (for late night services > 2400)
                    h_mins_next = (h + 24) * 60
                    if start_min <= h_mins_next <= end_min:
                        valid_hours.add(h)
                        
        except:
            pass
            
    return valid_hours

def calculate_hourly_data(stops, start_index=0, end_index=None, freq_data=None):
    chart_data = {}
    print(f"Scanning local data files (Stops {start_index} to {end_index})...")
    
    if end_index is None:
        end_index = len(stops) - 1
        
    # Validation
    if start_index < 0: start_index = 0
    if end_index >= len(stops): end_index = len(stops) - 1
    if start_index >= end_index: 
        return {k: [None]*24 for k in DAYS}
    
    total_segments_in_range = end_index - start_index
    
    # Optimization: simple cache for the current file being read
    # structure: { abs_path_string: content_dict }
    file_cache = {}
    
    for day_code in DAYS:
        print(f"  Processing {DAYS[day_code]}...")
        day_data = []
        
        # Determine valid hours for this day based on freq_data
        valid_service_hours = get_valid_hours_for_day(freq_data, day_code) if freq_data else set(range(24))
        
        # We iterate through start hours (0-23)
        for start_hour in range(24):
            # Filtering: Skip if not in service hours
            if start_hour not in valid_service_hours:
                day_data.append(None)
                continue
                
            total_seconds_accumulated = 0
            segments_found = 0
            
            # Start the ripple: We assume the bus starts exactly at `start_hour`:00
            current_simulated_time = start_hour * 3600
            
            # Track the current day context for this specific trip
            current_trip_day = day_code
            
            for i in range(start_index, end_index):
                start_id = stops[i]
                end_id = stops[i+1]
                
                # Check for day wrap
                # 86400 seconds = 24 hours
                # If simulated time exceeds 24h, we are in the next day
                day_offset = current_simulated_time // 86400
                
                # Dwell time assumption (boarding/alighting)
                dwell_time = 0
                
                start_id = stops[i]
                end_id = stops[i+1]
                
                # Check for day wrap
                day_offset = current_simulated_time // 86400
                lookup_hour = int((current_simulated_time // 3600) % 24)
                
                # Helper to get time from a specific hour
                def get_time_for_hour(d_code, h, s_id, e_id):
                    # Handle hour wrap 24 -> 0? No, data is 0-23. 
                    # If h < 0 or h > 23, we should probably stick to current day or wrap. 
                    # Simple clamping for adjacent check
                    if h < 0: h = 23 # prev day? complex. let's just clamp or wrap
                    if h > 23: h = 0
                    
                    # Determine effective day code (simplified for helper)
                    # We reuse logic from main loop or pass it in? 
                    # Let's duplicate the path logic for safety/simplicity here involves effective_day
                    pass
                
                # ... Actually let's just do it inline to access all variables
                
                # Determine effective day code
                effective_day = current_trip_day
                if day_offset > 0:
                    try:
                        base_d = int(current_trip_day)
                        effective_d = (base_d + int(day_offset)) % 7
                        effective_day = str(effective_d)
                    except:
                        pass

                prefix = start_id[:2]
                
                # Function to try fetching data
                def try_fetch(d, h):
                    p = os.path.join(HOURLY_BASE, str(d), f"{h:02d}", f"{prefix}.json")
                    if os.path.exists(p):
                        if p in file_cache:
                            dt = file_cache[p]
                        else:
                            dt = load_local_json(p)
                            file_cache[p] = dt
                        
                        if dt and start_id in dt and end_id in dt[start_id]:
                             val = dt[start_id][end_id]
                             if val > 0: return val
                    return None

                # 1. Try exact hour
                segment_time = try_fetch(effective_day, lookup_hour)
                
                # 2. Gap Filling: Try adjacent hours if missing
                if segment_time is None:
                    # Try previous hour
                    prev_h = (lookup_hour - 1) % 24
                    segment_time = try_fetch(effective_day, prev_h)
                    
                    if segment_time is None:
                        # Try next hour
                        next_h = (lookup_hour + 1) % 24
                        segment_time = try_fetch(effective_day, next_h)

                if segment_time is not None and segment_time > 0:
                    # Apply Traffic Multiplier (1.1x) found in original logic
                    segment_time = segment_time * 1.1
                    
                    total_seconds_accumulated += segment_time
                    total_seconds_accumulated += dwell_time
                    segments_found += 1
                    # Ripple effect: Advance the clock
                    current_simulated_time += segment_time
                    current_simulated_time += dwell_time
                else:
                    # Still missing after fallback
                    # We will rely on final scaling
                    # But we SHOULD add dwell time even if moving virtually?
                    # If we scale up later, dwell time is implicitly scaled up too.
                    pass
            
            # Data Validity Logic
            if total_segments_in_range > 0 and segments_found < total_segments_in_range * 0.5: # Relaxed from 0.9 to 0.5 given gap filling
                day_data.append(None)
            else:
                if segments_found > 0:
                     # Scale up to account for missing segments
                     adjusted_time = (total_seconds_accumulated / segments_found) * total_segments_in_range
                     day_data.append(round(adjusted_time / 60.0, 2))
                else:
                    day_data.append(None)
                
        chart_data[day_code] = day_data
        
    return chart_data

def generate_js(chart_data, title):
    content = f"""
window.routeTitle = "{title}";
window.chartData = {json.dumps(chart_data)};
"""
    with open(OUTPUT_JS_FILE, 'w') as f:
        f.write(content)
    print(f"Data saved to {OUTPUT_JS_FILE}")

def main():
    if len(sys.argv) > 1:
        route_input = sys.argv[1]
    else:
        route_input = input("Enter Route Number (e.g. 94): ").strip()
        
    db = get_json(BRIDGE_DB_URL)
    if not db:
        return

    enriched_stops, title, raw_stop_ids, variants = find_route_stops(db, route_input)
    if not enriched_stops:
        return
        
    chart_data = calculate_hourly_data(raw_stop_ids)
    generate_js(chart_data, title)
    
    print("Opening dashboard...")
    webbrowser.open('dashboard.html')

if __name__ == "__main__":
    main()
