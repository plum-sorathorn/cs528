import requests
import time
import argparse
import sys

def run_client(url, filename, interval=1.0):
    print(f"Starting client. Target: {url}, File: {filename}, Interval: {interval}s")
    print("Press Ctrl+C to stop.")
    print("-" * 50)
    
    request_count = 0
    zone_counts = {}

    try:
        while True:
            request_count += 1
            try:
                # Construct the full URL with filename parameter
                # Similar to how HW3/HW4 client behaves
                target_url = f"{url.rstrip('/')}/?filename={filename}"
                
                start_time = time.time()
                response = requests.get(target_url, timeout=5)
                latency = (time.time() - start_time) * 1000
                
                zone = response.headers.get('X-Zone', 'Unknown')
                status = response.status_code
                
                zone_counts[zone] = zone_counts.get(zone, 0) + 1
                
                print(f"[{request_count}] Status: {status} | Zone: {zone} | Latency: {latency:.2f}ms")
                
            except requests.exceptions.RequestException as e:
                print(f"[{request_count}] Error: {e}")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\nStopping client...")
        print("-" * 50)
        print(f"Total Requests: {request_count}")
        print("Zone Distribution:")
        for zone, count in zone_counts.items():
            percentage = (count / request_count) * 100 if request_count > 0 else 0
            print(f"  {zone}: {count} ({percentage:.2f}%)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HW8 Client for Load Balancer Testing")
    parser.add_argument("--url", required=True, help="Load Balancer URL (e.g., http://34.1.2.3)")
    parser.add_argument("--file", default="0.html", help="Filename to request (default: 0.html)")
    parser.add_argument("--interval", type=float, default=1.0, help="Interval between requests in seconds (default: 1.0)")
    
    args = parser.parse_args()
    
    run_client(args.url, args.file, args.interval)
