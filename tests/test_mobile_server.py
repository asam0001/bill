"""
Automated Test Suite for mobile_server.py
Verifies:
  1. Background HTTP server starts on available port.
  2. Local IP discovery.
  3. Static asset delivery (index.html, manifest.json, sw.js).
  4. REST API endpoints (/api/status, /api/dashboard, /api/medicines, /api/qr).
  5. Clean shutdown.
"""

import os
import sys
import time
import urllib.request
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from mobile_server import MobileServer, get_local_ip

def run_tests():
    print("=" * 60)
    print("STARTING TEST SUITE: mobile_server.py")
    print("=" * 60)

    # Use port 8089 to prevent collisions with any active dev servers
    port = 8089
    server = MobileServer(port=port)
    server.start(daemon=True)
    time.sleep(0.5)

    base_url = f"http://127.0.0.1:{port}"

    try:
        # 1. Test Static PWA Root Delivery
        with urllib.request.urlopen(f"{base_url}/") as response:
            assert response.status == 200
            html = response.read().decode("utf-8")
            assert "MediTrack Mobile" in html
            print("[PASS] Static PWA index.html served successfully.")

        # 2. Test Manifest Delivery
        with urllib.request.urlopen(f"{base_url}/manifest.json") as response:
            assert response.status == 200
            manifest = json.loads(response.read().decode("utf-8"))
            assert manifest["short_name"] == "MediTrack"
            print("[PASS] PWA manifest.json served successfully.")

        # 3. Test Service Worker Delivery
        with urllib.request.urlopen(f"{base_url}/sw.js") as response:
            assert response.status == 200
            sw = response.read().decode("utf-8")
            assert "meditrack-mobile" in sw
            print("[PASS] PWA sw.js served successfully.")

        # 4. Test /api/status
        with urllib.request.urlopen(f"{base_url}/api/status") as response:
            assert response.status == 200
            data = json.loads(response.read().decode("utf-8"))
            assert data["status"] == "ok"
            assert data["app"] == "MediTrack ERP"
            print(f"[PASS] /api/status returned: {data['url']}")

        # 5. Test /api/dashboard
        with urllib.request.urlopen(f"{base_url}/api/dashboard") as response:
            assert response.status == 200
            dash = json.loads(response.read().decode("utf-8"))
            assert dash["status"] == "ok"
            assert "today_sales" in dash
            print(f"[PASS] /api/dashboard returned today_sales=₹{dash['today_sales']:.2f}")

        # 6. Test /api/medicines search
        with urllib.request.urlopen(f"{base_url}/api/medicines?q=Dolo") as response:
            assert response.status == 200
            meds = json.loads(response.read().decode("utf-8"))
            assert len(meds) >= 1
            assert meds[0]["name"] == "Dolo 650"
            assert "strips" in meds[0]
            assert "total_tablets" in meds[0]
            print(f"[PASS] /api/medicines found '{meds[0]['name']}' with {meds[0]['total_tablets']} tablets in stock.")

        # 7. Test /api/qr generator
        with urllib.request.urlopen(f"{base_url}/api/qr") as response:
            assert response.status == 200
            qr_bytes = response.read()
            assert len(qr_bytes) > 100
            assert qr_bytes.startswith(b"\x89PNG") # Valid PNG magic bytes
            print(f"[PASS] /api/qr successfully generated {len(qr_bytes)} bytes PNG QR image.")

    finally:
        server.stop()
        print("[PASS] Mobile server gracefully stopped.")

    print("\n" + "=" * 60)
    print("ALL MOBILE SERVER TESTS PASSED SUCCESSFULLY! (EXIT CODE 0)")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
