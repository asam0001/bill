# 💊 MediTrack ERP — Production-Quality Medical Shop & Pharmacy Management System

> **A Dependable, Offline-First Medical Shop Management System for Laptops, PCs, and Mobile Devices (Android & iOS).**

[![Application Version](https://img.shields.io/badge/Version-2.0.0-166534.svg)]()
[![Python Runtime](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![UI Framework](https://img.shields.io/badge/GUI-CustomTkinter-0284C7.svg)](https://github.com/TomSchimansky/CustomTkinter)
[![Database Engine](https://img.shields.io/badge/Database-SQLite%203%20WAL-orange.svg)]()
[![Platform Support](https://img.shields.io/badge/Platforms-Windows%20%7C%20Linux%20%7C%20macOS%20%7C%20Android%20%7C%20iOS-16A34A.svg)]()
[![Offline Guarantee](https://img.shields.io/badge/Offline-100%25%20No%20Internet%20Required-success.svg)]()

---

## 📑 Table of Contents

1. [Executive Overview & Philosophy](#-1-executive-overview--philosophy)
2. [Visual Identity & Design System](#-2-visual-identity--design-system)
3. [Architecture & Core Invariants](#-3-architecture--core-invariants)
   - [Authoritative Stock Single Source of Truth](#authoritative-stock-single-source-of-truth)
   - [Centralized Financial Decimal Engine](#centralized-financial-decimal-engine)
   - [Expiry Safety Enforcement & Audit Override](#expiry-safety-enforcement--audit-override)
   - [Distributor Procurement & Duplicate Protection](#distributor-procurement--duplicate-protection)
   - [Disaster Recovery & Non-Blocking Backup Engine](#disaster-recovery--non-blocking-backup-engine)
   - [Immutable Audit Trail Engine](#immutable-audit-trail-engine)
4. [System Architecture Diagram](#-4-system-architecture-diagram)
5. [Getting Started & Installation Guide](#-5-getting-started--installation-guide)
   - [Method A: Standalone Windows App (No Python Required)](#method-a-standalone-windows-app-no-python-required)
   - [Method B: Running from Source (Windows, Linux, macOS)](#method-b-running-from-source-windows-linux-macos)
   - [First-Time Database Seeding](#first-time-database-seeding)
   - [Default Login Credentials](#default-login-credentials)
6. [Desktop Application Modules (Detailed Walkthrough)](#-6-desktop-application-modules-detailed-walkthrough)
   - [1. Executive Dashboard](#1-executive-dashboard)
   - [2. Billing & Point of Sale (POS)](#2-billing--point-of-sale-pos)
   - [3. Purchases & Distributor Intake](#3-purchases--distributor-intake)
   - [4. Stock Inventory Management](#4-stock-inventory-management)
   - [5. FEFO Expiry Tracker](#5-fefo-expiry-tracker)
   - [6. Suppliers & Accounts Payable](#6-suppliers--accounts-payable)
   - [7. Customers & Accounts Receivable](#7-customers--accounts-receivable)
   - [8. Sales History & Returns Manager](#8-sales-history--returns-manager)
   - [9. Financial Reports & Analytics](#9-financial-reports--analytics)
   - [10. Accounts & Day-Book Ledger](#10-accounts--day-book-ledger)
   - [11. System Settings & Configuration](#11-system-settings--configuration)
7. [Mobile Companion Application Suite](#-7-mobile-companion-application-suite)
   - [Offline Local Network Server](#offline-local-network-server)
   - [Option 1: Zero-Build Mobile PWA](#option-1-zero-build-mobile-pwa)
   - [Option 2: Native Android Studio Application](#option-2-native-android-studio-application)
   - [Mobile Capabilities & Workflow](#mobile-capabilities--workflow)
8. [Database Engine & Migration Architecture](#-8-database-engine--migration-architecture)
   - [WAL Mode & Concurrency Pragmas](#wal-mode--concurrency-pragmas)
   - [Schema Version 2 Tables & Relationships](#schema-version-2-tables--relationships)
   - [Idempotent Migration Engine](#idempotent-migration-engine)
9. [Packaging, Distribution & Git Repository Setup](#-9-packaging-distribution--git-repository-setup)
   - [Building Windows Executable (`build_desktop.py`)](#building-windows-executable-build_desktoppy)
   - [Portable USB Distribution ZIP](#portable-usb-distribution-zip)
   - [Windows Desktop Shortcut Generator](#windows-desktop-shortcut-generator)
   - [Git Repository Sharing & Remote Setup](#git-repository-sharing--remote-setup)
10. [Automated Quality Assurance & Test Suites](#-10-automated-quality-assurance--test-suites)
11. [Troubleshooting & Frequently Asked Questions (FAQ)](#-11-troubleshooting--frequently-asked-questions-faq)

---

## 🏥 1. Executive Overview & Philosophy

**MediTrack ERP** is an offline-first pharmacy and medical store management platform developed specifically for community pharmacies, retail medical stores, and hospital chemists. 

In real-world retail healthcare environments, internet outages, bandwidth throttling, and cloud downtime are intolerable risks: customers waiting for critical prescriptions cannot be delayed by network errors. MediTrack is built on the fundamental principle that **100% of core pharmacy operations must execute entirely offline without an active internet connection**.

### What MediTrack Solves:
- **Tablet & Strip Precision**: Eliminates fractional inventory mismatches by deriving strips and loose pills dynamically from an authoritative integer tablet count.
- **Financial Correctness**: Eliminates binary floating-point rounding errors (`0.1 + 0.2 != 0.3`) through a centralized Python `Decimal` accounting engine with commercial `ROUND_HALF_UP` rounding.
- **Expiry Compliance**: Prevents illegal intake of expired medicines from distributors and strictly blocks billing of expired stock at the point of sale without an auditable administrative override.
- **Dual-Device Mobility**: Enables staff to use their personal smartphones inside store aisles to scan medicine box barcodes, locate shelf bins, and enter counter bills via local shop Wi-Fi without third-party cloud hosting.
- **Disaster Durability**: Leverages SQLite's native Online Backup API for zero-lock live backups and pre-restore integrity audits with emergency rollback snapshots.

---

## 🎨 2. Visual Identity & Design System

MediTrack uses a custom healthcare color palette crafted for clarity, visual comfort during long shifts, and high legibility across desktop monitors and mobile touchscreens.

### Core Palette

| Role | Color Name | Hex Code | Visual Preview | Application Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Primary** | Deep Emerald | `#166534` | ![#166534](https://via.placeholder.com/15/166534/000000?text=+) | Primary action buttons, active sidebar tab, header bars |
| **Primary Light** | Soft Sage | `#DCFCE7` | ![#DCFCE7](https://via.placeholder.com/15/DCFCE7/000000?text=+) | Healthy status pill, selection highlights, badge fills |
| **Sidebar BG** | Dark Forest | `#092419` | ![#092419](https://via.placeholder.com/15/092419/000000?text=+) | Persistent desktop sidebar navigation frame |
| **Window BG** | Warm Off-White | `#F7F8F6` | ![#F7F8F6](https://via.placeholder.com/15/F7F8F6/000000?text=+) | Main application background (reduces eye strain) |
| **Cards & Panels** | Pure White | `#FFFFFF` | ![#FFFFFF](https://via.placeholder.com/15/FFFFFF/000000?text=+) | Form cards, tables, dashboard widgets, modal dialogs |
| **Borders** | Soft Gray | `#E5E7E5` | ![#E5E7E5](https://via.placeholder.com/15/E5E7E5/000000?text=+) | Container outlines, table gridlines, separator rules |
| **Main Text** | Charcoal | `#171A17` | ![#171A17](https://via.placeholder.com/15/171A17/000000?text=+) | Primary typography, headers, table data |
| **Secondary Text**| Slate Gray | `#647067` | ![#647067](https://via.placeholder.com/15/647067/000000?text=+) | Subtitles, field labels, metadata, timestamps |

### Status Classification Colors

| Status | Color Name | Hex Code | Pharmacy Semantic Meaning |
| :--- | :--- | :--- | :--- |
| **Success** | Emerald | `#16A34A` | Healthy stock, paid invoice, valid batch |
| **Warning** | Amber | `#D97706` | Low stock threshold reached, expiring in 30-90 days |
| **Danger** | Crimson Red | `#DC2626` | Expired stock, stockout, payment overdue |
| **Information** | Cobalt Blue | `#2563EB` | Customer credit limit warning, system notification |
| **Special** | Violet | `#7C3AED` | Administrative override, audit event, scheduled job |

---

## 🏛️ 3. Architecture & Core Invariants

MediTrack enforces 6 mission-critical business invariants across its database and service layer.

---

### Authoritative Stock Single Source of Truth
In retail pharmacies, medicine is received in strips or boxes but frequently dispensed as loose tablets. Many simple pharmacy systems track strips as floats (e.g. `9.66 strips`), causing floating-point rounding errors and inventory drift.

**MediTrack Rule**:
The authoritative inventory quantity stored in `medicine_batches` is strictly:
$$\text{total\_tablets} \in \mathbb{Z}_{\ge 0}$$

Strips and loose tablets are **always dynamically derived**:
$$\text{full\_strips} = \lfloor \text{total\_tablets} / \text{tablets\_per\_strip} \rfloor$$
$$\text{loose\_tablets} = \text{total\_tablets} \pmod{\text{tablets\_per\_strip}}$$

*Example*: If a batch has $\text{tablets\_per\_strip} = 15$ and $\text{total\_tablets} = 145$:
- Full strips: $145 // 15 = 9\text{ strips}$
- Loose tablets: $145 \% 15 = 10\text{ tablets}$
- Display: **9 strips + 10 loose tablets**

---

### Centralized Financial Decimal Engine
Floating-point binary arithmetic (`float`) cannot accurately represent decimal currency (e.g. `0.1 + 0.2 = 0.30000000000000004`). In a pharmacy processing thousands of line items, floating-point drift creates cumulative discrepancies in tax audits and cash registers.

**MediTrack Rule**:
All monetary calculations are centralized in [`utils/money.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/utils/money.py) using Python's `Decimal` type with explicit commercial rounding (`ROUND_HALF_UP`) to 2 decimal places:
- **Tablet Unit Price**:
  $$\text{tablet\_price} = \text{quantize}\left(\frac{\text{strip\_selling\_price}}{\text{tablets\_per\_strip}}\right)$$
- **Line Item Subtotal**:
  $$\text{subtotal} = \text{quantize}(\text{quantity} \times \text{unit\_price})$$
- **Line Item Discount**:
  $$\text{discount\_amt} = \text{quantize}\left(\text{subtotal} \times \frac{\text{discount\_percent}}{100}\right)$$
- **GST / Tax Split (CGST + SGST)**:
  $$\text{taxable\_base} = \text{subtotal} - \text{discount\_amt}$$
  $$\text{cgst\_amt} = \text{quantize}\left(\text{taxable\_base} \times \frac{\text{gst\_percent}}{200}\right)$$
  $$\text{sgst\_amt} = \text{quantize}\left(\text{taxable\_base} \times \frac{\text{gst\_percent}}{200}\right)$$

---

### Expiry Safety Enforcement & Audit Override
Selling expired medicine is illegal and poses severe patient health hazards. MediTrack enforces two layers of expiry protection:

1. **Procurement Intake Block**: When recording distributor purchase invoices in `purchase_service.py`, any line item whose expiry date has already passed is immediately rejected before touching database tables.
2. **Point of Sale Dispensing Block**: When a cashier scans or bills a batch that has expired ($\text{expiry\_date} < \text{current\_date}$):
   - The transaction is blocked with an alert: `Batch is expired and cannot be dispensed.`
   - In rare medical emergencies or authorized disposal scenarios, an administrator can authorize an **Audited Expiry Override** (`authorize_expired_sale_override`). This writes an immutable, timestamped record into `audit_logs` containing the supervisor's user ID, reason, batch number, and patient details.

---

### Distributor Procurement & Duplicate Protection
In high-volume stores, distracted staff might re-enter a distributor invoice or scan the same bill twice, artificially inflating inventory and supplier accounts payable.

**MediTrack Rule**:
1. **Duplicate Invoice Protection**: A compound uniqueness check on $(\text{supplier\_id}, \text{purchase\_invoice\_number})$ validates that the invoice has not already been recorded. Attempting duplicate entry aborts with the original purchase ID and entry timestamp.
2. **Pricing Bounds Validation**:
   $$\text{Purchase Rate} \le \text{Selling Price} \le \text{MRP}$$
   Selling price cannot exceed Maximum Retail Price (MRP). Purchase cost cannot exceed MRP.

---

### Disaster Recovery & Non-Blocking Backup Engine
Traditional SQLite file copying (`shutil.copyfile`) on a live, WAL-enabled database can capture half-written pages, causing corrupted backups.

**MediTrack Rule**:
Implemented in [`utils/backup_service.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/utils/backup_service.py):
1. **Online Backup API**: Uses SQLite's native `sqlite3.Connection.backup()` to stream pages consistently without locking POS terminals.
2. **Pre-Restore Verification**: Before restoring any backup, `verify_backup_integrity()` performs an explicit integrity check (`PRAGMA integrity_check`), inspects table structures, and checks the schema version. If corrupt, restoration is aborted.
3. **Emergency Pre-Restore Safety Snapshot**: Before replacing the active database, the engine automatically creates a timestamped safety snapshot: `pre_restore_safety_YYYY_MM_DD_HH_MM_SS.db`. If a user accidentally restores an old backup, their current data can be recovered.

---

### Immutable Audit Trail Engine
All critical operations are logged into `audit_logs` via [`utils/audit_service.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/utils/audit_service.py):
- User ID and role.
- Action type (`STOCK_ADJUSTMENT`, `EXPIRED_SALE_OVERRIDE`, `DATABASE_RESTORE`, `PRICE_UPDATE`, `PURCHASE_RETURN`).
- Pre-mutation state snapshot (`old_values` serialized as JSON).
- Post-mutation state snapshot (`new_values` serialized as JSON).
- In-transaction cursor reuse to prevent database lock contention.

---

## 📐 4. System Architecture Diagram

```
+-----------------------------------------------------------------------------------------+
|                                    USER INTERFACES                                      |
|                                                                                         |
|   +------------------------------------+       +------------------------------------+   |
|   |         Desktop GUI (PC)           |       |        Mobile Companion (LAN)      |   |
|   | - CustomTkinter Modern UI          |       | - Offline Touch PWA (iOS/Android)  |   |
|   | - Keyboard F1-F12 POS Shortcuts    |       | - Native Android App (Gradle APK)  |   |
|   | - Thermal (80mm) & A4 PDF Invoices |       | - Camera Barcode / QR Scanner      |   |
|   | - Excel Financial Reports          |       | - Fast Aisle Shelf-Rack Locator    |   |
|   +-----------------+------------------+       +-----------------+------------------+   |
+---------------------|--------------------------------------------|----------------------+
                      |                                            |
                      v                                            v
+-----------------------------------------------------------------------------------------+
|                                   COMMUNICATION BUS                                     |
|                                                                                         |
|   Direct Python In-Process Calls                 Zero-Dependency LAN HTTP Daemon       |
|   (MainWindow -> Service Layer)                  (mobile_server.py on 0.0.0.0:8080)     |
+---------------------+--------------------------------------------+----------------------+
                      |                                            |
                      +--------------------+-----------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------------+
|                                  CORE SERVICE LAYER                                     |
|                                                                                         |
|   +----------------------+   +----------------------+   +---------------------------+   |
|   |   medicine_service   |   |    sales_service     |   |     purchase_service      |   |
|   | - FEFO Batch Queries |   | - POS Atomicity      |   | - Duplicate Invoice Guard |   |
|   | - Derived Strip Math |   | - Credit Validation  |   | - Expiry Intake Filter    |   |
|   | - Stock Adjustments  |   | - Stock Decrements   |   | - Strips-to-Tablets Math  |   |
|   +----------------------+   +----------------------+   +---------------------------+   |
|   +----------------------+   +----------------------+   +---------------------------+   |
|   |       money.py       |   |    backup_service    |   |       audit_service       |   |
|   | - Decimal Precision  |   | - SQLite Online API  |   | - JSON State Deltas       |   |
|   | - Commercial Rounding|   | - Pre-Restore Audits |   | - Cursor Reuse            |   |
|   | - Tax/Discount Split |   | - Safety Snapshots   |   | - Immutable History       |   |
|   +----------------------+   +----------------------+   +---------------------------+   |
+------------------------------------------+----------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------------+
|                                SQLite PERSISTENCE ENGINE                                |
|                                                                                         |
|   - PRAGMA journal_mode = WAL (Write-Ahead Logging for concurrent read/write)           |
|   - PRAGMA foreign_keys = ON  (Strict relational integrity)                             |
|   - PRAGMA busy_timeout = 5000 (Non-blocking queue under high transaction volume)       |
|   - 15 Strategic Performance Indexes (Covering FEFO, searches, barcode, customer phone) |
|   - Auto-Migration Engine (Schema Version 2 Self-Healing)                               |
+-----------------------------------------------------------------------------------------+
```

---

## 🚀 5. Getting Started & Installation Guide

MediTrack is packaged for multiple operating systems and deployment preferences.

---

### Method A: Standalone Windows App (No Python Required)
Use this option if you want to deploy MediTrack to a Windows PC or laptop without installing Python or dependencies.

1. Locate the standalone distribution archive:
   ```text
   dist/MediTrack-v2.0-Windows-Portable.zip
   ```
2. Extract the ZIP archive to any directory (e.g. `C:\MediTrack` or a USB flash drive).
3. Double-click **`MediTrack.exe`** (or `Launch MediTrack.bat`).
4. *(Optional)* Run **`create_desktop_shortcut.bat`** to create an official Windows Desktop shortcut with the custom MediTrack icon.

---

### Method B: Running from Source (Windows, Linux, macOS)

#### 1. Prerequisites
- **Python 3.10+** installed ([python.org](https://www.python.org/downloads/)).
- Ensure Python and pip are registered on your system PATH.

#### 2. Clone Repository
```bash
git clone https://github.com/<your-username>/meditrack-erp.git
cd meditrack-erp
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Launch Desktop Application
- **Windows (1-Click)**: Double-click [`run.bat`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/run.bat).
- **Linux / macOS (1-Click)**: Run `./run.sh` in terminal.
- **Direct Command Line**:
  ```bash
  python main.py
  ```

---

### First-Time Database Seeding
To populate realistic pharmacy data (including Dolo 650, Pan-D, Augmentin 625, Azithral 500, Telma 40, real distributors, batch numbers, and rack locations):
```bash
python seed_data.py
```

---

### User Profiles & Access Roles

MediTrack provides role-based security out of the box with cryptographic password hashing (zero plaintext password storage):

| Profile Role | Default Username | Initial Access Policy | Permissions Scope |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | Set during initialization / Change in Settings | Full access to all 12 modules, financial audits, settings, and database recovery |
| **Pharmacist** | `pharmacist` | Configured by Administrator | POS billing, stock inventory, purchases, supplier intake, returns, and expiry tracker |
| **Cashier** | `cashier` | Configured by Administrator | Fast POS counter billing, customer search, sales history, and stock lookup |

> 🔒 **Security Notice**: All user passwords in MediTrack are cryptographically salted and hashed via SHA-256 (`utils/security.py`). Default initial accounts should be updated immediately upon first login by navigating to **⚙️ System Settings > Change Login Password**.

---

## 🖥️ 6. Desktop Application Modules (Detailed Walkthrough)

The desktop application provides 12 specialized modules accessible via the left sidebar.

```
┌──────────────────────────────────────────────────────────────┐
│  🏥 MediTrack ERP                          🟢 LAN Active   👤 Admin │
├───────────────┬──────────────────────────────────────────────┤
│  🏠 Dashboard │                                              │
│  🧾 Billing   │                                              │
│  📦 Purchases │                   ACTIVE                     │
│  💊 Stock     │                   MODULE                     │
│  ⚠️ Expiry    │                    VIEW                      │
│  🚚 Suppliers │                  CONTAINER                   │
│  👥 Customers │                                              │
│  📜 History   │                                              │
│  🔄 Returns   │                                              │
│  📊 Reports   │                                              │
│  💼 Accounts  │                                              │
│  ⚙️ Settings  │                                              │
│───────────────┤                                              │
│  🚪 Sign Out  │                                              │
└───────────────┴──────────────────────────────────────────────┘
```

---

### 1. Executive Dashboard
- **Real-Time KPI Cards**:
  - **Today's Sales**: Gross revenue for the current business day.
  - **Today's Net Profit**: Calculated dynamically as $\sum (\text{Selling Price} - \text{Purchase Cost})$.
  - **Bills Generated**: Counter ticket count for today.
  - **Low Stock Watchlist**: Medicines whose total tablets are below minimum threshold.
- **Expiring Soon Watchlist**: Displays batches nearing expiration within the next 90 days.
- **Quick Shortcuts**: 1-click jump to New Bill, Add Stock, or Supplier Intake.

---

### 2. Billing & Point of Sale (POS)
- **Fast Search Bar**: Search by medicine brand name, generic composition, or barcode.
- **Batch Drawer (FEFO Order)**: When a medicine is selected, shows all available batches sorted by **First-Expiry-First-Out (FEFO)** so cashiers dispense older stock first.
- **Unit Flexibility**: Choose between selling **Full Strips** or **Loose Tablets**. Automatically computes price per tablet.
- **Customer Association**: Lookup registered patients by mobile number or enter quick walk-in cash patient details.
- **Real-Time Calculation**: Subtotal, line-item discounts, GST tax breakup, and grand total.
- **Payment Modes**: Supports **Cash**, **UPI / QR Code**, **Card**, and **Patient Credit (Pay Later)**.
- **Invoice Generation**: Instantly prints:
  - **Thermal 80mm Slip**: Compact slip for POS thermal receipt printers.
  - **A4 Formatted PDF**: Full tax invoice with pharmacy GSTIN, drug license numbers, batch details, and dynamic UPI QR code for scan-and-pay.
- **Keyboard Shortcuts**:
  - `F1`: Focus medicine search
  - `F2`: Add customer
  - `F5`: Switch to Cash payment
  - `F6`: Switch to UPI payment
  - `F9`: Complete & Print Bill
  - `Esc`: Clear cart

---

### 3. Purchases & Distributor Intake
- **Distributor Invoice Entry**: Record incoming stock from pharmaceutical distributors (e.g. Sun Pharma Dist, Cipla C&F).
- **Invoice Number Duplication Guard**: Validates that $(\text{supplier\_id}, \text{invoice\_number})$ is unique.
- **Strip-to-Tablet Conversion**: Staff enters number of strips and pack size; the system automatically calculates and updates authoritative `total_tablets`.
- **Purchase Price Rules**: Ensures $\text{Purchase Rate} \le \text{Selling Price} \le \text{MRP}$.
- **Accounts Payable Ledger Integration**: Automatically updates supplier balance and logs the invoice to double-entry supplier credit records.

---

### 4. Stock Inventory Management
- **Centralized Master Catalog**: Search across brand name, generic name, manufacturer, and barcode.
- **Live Inventory Breakdown**: Displays total available tablets alongside human-readable full strips and loose tablet breakdown.
- **Shelf Rack Locator**: Displays exact physical aisle location (e.g., `Rack B - Shelf 2 (Antibiotics)`).
- **Stock Status Badges**:
  - `HEALTHY` (Green): Sufficient stock with safe shelf life.
  - `LOW_STOCK` (Amber): Stock below minimum threshold.
  - `EXPIRING_SOON` (Orange): Within 90-day expiry window.
  - `EXPIRED` (Red): Shelf-life expired.
  - `OUT_OF_STOCK` (Gray): Zero available units.
- **Audited Stock Adjustment Modal**: Correct stock for physical breakage, damage, or discrepancy with required audit notes.

---

### 5. FEFO Expiry Tracker
- **Predictive Expiry Horizons**: Filter inventory by batches expiring in:
  - Next 30 Days (Critical)
  - Next 60 Days (Actionable)
  - Next 90 Days (Watchlist)
  - Next 180 Days (Long-range)
  - Already Expired
- **Distributor Return Dispatch**: 1-click generation of supplier return debits to return near-expiry medicines to distributors for credit notes.

---

### 6. Suppliers & Accounts Payable
- **Distributor Directory**: Manage distributor names, contact persons, phone numbers, GSTIN, and addresses.
- **Balance Tracking**: Tracks outstanding accounts payable for credit purchases.
- **Payment Recording**: Record payments made to distributors with transaction reference numbers (Cheque, NEFT, UPI, Cash) and print payment vouchers.

---

### 7. Customers & Accounts Receivable
- **Patient Profiles**: Phone number, patient name, doctor reference, and address.
- **Credit Limit Control**: Assign maximum allowed unpaid credit. POS alerts or blocks billing if credit balance exceeds limit.
- **Ledger Statement**: View transaction-by-transaction history of bills, credit amounts, and repayments.
- **Outstanding Settlement**: Record partial or full balance clearance.

---

### 8. Sales History & Returns Manager
- **Complete Sales Audit**: Filter past invoices by invoice number, date range, or customer name.
- **Reprint Bills**: Re-generate original thermal receipt or A4 PDF invoices anytime.
- **Sales Return Processing**:
  - Support full or partial returns.
  - Restores authoritative tablet count back into the exact original batch.
  - Re-adjusts customer credit balance or issues cash refunds.
  - Re-computes profit metrics.

---

### 9. Financial Reports & Analytics
- **Date-Range Filtering**: Analyze performance by Today, This Week, This Month, or Custom Date Horizons.
- **Key Metrics**:
  - Total Gross Sales Revenue
  - Total Cost of Goods Sold (COGS)
  - Total Net Profit & Profit Margin %
  - Total GST Collected (CGST / SGST split)
- **Top Performers**:
  - Most Sold Medicines (by volume)
  - Most Profitable Medicines (by gross margin)
- **Exports**:
  - **Excel Spreadsheet (`.xlsx`)**: Formatted multi-tab workbook with gridlines, headers, and formulas via `openpyxl`.
  - **Executive PDF Report (`.pdf`)**: Formal printed report via ReportLab.

---

### 10. Accounts & Day-Book Ledger
- **Daily Financial Close**: Consolidated day-book summarizing opening cash balance, cash sales, digital collections, distributor payments, and closing cash.
- **Payment Method Distribution**: Split between Cash, UPI, Card, and Credit.
- **Receivables vs Payables**: Snapshot of total outstanding patient debt versus supplier debt.

---

### 11. System Settings & Configuration
- **Pharmacy Profile**: Store name, address, phone number, GSTIN, Drug License (DL) Number 20B/21B.
- **Receipt Customization**: Upload shop logo, custom receipt header, and footer greetings.
- **UPI Configuration**: Enter pharmacy VPA/UPI ID (e.g. `pharmacy@upi`) to automatically render scan-to-pay QR codes on invoices.
- **Database Backup & Restore Center**:
  - Create instant SQLite Online Backup snapshots.
  - Audit backup integrity.
  - Restore previous snapshots with safety rollback guarantees.
- **Mobile Companion Pairing**: Displays local network IP and pairing QR code for phone connections.

---

## 📱 7. Mobile Companion Application Suite

MediTrack includes a dedicated mobile companion system allowing pharmacists to move through aisles with a phone or tablet.

---

### Offline Local Network Server
The desktop application automatically launches a lightweight LAN HTTP daemon on port `8080`:
- **Zero External Dependencies**: Built entirely with Python's standard library `http.server` and `socket`.
- **Offline LAN Operation**: Operates over the shop's local Wi-Fi router or laptop Mobile Hotspot. No internet connection is required.
- **Automatic IP Discovery**: Discovers and broadcasts the host computer's active IP (e.g. `192.168.1.15:8080`).

---

### Option 1: Zero-Build Mobile PWA
No compilation or app store download required.

1. Connect your smartphone and PC/laptop to the same Wi-Fi router or laptop **Mobile Hotspot**.
2. On MediTrack PC, go to **⚙️ System Settings** $\rightarrow$ **Mobile Companion Pairing**.
3. Scan the displayed QR code with your mobile camera, or open Chrome/Safari and navigate to:
   ```text
   http://<pc-local-ip>:8080
   ```
4. In your mobile browser, tap **"Add to Home Screen"** or **"Install MediTrack"**.
5. The app installs as a standalone, full-screen mobile app with service worker caching.

---

### Option 2: Native Android Studio Application
For stores with dedicated Android barcode terminals or staff smartphones, a complete native Android Studio Gradle project is included in [`android_app/`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/android_app/):

- **Target SDK**: Android 14 (API 34), Min SDK Android 7.0 (API 24).
- **Cleartext HTTP Support**: [`network_security_config.xml`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/android_app/app/src/main/res/xml/network_security_config.xml) permits local intranet communication (`192.168.*.*`, `10.*.*.*`).
- **Hardware Camera Bridge**: [`MainActivity.java`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/android_app/app/src/main/java/com/meditrack/erp/MainActivity.java) implements a WebChromeClient permission bridge for barcode and QR scanning.
- **Branding**: Includes complete mipmap launcher icon sets in all pixel densities (MDPI to XXXHDPI).
- **Building the APK**:
  1. Open Android Studio.
  2. Select **Open** and choose the `android_app/` directory.
  3. Let Gradle sync dependencies.
  4. Click **Build > Build Bundle(s) / APK(s) > Build APK(s)**.
  5. Install `app-debug.apk` directly on Android devices.

---

### Mobile Capabilities & Workflow
- 🔍 **Aisle Stock Checker**: Search 5,000+ medicines to check live stock in strips and loose tablets.
- 📍 **Shelf & Rack Locator**: Shows exact aisle shelf locations (e.g. `Rack A - Shelf 3`).
- 📷 **Aisle Barcode Scanner**: Scan barcodes on medicine packages with the device camera to check batch expiry and pricing.
- 🧾 **Rapid Counter Sales**: Add medicines to mobile cart and submit directly to desktop cash register.
- 📈 **Mobile KPIs**: Real-time sales totals, profit numbers, and critical low-stock alerts.

---

## 🗄️ 8. Database Engine & Migration Architecture

---

### WAL Mode & Concurrency Pragmas
MediTrack executes SQLite in Write-Ahead Logging (WAL) mode:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
PRAGMA temp_store = MEMORY;
```

**Benefits**:
- **Non-blocking concurrency**: Readers never block writers, and writers never block readers. Desktop POS checkouts and mobile barcode searches execute simultaneously without `database is locked` errors.
- **Crash durability**: In the event of a sudden power loss, uncommitted transactions are cleanly rolled back from the WAL file upon restart without file corruption.

---

### Schema Version 2 Tables & Relationships

```
┌─────────────────┐       ┌──────────────────────┐       ┌────────────────────┐
│   suppliers     │       │      medicines       │       │     customers      │
│─────────────────│       │──────────────────────│       │────────────────────│
│ id (PK)         │◄──┐   │ id (PK)              │◄──┐   │ id (PK)            │◄──┐
│ name            │   │   │ name                 │   │   │ name               │   │
│ phone           │   │   │ generic_name         │   │   │ phone              │   │
│ gstin           │   │   │ rack_shelf           │   │   │ credit_limit       │   │
│ balance         │   │   │ min_stock_alert      │   │   │ current_balance    │   │
└─────────────────┘   │   └──────────────────────┘   │   └────────────────────┘   │
                      │               ▲              │               ▲            │
                      │               │              │               │            │
┌─────────────────┐   │   ┌───────────┴──────────┐   │   ┌───────────┴────────┐   │
│    purchases    │   │   │   medicine_batches   │   │   │       bills        │   │
│─────────────────│   │   │──────────────────────│   │   │────────────────────│   │
│ id (PK)         │   │   │ id (PK)              │   │   │ bill_number (PK)   │   │
│ supplier_id (FK)├───┘   │ medicine_id (FK)     ├───┘   │ customer_id (FK)   ├───┘
│ invoice_number  │       │ batch_number         │       │ total_amount       │
│ total_amount    │       │ total_tablets        │       │ profit             │
│ payment_status  │       │ tablets_per_strip    │       │ payment_mode       │
└─────────────────┘       │ purchase_price       │       │ payment_status     │
        ▲                 │ selling_price        │       └────────────────────┘
        │                 │ mrp                  │                 ▲
┌───────┴─────────┐       │ expiry_date          │                 │
│ purchase_items  │       └──────────────────────┘       ┌─────────┴──────────┐
│─────────────────│                   ▲                  │     bill_items     │
│ purchase_id (FK)│                   │                  │────────────────────│
│ medicine_id     │                   └──────────────────┤ batch_id (FK)      │
│ batch_number    │                                      │ quantity (tablets) │
│ total_tablets   │                                      │ price              │
└─────────────────┘                                      └────────────────────┘
```

#### Core Database Tables (15 Tables):
1. `medicines`: Master product records (brand, generic, manufacturer, rack shelf).
2. `medicine_batches`: Specific physical batches with authoritative `total_tablets`, FEFO expiry dates, and pricing.
3. `suppliers`: Distributor profiles and accounts payable.
4. `purchases`: Header records for distributor shipments with duplicate invoice protection.
5. `purchase_items`: Individual batch items received in distributor purchases.
6. `purchase_returns`: Items returned to distributors with debit notes.
7. `customers`: Patient profiles, accounts receivable, and credit limits.
8. `bills`: Header sales records with payment modes, totals, and profits.
9. `bill_items`: Line-item sales records with unit prices and batch traceability.
10. `sales_returns`: Customer return records with stock reversal tracking.
11. `users`: Administrative, pharmacist, and cashier credentials with role-based permissions.
12. `settings`: Key-value application configuration (store name, DL numbers, UPI ID).
13. `audit_logs`: Immutable audit trail with serialized JSON before/after state deltas.
14. `stock_adjustments`: Historical physical inventory discrepancy corrections.
15. `supplier_ledger`: Double-entry accounting ledger tracking distributor debits and credits.

---

### Idempotent Migration Engine
Implemented in [`database/migrations.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/database/migrations.py):
- Automatically inspects the current SQLite database version (`PRAGMA user_version`).
- Applies schema changes sequentially inside atomic transactions.
- **Self-Healing Features**:
  - Automatically migrates legacy `bills.bill_number` from `INTEGER PRIMARY KEY` to `TEXT PRIMARY KEY` to support formatted strings like `MT-2026-000001`.
  - Safely decouples legacy foreign key artifacts without data loss.

---

## 📦 9. Packaging, Distribution & Git Repository Setup

---

### Building Windows Executable (`build_desktop.py`)
To build the standalone Windows `.exe` application:
```bash
python build_desktop.py
```

**Build Pipeline**:
1. Checks and installs PyInstaller automatically if absent.
2. Generates multi-resolution icon assets (`assets/icon.ico`).
3. Embeds CustomTkinter styling themes and the mobile PWA web assets.
4. Packages a standalone executable: `dist/MediTrack/MediTrack.exe`.
5. Compresses the output into: `dist/MediTrack-v2.0-Windows-Portable.zip`.

---

### Portable USB Distribution ZIP
The generated ZIP file is located at:
```text
dist/MediTrack-v2.0-Windows-Portable.zip
```
- **Size**: Approximately 44 MB.
- **Features**: Includes `MediTrack.exe`, runtime libraries, mobile server assets, and a pre-seeded `medical_shop.db`.
- **Usage**: Copy the ZIP to any USB drive. Extract and run on any Windows 10/11 computer without installing Python or dependencies.

---

### Windows Desktop Shortcut Generator
To place a shortcut on your Windows Desktop:
- Double-click [`create_desktop_shortcut.bat`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/create_desktop_shortcut.bat).
- It executes [`create_desktop_shortcut.ps1`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/create_desktop_shortcut.ps1), automatically linking the shortcut to `MediTrack.exe` (or `run.bat`) and assigning `assets/icon.ico`.

---

### Git Repository Sharing & Remote Setup
The codebase is structured as a clean Git repository on the `main` branch.

#### Push to Your Remote (GitHub, GitLab, Gitea):
```bash
# Add your remote repository URL
git remote add origin https://github.com/<your-username>/meditrack-erp.git

# Push all source code, assets, and documentation
git push -u origin main
```

#### Clone on Another PC or Laptop:
```bash
git clone https://github.com/<your-username>/meditrack-erp.git
cd meditrack-erp
pip install -r requirements.txt
python seed_data.py
python main.py
```

---

## 🧪 10. Automated Quality Assurance & Test Suites

MediTrack includes automated test suites covering financial calculations, database concurrency, disaster recovery, and mobile communication. All tests execute in isolated sandboxes and exit with code `0`.

```bash
# 1. Purchase & Procurement Engine Test
python tests/test_purchase_service.py

# 2. Disaster Recovery & Online Backup Test
python tests/test_backup_service.py

# 3. Immutable Audit Trail Service Test
python tests/test_audit_service.py

# 4. Mobile Companion LAN Server Test
python tests/test_mobile_server.py

# 5. Full End-to-End System Regression Test
python verify_system.py
```

---

## ❓ 11. Troubleshooting & Frequently Asked Questions (FAQ)

### Q1: Chrome says "This site can't be reached" (DNS_PROBE_FINISHED_NXDOMAIN)
* **Cause**: You typed `v2.0-windows-portable.zip` directly into your browser URL bar. Chrome treats `.zip` as a web domain rather than a local file.
* **Solution**: `MediTrack-v2.0-Windows-Portable.zip` is a **local offline file** located at:
  ```text
  C:\Users\Mruthyunjaya\.gemini\antigravity\scratch\medical_shop\dist\
  ```
  If you want to download it in your browser, include the local server address:
  ```text
  http://localhost:8080/download
  ```

---

### Q2: Mobile phone cannot connect to the desktop application
* **Checklist**:
  1. Confirm your PC and phone are connected to the **same Wi-Fi router** or your laptop's **Mobile Hotspot**.
  2. Verify the IP address shown in **Settings > Mobile Companion Pairing** (e.g. `http://192.168.1.15:8080`).
  3. Ensure Windows Firewall allows incoming connections on port `8080`.

---

### Q3: How do I backup my store data before updating?
1. Open MediTrack desktop.
2. Go to **⚙️ System Settings** $\rightarrow$ **Database Backup & Recovery**.
3. Click **💾 Create Backup Now**.
4. A verified backup snapshot will be saved in the `backups/` folder.

---

### Q4: Can I run MediTrack on multiple desktop computers at the same time?
* Yes. Because MediTrack uses SQLite WAL mode, you can place the active `medical_shop.db` on a shared local network drive (NAS) and set the `MEDITRACK_DB_PATH` environment variable on each computer pointing to that shared path.

---

## 📄 License & Intellectual Property

MediTrack ERP is open-source software engineered for medical shops, retail pharmacies, and healthcare clinics.

Developed for dependability, precision, and complete offline independence.
