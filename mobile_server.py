"""
MediTrack ERP - Mobile Companion LAN Server
Serves the offline-first Mobile Pharmacy PWA and REST API over local Wi-Fi / Hotspot.
Allows smartphones and tablets in the shop to scan barcodes, check stock & shelf locations, and bill counter sales.
Requires zero external dependencies (uses standard library http.server and socket).
"""

import os
import sys
import io
import json
import socket
import threading
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import shutil
from typing import Any, Optional, Dict, List
from datetime import datetime

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database.db import get_connection
from utils.settings_service import get_all_settings
from utils.dashboard_service import get_dashboard_stats
from utils.medicine_service import search_medicines, get_expiring_soon_medicines, get_low_stock_medicines
from utils.sales_service import record_sale


def get_local_ip() -> str:
    """Discovers the active LAN / Wi-Fi IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class MobileAPIRequestHandler(BaseHTTPRequestHandler):
    """Handles static PWA delivery and REST API operations for mobile devices."""

    def log_message(self, format, *args):
        # Suppress noisy HTTP access logs in console
        pass

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, filepath: str, content_type: str):
        if not os.path.exists(filepath):
            self.send_error(404, "File Not Found")
            return
        with open(filepath, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # 1. Static Web App & PWA Assets
        mobile_dir = os.path.join(BASE_DIR, "mobile")
        if path in ("/", "/index.html"):
            return self._serve_file(os.path.join(mobile_dir, "index.html"), "text/html; charset=utf-8")
        elif path == "/manifest.json":
            return self._serve_file(os.path.join(mobile_dir, "manifest.json"), "application/manifest+json")
        elif path == "/sw.js":
            return self._serve_file(os.path.join(mobile_dir, "sw.js"), "application/javascript")
        elif path in ("/icon.png", "/icon-192.png"):
            fname = "icon.png" if path == "/icon.png" else "icon-192.png"
            return self._serve_file(os.path.join(mobile_dir, fname), "image/png")
        elif path == "/favicon.ico":
            return self._serve_file(os.path.join(mobile_dir, "favicon.ico"), "image/x-icon")
        elif path in ("/download", "/download/zip", "/MediTrack-v2.0-Windows-Portable.zip", "/v2.0-windows-portable.zip"):
            zip_path = os.path.join(BASE_DIR, "dist", "MediTrack-v2.0-Windows-Portable.zip")
            if os.path.exists(zip_path):
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", 'attachment; filename="MediTrack-v2.0-Windows-Portable.zip"')
                self.send_header("Content-Length", str(os.path.getsize(zip_path)))
                self.end_headers()
                with open(zip_path, "rb") as f:
                    shutil.copyfileobj(f, self.wfile)
                return
            else:
                self.send_error(404, "Portable ZIP package not found on server.")
                return

        # 2. REST API: Server Status & Pairing Info
        if path == "/api/status":
            settings = get_all_settings()
            ip = get_local_ip()
            return self._send_json({
                "status": "ok",
                "app": "MediTrack ERP",
                "version": settings.get("app_version", "2.0.0"),
                "shop_name": settings.get("shop_name", "MediTrack Pharmacy"),
                "ip": ip,
                "port": self.server.server_port,
                "url": f"http://{ip}:{self.server.server_port}"
            })

        # 3. REST API: Dashboard Stats
        elif path == "/api/dashboard":
            kpis = get_dashboard_stats()
            settings = get_all_settings()
            expiring = get_expiring_soon_medicines(days_threshold=90)
            return self._send_json({
                "status": "ok",
                "today_sales": float(kpis.get("today_sales", 0.0)),
                "today_profit": float(kpis.get("today_profit", 0.0)),
                "bills_count": int(kpis.get("today_bills", 0)),
                "low_stock_count": int(kpis.get("low_stock_count", 0)),
                "shop_name": settings.get("shop_name", "MediTrack Pharmacy"),
                "shop_address": settings.get("address", "Local Network"),
                "expiring_items": expiring[:8]
            })

        # 4. REST API: Search Medicines & Stock Check
        elif path == "/api/medicines":
            query = params.get("q", [""])[0].strip()
            results = search_medicines(query)
            return self._send_json(results[:50])

        # 5. REST API: Expiry Alerts
        elif path == "/api/expiry":
            days = int(params.get("days", [90])[0])
            expiring = get_expiring_soon_medicines(days_threshold=days)
            return self._send_json(expiring)

        # 6. REST API: QR Code Image for Instant Mobile Pairing
        elif path == "/api/qr":
            try:
                import qrcode
                ip = get_local_ip()
                url = f"http://{ip}:{self.server.server_port}"
                qr = qrcode.QRCode(box_size=8, border=2)
                qr.add_data(url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="#166534", back_color="white")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)
                qr_bytes = buf.getvalue()

                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(qr_bytes)))
                self.end_headers()
                self.wfile.write(qr_bytes)
                return
            except Exception as ex:
                return self._send_json({"error": f"QR generation error: {ex}"}, status=500)

        else:
            self.send_error(404, "Endpoint Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/sales":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                post_body = self.rfile.read(content_len).decode("utf-8")
                payload = json.loads(post_body)

                c_name = payload.get("customer_name") or "Walk-in Cash Patient"
                c_phone = payload.get("customer_phone") or ""
                p_mode = payload.get("payment_mode") or "Cash"
                disc_pct = float(payload.get("discount_percent") or 0.0)
                items = payload.get("cart_items") or []

                if not items:
                    return self._send_json({"status": "error", "error": "Cart is empty."}, status=400)

                # Process transaction atomically
                bill_number = record_sale(
                    customer_id=None,
                    customer_name=c_name,
                    customer_phone=c_phone,
                    payment_mode=p_mode,
                    cart_items=items,
                    discount_percent=disc_pct
                )

                return self._send_json({
                    "status": "ok",
                    "bill_number": bill_number,
                    "message": f"Sale recorded successfully as #{bill_number}"
                })

            except Exception as ex:
                return self._send_json({"status": "error", "error": str(ex)}, status=400)
        else:
            self.send_error(404, "Endpoint Not Found")


class MobileServer:
    """Manages the lifecycle of the local mobile companion server."""

    def __init__(self, port: int = 8080):
        self.port = port
        self.httpd = None
        self.thread = None
        self.is_running = False

    def start(self, daemon: bool = True):
        """Starts the HTTP server on 0.0.0.0 in a background thread."""
        if self.is_running:
            return

        try:
            self.httpd = ThreadingHTTPServer(("0.0.0.0", self.port), MobileAPIRequestHandler)
            self.is_running = True
            self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=daemon)
            self.thread.start()
            ip = get_local_ip()
            print(f"[MOBILE SERVER] Running at http://{ip}:{self.port} (Offline Local Network)")
        except Exception as ex:
            self.is_running = False
            print(f"[MOBILE SERVER] Failed to bind to port {self.port}: {ex}")

    def stop(self):
        """Gracefully shuts down the HTTP server."""
        if self.httpd and self.is_running:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.is_running = False
            print("[MOBILE SERVER] Stopped.")


# Global singleton instance for use by desktop app
_server_instance: Optional[MobileServer] = None


def get_mobile_server(port: int = 8080) -> MobileServer:
    global _server_instance
    if _server_instance is None:
        _server_instance = MobileServer(port=port)
    return _server_instance


def start_mobile_server_background(port: int = 8080) -> str:
    """Helper to start server in background and return its access URL."""
    srv = get_mobile_server(port)
    srv.start(daemon=True)
    ip = get_local_ip()
    return f"http://{ip}:{port}"


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = MobileServer(port=port_arg)
    print("=" * 60)
    print("MediTrack Mobile Companion Server")
    print(f"Local Access:   http://localhost:{port_arg}")
    print(f"Mobile Wi-Fi:   http://{get_local_ip()}:{port_arg}")
    print("Point phone camera at PC screen or connect via local Wi-Fi.")
    print("Press Ctrl+C to terminate.")
    print("=" * 60)
    try:
        server.start(daemon=False)
    except KeyboardInterrupt:
        server.stop()
