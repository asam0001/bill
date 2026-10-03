# 💊 MediTrack ERP — Medical Shop & Pharmacy Management System

> **Production-Quality, Offline-First Medical Shop Management System for Laptops, PCs, and Mobile Devices (Android & iOS).**

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS%20%7C%20Android-166534.svg)]()
[![Offline First](https://img.shields.io/badge/Offline-100%25%20No%20Internet%20Required-success.svg)]()
[![Database](https://img.shields.io/badge/Database-SQLite%20WAL%20v2-orange.svg)]()

---

## 📌 Executive Summary

**MediTrack ERP** is an offline-first pharmacy and medical shop management application engineered for speed, mathematical accuracy, batch traceability, and transaction durability. Unlike web-based solutions that freeze when the internet drops, MediTrack operates **100% offline**, allowing pharmacies to bill customers, receive distributor shipments, track loose tablets, and audit financials without cloud dependencies.

To support pharmacists and assistants moving around the store aisles, MediTrack provides a complete cross-platform mobile suite:
1. **Instant Offline Mobile PWA**: Runs on Android, iPhone, and iPad over local shop Wi-Fi or laptop hotspot with camera barcode scanning and shelf locator.
2. **Native Android Companion App**: A full Android Studio project in `android_app/` capable of building a native Android APK package.
3. **Standalone Windows Executable**: A zero-dependency Windows desktop package in `dist/MediTrack/` with an instant 1-click launcher.

---

## 🏗️ Architecture & Core Principles

```
                               ┌──────────────────────────────────────────────┐
                               │           MediTrack Desktop Core             │
                               │        (Windows / Linux / macOS PC)          │
                               │  - CustomTkinter UI (Deep Emerald Theme)     │
                               │  - Python 3.10+ Central Financial Engine     │
                               │  - ReportLab PDF Invoices / openpyxl Reports │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                                      ▼
                      ┌──────────────────────────────────────────────────────────────┐
                      │              Authoritative SQLite Database Engine            │
                      │  - WAL Journal Mode (Non-blocking concurrent reads/writes)   │
                      │  - Single Source of Truth: total_tablets                     │
                      │  - Schema Version 2 Auto-Migration Runner                    │
                      │  - In-Transaction Atomic Rollback Guarantees                 │
                      └──────────────────────────────┬───────────────────────────────┘
                                                     │
                                                     ▼
                               ┌──────────────────────────────────────────────┐
                               │           Mobile Companion Server            │
                               │          (Offline LAN / WLAN Host)           │
                               │  - Zero-dependency Python ThreadingHTTPServer│
                               │  - REST API & Real-Time Stock Feeds          │
                               └──────────────────────┬───────────────────────┘
                                                      │
                         ┌────────────────────────────┴────────────────────────────┐
                         ▼                                                         ▼
    ┌─────────────────────────────────────────────┐         ┌─────────────────────────────────────────────┐
    │          Mobile Companion PWA               │         │        Native Android Companion APK         │
    │         (Android / iPhone / iPad)           │         │              (Android Studio)               │
    │  - Camera Barcode & QR Box Scanner          │         │  - Full-screen immersion & Hardware camera  │
    │  - Fast Aisle Stock & Rack-Shelf Locator    │         │  - Local LAN Cleartext HTTP Communication   │
    │  - Mobile Counter Sales Assistant           │         │  - Standalone APK for store mobile fleet    │
    │  - Zero-Build "Add to Home Screen"          │         │  - Located in `android_app/`                │
    └─────────────────────────────────────────────┘         └─────────────────────────────────────────────┘
```

### Core Invariants
1. **Authoritative Stock Single Source of Truth**: `total_tablets` is the sole authoritative inventory unit in `medicine_batches`. Strips and loose tablets are dynamically derived (`strips = total_tablets // tablets_per_strip`, `loose = total_tablets % tablets_per_strip`).
2. **Financial Precision via `Decimal`**: Centralized in `utils/money.py`. All money calculations use Python's `Decimal` with commercial `ROUND_HALF_UP` rounding. Floating-point binary representation errors are completely eliminated.
3. **Expiry Enforcement**:
   - **Procurement**: Dispensing or procuring expired medicines from distributors is blocked at data entry.
   - **Dispensing**: Expired stock cannot be billed at POS without authenticated administrative override with an immutable audit record.
4. **Duplicate Purchase Protection**: Multiple entries of the same distributor invoice (`supplier_id + purchase_invoice_number`) are rejected before touching stock.
5. **Non-Blocking Disaster Recovery**: Uses SQLite's native **Online Backup API** (`sqlite3.Connection.backup()`), deep pre-restore verification, and automatic pre-restore emergency snapshots.

---

## 💻 Desktop Installation & Running (Laptop / PC)

### Option A: Standalone Windows App (No Python Required)
1. Download or extract the pre-built `dist/MediTrack-v2.0-Windows-Portable.zip`.
2. Extract the folder to any location on your PC or USB drive.
3. Double-click `MediTrack.exe` or `Launch MediTrack.bat`.
4. (Optional) Run `create_desktop_shortcut.bat` to place a shortcut directly on your Windows Desktop.

### Option B: From Source (Windows, Linux, macOS)
1. Ensure **Python 3.10+** is installed ([python.org](https://www.python.org/downloads/)).
2. Clone this repository:
   ```bash
   git clone https://github.com/<your-username>/meditrack-erp.git
   cd meditrack-erp
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Seed demo pharmacy data (Optional):
   ```bash
   python seed_data.py
   ```
5. Launch the application:
   - **Windows**: Double-click `run.bat`
   - **Linux / macOS**: Run `./run.sh`
   - **Command Line**:
     ```bash
     python main.py
     ```

Default administrative login:
- **Username**: `admin`
- **Password**: `admin123`
- **Role**: `Admin` *(Pharmacist and Cashier accounts also supported)*

---

## 📱 Mobile Applications (Phone / Tablet)

MediTrack includes two ready-to-use mobile solutions that operate **100% offline** over local Wi-Fi:

### Pathway 1: Instant Offline PWA (Recommended — Zero Build Required)
1. Connect your mobile phone and PC/laptop to the same Wi-Fi router or laptop **Mobile Hotspot**.
2. Start MediTrack on your PC.
3. Go to **⚙️ System Settings** $\rightarrow$ **Mobile Companion Pairing**.
4. Scan the displayed QR code with your mobile camera, or open Chrome/Safari and visit the URL shown on screen (e.g. `http://192.168.1.15:8080`).
5. In your mobile browser, tap **"Add to Home Screen"** or **"Install MediTrack"**.
6. The app opens full-screen with offline caching, camera barcode scanner, and shelf locator.

### Pathway 2: Native Android Application (Android Studio / APK)
A full native Android Gradle project is included in `android_app/`:
1. Open **Android Studio**.
2. Choose **Open** and select the `android_app` folder.
3. Allow Gradle to sync.
4. Click **Build** $\rightarrow$ **Build Bundle(s) / APK(s)** $\rightarrow$ **Build APK(s)**.
5. Transfer the generated `.apk` to any Android phone or tablet in your pharmacy.

### Mobile Features:
- 🔍 **Aisle Stock Checker**: Search medicines to see instant stock in strips and loose tablets.
- 📍 **Shelf & Rack Locator**: Instantly displays where the medicine is kept (e.g. `Rack B - Shelf 2 (Antibiotics)`).
- 📷 **Camera Barcode Scanner**: Scan barcodes on medicine boxes using your phone camera to inspect batch expiry and pricing.
- 🧾 **Quick Counter Billing**: Add items to cart, compute taxes, and send orders straight to the PC cash register.
- 📈 **Owner Dashboard**: View today's total sales, profit, bill count, and low-stock alerts on the go.

---

## 📦 Building Desktop Executables & Portable ZIPs

To compile a standalone Windows desktop executable that can be distributed on USB sticks or downloaded without needing Python:

```bash
python build_desktop.py
```

This automated builder:
1. Embeds custom high-resolution application icons (`assets/icon.ico`).
2. Bundles the offline mobile PWA, assets, and CustomTkinter themes.
3. Packages a standalone executable in `dist/MediTrack/MediTrack.exe`.
4. Automatically generates a portable distribution ZIP: `dist/MediTrack-v2.0-Windows-Portable.zip`.

---

## 🌐 Git Sharing & Remote Repository Setup

To share this codebase via GitHub, GitLab, or Bitbucket:

### 1. Push to Remote Repository
```bash
# Set your preferred remote URL (e.g., GitHub)
git remote add origin https://github.com/<your-username>/meditrack-erp.git

# Rename default branch to main
git branch -M main

# Push all source code, assets, and documentation
git push -u origin main
```

### 2. Cloning on Another PC or Laptop
When cloning to another computer:
```bash
git clone https://github.com/<your-username>/meditrack-erp.git
cd meditrack-erp
pip install -r requirements.txt
python seed_data.py
python main.py
```
*Note: User transactional databases (`medical_shop.db`), backup dumps, and compiled binaries are excluded by `.gitignore` to maintain clean repository hygiene.*

---

## 🧪 Automated Test Suite & Quality Assurance

MediTrack includes an automated test harness covering financial calculations, transaction concurrency, database migrations, and disaster recovery:

```bash
# Run unit & domain services tests
python tests/test_purchase_service.py
python tests/test_backup_service.py
python tests/test_audit_service.py
python tests/test_mobile_server.py

# Run end-to-end system regression test
python verify_system.py
```

All test suites verify their operations in isolated sandboxes and exit with code `0`.

---

## 📂 Project Structure

```
medical_shop/
├── android_app/            # Native Android Studio Project (Gradle, Manifest, Java)
│   ├── app/
│   │   ├── src/main/java/  # MainActivity.java (Camera, WebChromeClient, WebView)
│   │   ├── src/main/res/   # Mipmaps, themes, layouts, network_security_config
│   │   └── build.gradle    # Android SDK 34 build configuration
│   ├── settings.gradle
│   └── README.md
├── assets/                 # Application branding, icons & graphics
│   ├── icon.ico            # Multi-resolution Windows desktop icon (16px to 256px)
│   └── icon.png            # High-resolution 512x512 emblem
├── database/
│   ├── db.py               # Core SQLite connection, WAL mode, pragmas, schema v2
│   └── migrations.py       # Idempotent version migration & foreign-key repair engine
├── ui/
│   ├── main_window.py      # Main application window & responsive tab switcher
│   ├── theme.py            # Deep Emerald visual design tokens & palettes
│   ├── components.py       # Reusable buttons, cards, badges, and search inputs
│   ├── home.py             # Executive dashboard & real-time store metrics
│   ├── billing.py          # POS checkout, F-key shortcuts, batch drawers
│   ├── stock.py            # Inventory management, strip & loose pill counts
│   ├── expiry.py           # FEFO batch expiry tracker & critical alerts
│   ├── purchases.py        # Distributor invoice receiving & batch intake
│   ├── returns.py          # Customer sales returns & supplier return debits
│   ├── suppliers.py        # Supplier profiles & accounts payable ledger
│   ├── customers.py        # Patient credit limits & accounts receivable ledger
│   ├── reports.py          # Profitability analytics, Excel exports, date filters
│   └── settings.py         # Shop branding, mobile pairing QR, online backup
├── utils/
│   ├── money.py            # Centralized Decimal financial & commercial rounding engine
│   ├── medicine_service.py # Authoritative stock engine, FEFO queries, adjustments
│   ├── sales_service.py    # POS billing, credit checks, double-check concurrency
│   ├── purchase_service.py # Distributor procurement, duplicate invoice protection
│   ├── backup_service.py   # SQLite Online Backup API, pre-restore verification
│   ├── audit_service.py    # Immutable audit logging with structured JSON deltas
│   ├── customer_service.py # Patient ledger & credit balance management
│   ├── supplier_service.py # Distributor ledger & payment tracking
│   ├── dashboard_service.py# Aggregated sales, profit, and stock metrics
│   └── pdf_service.py      # Thermal & A4 ReportLab invoice PDF generator
├── mobile/
│   ├── index.html          # Mobile PWA touch interface & camera barcode scanner
│   ├── manifest.json       # Progressive Web App manifest
│   ├── sw.js               # Service Worker for offline app shell caching
│   ├── icon.png            # 512x512 PWA app icon
│   ├── icon-192.png        # 192x192 home screen icon
│   └── favicon.ico         # Browser tab icon
├── tests/
│   ├── test_purchase_service.py
│   ├── test_backup_service.py
│   ├── test_audit_service.py
│   └── test_mobile_server.py
├── mobile_server.py        # Lightweight LAN HTTP server & REST API
├── seed_data.py            # Realistic pharmacy database seeder
├── main.py                 # Desktop application entry point
├── verify_system.py        # End-to-end integration regression test suite
├── run.bat                 # 1-Click Windows PC/Laptop launcher
├── run.sh                  # 1-Click Linux/macOS launcher
├── create_desktop_shortcut.bat # Windows desktop shortcut generator
├── build_desktop.py        # Standalone PyInstaller Windows .exe builder
├── generate_assets.py      # Icon and visual asset generation script
├── requirements.txt        # Python dependency manifest
├── .gitignore              # Git repository ignore rules
└── README.md               # Complete documentation
```

---

## 🔒 Security & Data Integrity

- **Offline Independence**: MediTrack stores all operational data locally on the host machine. No external servers or telemetry are contacted.
- **Auditing**: Every critical administrative action (dispensing expired drugs via override, manual stock adjustments, database restorations, price modifications) is recorded in `audit_logs` with timestamps, authorized user, and pre/post JSON state deltas.
- **Concurrency & WAL Mode**: SQLite operates in `journal_mode = WAL` with a 5000ms busy timeout, supporting seamless concurrent operations between the desktop POS terminal and mobile companion devices.

---

## 📄 License & Distribution

MediTrack ERP is open-source and free for medical shops, community pharmacies, and healthcare clinics.
Shared through Git, network drives, or standalone portable packages.
