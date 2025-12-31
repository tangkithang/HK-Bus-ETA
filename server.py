import http.server
import socketserver
import urllib.parse
import json
import analyze_route
import sys
import subprocess
import time
import os

# Configuration
PORT = int(os.environ.get('PORT', 8000))
BRIDGE_DB_URL = "https://raw.githubusercontent.com/hkbus/hk-bus-crawling/refs/heads/gh-pages/routeFareList.min.json"

# Global Cache
ROUTE_DB = None

class BusRouteHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        # API Endpoint
        if parsed.path == '/api/route':
            query = urllib.parse.parse_qs(parsed.query)
            route_id = query.get('id', [None])[0]
            start_idx = int(query.get('start', [0])[0])
            
            end_param = query.get('end', [None])[0]
            end_idx = int(end_param) if end_param else None
            
            var_param = query.get('variant', [0])[0]
            variant_idx = int(var_param)
            
            dest_param = query.get('dest', [None])[0]
            
            if not route_id:
                self.send_error(400, "Missing route id")
                return

            self.handle_route_request(route_id, start_idx, end_idx, variant_idx, dest_param)
            return

        # Search Endpoint
        if parsed.path == '/api/search':
            query = urllib.parse.parse_qs(parsed.query)
            q = query.get('q', [''])[0]
            self.handle_search_request(q)
            return
            self.handle_search_request(q)
            return

        # Overlap Endpoint
        if parsed.path == '/api/overlap':
            query = urllib.parse.parse_qs(parsed.query)
            start_id = query.get('start', [None])[0]
            end_id = query.get('end', [None])[0]
            exclude = query.get('exclude', [None])[0]
            
            if start_id and end_id:
                self.handle_overlap_request(start_id, end_id, exclude)
            else:
                 self.send_error(400, "Missing start or end stop id")
            return
            
        # Default to dashboard
        if self.path == '/' or self.path == '/index.html':
            self.path = '/dashboard.html'
            
        return super().do_GET()

    def handle_route_request(self, route_id, start_idx=0, end_idx=None, variant_idx=0, dest=None):
        try:
            global ROUTE_DB
            if not ROUTE_DB:
                print("Initializing DB...")
                ROUTE_DB = analyze_route.get_json(BRIDGE_DB_URL)
            
            print(f"Analyzing Route {route_id} [Var {variant_idx}] [Stop {start_idx} -> {end_idx}] [Dest: {dest}]...")
            enriched_stops, title, raw_stop_ids, variants, freq_data = analyze_route.find_route_stops(ROUTE_DB, route_id, variant_idx, dest)
            
            if not enriched_stops:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Route not found"}).encode())
                return
                
            chart_data = analyze_route.calculate_hourly_data(raw_stop_ids, start_idx, end_idx, freq_data)
            
            response_data = {
                "title": title,
                "stops": enriched_stops,
                "variants": variants,
                "current_variant": variant_idx,
                "data": chart_data
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())
            
        except Exception as e:
            print(f"Server Error: {e}")
            self.send_error(500, str(e))

    def handle_search_request(self, query):
        global ROUTE_DB
        if not ROUTE_DB:
            ROUTE_DB = analyze_route.get_json(BRIDGE_DB_URL)
            
        create_response = []
        seen = set()
        
        # Search DB
        q = query.upper()
        count = 0 
        
        # We search keys or values?
        # The structure is "HexID": { "route": "94", ... }
        
        for val in ROUTE_DB['routeList'].values():
            r = val.get('route', '')
            company_list = val.get('co', [])
            if r.startswith(q) and ('kmb' in company_list or 'ctb' in company_list):
                unique_key = r + "-" + val.get('dest', {}).get('en', '')
                if unique_key not in seen:
                    create_response.append({
                        "route": r,
                        "dest": val.get('dest', {}).get('en', 'Unknown')
                    })
                    seen.add(unique_key)
                    count += 1
                    
            if count >= 10: # Limit results
                break
                
        # Sort by route length then alpha
        create_response.sort(key=lambda x: (len(x['route']), x['route']))
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(create_response).encode())

    def handle_overlap_request(self, start_id, end_id, exclude_route=None):
        global ROUTE_DB
        if not ROUTE_DB:
            ROUTE_DB = analyze_route.get_json(BRIDGE_DB_URL)
            
        try:
             matches = analyze_route.find_overlapping_routes(ROUTE_DB, start_id, end_id, exclude_route)
             
             self.send_response(200)
             self.send_header('Content-type', 'application/json')
             self.end_headers()
             self.wfile.write(json.dumps(matches).encode())
        except Exception as e:
            print(f"Overlap search error: {e}")
            self.send_error(500, str(e))

def run_server():
    print(f"Starting Bus Analyzer Server on port {PORT}...")
    print(f"Open http://localhost:{PORT} in your browser.")
    
    # Pre-load DB
    global ROUTE_DB
    ROUTE_DB = analyze_route.get_json(BRIDGE_DB_URL)
    
    # Auto-Sync Logic
    try:
        pages_dir = "hk-bus-time-between-stops-pages"
        fetch_head = os.path.join(pages_dir, ".git", "FETCH_HEAD")
        
        should_sync = False
        if not os.path.exists(fetch_head):
            should_sync = True
            print("Status: No previous sync record found.")
        else:
            last_mtime = os.path.getmtime(fetch_head)
            if time.time() - last_mtime > 86400: # 24 hours
                should_sync = True
                print("Status: Data is older than 24 hours.")
            else:
                print("Status: Data is up to date (synced within 24h).")
                
        if should_sync:
            print("Auto-syncing data from GitHub...")
            subprocess.run(["bash", "sync_data.sh"], check=True)
    except Exception as e:
        print(f"Auto-sync failed: {e}")
    
    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    with ReusableTCPServer(("", PORT), BusRouteHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

if __name__ == "__main__":
    run_server()
