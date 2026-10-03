# 📋 Changelog — MediTrack ERP

All notable changes to the **MediTrack ERP** application are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-10-03 — Production-Quality Multi-Platform Suite

### 🚀 Added
- **Centralized Decimal Financial Engine**: Created [`utils/money.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/utils/money.py) implementing pure `Decimal` currency arithmetic, commercial `ROUND_HALF_UP` rounding, and precise CGST/SGST tax split.
- **Authoritative Stock Single Source of Truth**: Enforced integer `total_tablets` in `medicine_batches`; full strips and loose tablets dynamically derived.
- **Duplicate Purchase Invoice Guard**: Added compound uniqueness check on `(supplier_id, purchase_invoice_number)` in [`utils/purchase_service.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/utils/purchase_service.py).
- **Strict Expiry Safety Filter**: Hard block preventing procurement intake of expired medicines; audited administrative override with before/after state logging for POS emergency dispensing.
- **Pricing Bounds Validation**: Enforces $\text{Purchase Rate} \le \text{Selling Price} \le \text{MRP}$ on all procurement entries.
- **SQLite Online Backup API Engine**: Upgraded [`utils/backup_service.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/utils/backup_service.py) using `sqlite3.Connection.backup()`, pre-restore verification (`verify_backup_integrity()`), and automatic emergency rollback snapshots (`pre_restore_safety_*.db`).
- **Immutable JSON Audit Trails**: Upgraded [`utils/audit_service.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/utils/audit_service.py) with before/after state snapshots serialized to JSON and in-transaction cursor reuse.
- **Mobile Companion LAN Server**: Created [`mobile_server.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/mobile_server.py) with zero external dependencies, serving REST APIs, instant pairing QR codes, and direct ZIP downloads.
- **Touch-Optimized Offline PWA**: Built [`mobile/index.html`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/mobile/index.html) and Service Worker v2 ([`mobile/sw.js`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/mobile/sw.js)) featuring aisle stock search, shelf-rack locator, and camera barcode scanner.
- **Native Android Studio Project**: Created complete Android Gradle project in [`android_app/`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/android_app/) with target SDK 34, hardware camera permissions, cleartext HTTP config, and complete launcher mipmap sets.
- **Standalone Windows Desktop Packaging**: Built [`build_desktop.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/build_desktop.py) generating standalone `MediTrack.exe` and portable 44 MB ZIP archive (`MediTrack-v2.0-Windows-Portable.zip`).
- **1-Click Launchers & Shortcuts**: Added [`run.bat`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/run.bat), [`run.sh`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/run.sh), [`create_desktop_shortcut.bat`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/create_desktop_shortcut.bat), and [`create_desktop_shortcut.ps1`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/create_desktop_shortcut.ps1).
- **Realistic Indian Pharmacy Seeder**: Built [`seed_data.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/seed_data.py) with popular real-world medications, suppliers, and stock batches.

### 🔄 Changed
- **Database Engine**: Migrated SQLite to WAL journal mode with `busy_timeout = 5000` and 15 strategic performance indexes in [`database/db.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/database/db.py).
- **Bill Primary Key**: Upgraded `bills.bill_number` from `INTEGER` to `TEXT PRIMARY KEY` to support formatted invoice codes (e.g. `MT-2026-000001`).
- **Visual Branding**: Realigned all 18 CustomTkinter UI modules to the **Deep Emerald** (`#166534`), **Soft Sage** (`#DCFCE7`), and **Warm Off-White** (`#F7F8F6`) design palette.
- **Persistent Output Paths**: PDF invoices and Excel reports now save permanently to directories adjacent to the database via [`utils/pdf_service.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/utils/pdf_service.py) rather than temporary frozen folders.
- **Clean Shutdown Hook**: Added `WM_DELETE_WINDOW` protocol handler in [`ui/main_window.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/ui/main_window.py) to gracefully terminate mobile background servers.

### 🛡️ Fixed
- Fixed binary floating-point representation drift across invoice subtotals, tax splits, and profit calculations.
- Fixed non-atomic concurrency race conditions during high-speed counter checkouts with double-check queries (`WHERE id = ? AND total_tablets >= ?`).
- Fixed missing window icons on Windows taskbar by generating multi-resolution `assets/icon.ico`.
- Fixed silent startup exits in windowed `.exe` mode by adding graphical error dialog fallback in [`main.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/main.py).

---

## [1.5.0] - 2026-08-09 — Relational Architecture & Role Security

### 🚀 Added
- Separated master catalog (`medicines`) from batch inventory (`medicine_batches`).
- Added role-based access control (Admin, Pharmacist, Cashier) with route guards in `MainWindow`.
- Implemented First-Expiry-First-Out (FEFO) batch queries for POS dispensing.
- Added Thermal 80mm receipt generation and A4 PDF tax invoices with dynamic UPI QR codes.
- Added customer accounts receivable and supplier accounts payable ledgers.

### 🔄 Changed
- Migrated legacy database schemas via `database/migrations.py`.
- Modernized Tkinter views with CustomTkinter light theme.

---

## [1.0.0] - 2026-06-22 — Initial Prototype

### 🚀 Added
- Initial desktop application prototype with single-table medicine storage.
- Basic CRUD operations for medicines, suppliers, and billing.
- Standard file-copy backup script.
