import requests
import json
import time

base_url = "http://localhost:8000"

def run_flow():
    # 1. Create Event
    url = f"{base_url}/events"
    payload = {
        "phase": "Perforación",
        "family": "Pozo / Geomecánica",
        "parameters": {},
        "workflow": ["rca_lead"],
        "well_id": 1
    }

    try:
        print(f"1. Sending POST to {url}")
        response = requests.post(url, json=payload)
        print(f"   Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Error: {response.text}")
            return
        
        data = response.json()
        event_id = data["id"]
        problem_id = data["problem_id"]
        print(f"   Success. EventID: {event_id}, ProblemID: {problem_id}")

        # 2. Physics (Async - but in App.tsx it's awaited lightly or fired)
        url_calc = f"{base_url}/events/{event_id}/calculate"
        print(f"2. Sending POST to {url_calc}")
        resp_calc = requests.post(url_calc)
        print(f"   Status: {resp_calc.status_code}")
        # Not blocking, but check if it crashes 500

        # 3. Init Analysis
        url_init = f"{base_url}/problems/{problem_id}/analysis/init"
        payload_init = {
            "workflow": ["rca_lead"]
        }
        print(f"3. Sending POST to {url_init}")
        resp_init = requests.post(url_init, json=payload_init)
        print(f"   Status: {resp_init.status_code}")
        if resp_init.status_code != 200:
            print(f"   Error: {resp_init.text}")
            return
        
        print("   Success. Analysis Initialized.")
        print("Full flow complete.")

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    run_flow()
