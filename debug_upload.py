import requests
import os

# Create a dummy MD file
md_content = """
# Daily Drilling Report
## Well: Bakte-9
## Date: 2023-10-27

Current Depth: 12500 ft
Mud Weight: 10.5 ppg
Viscosity: 45 sec
Flow Rate: 450 gpm
SPP: 2200 psi
RPM: 120
WOB: 15 klb
Torque: 8500 ft-lb
Activity: Drilling 8.5" hole section. No issues.
"""

filename = "test_upload.md"
with open(filename, "w") as f:
    f.write(md_content)

url = "http://localhost:8000/events/extract"

try:
    with open(filename, "rb") as f:
        files = {"file": (filename, f, "text/markdown")}
        print(f"Uploading {filename} to {url}...")
        response = requests.post(url, files=files)
        
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

except Exception as e:
    print(f"Error: {e}")

finally:
    if os.path.exists(filename):
        os.remove(filename)
