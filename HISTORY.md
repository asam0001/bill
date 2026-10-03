# 📜 MediTrack ERP — Complete Development History & Architectural Evolution

This document records the complete chronological development history, engineering decisions, architectural audits, and evolutionary milestones of the **MediTrack ERP** system.

---

## 📅 Project Timeline Overview

```
+---------------------------------------------------------------------------------------------------+
|  PHASE 0: Legacy Prototype (v1.0.0)                                                               |
|  - Monolithic single-table medicine storage                                                       |
|  - Floating-point strip math & unhandled fractional units                                         |
|  - Basic UI, no role authorization, lack of formal audit logs                                     |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|  ARCHITECTURAL AUDIT & FORMAL SPECIFICATION                                                       |
|  - 10 Enterprise Pharmacy Directives formulated                                                   |
|  - Deep Emerald visual design system locked                                                       |
|  - Mandate of 100% offline independence & mathematical correctness                                |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|  PHASES 1-4: Core Foundation & Hardening                                                          |
|  - SQLite WAL mode, Schema v2, 15 indexes, and self-healing migrations                            |
|  - Authoritative total_tablets single source of truth                                             |
|  - Centralized Python Decimal money engine with ROUND_HALF_UP commercial rounding                 |
|  - Double-check concurrency protection and atomic POS billing transactions                        |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|  PHASES 5-7: Procurement, Disaster Recovery & Compliance Auditing                                 |
|  - Duplicate purchase invoice detection (supplier_id + invoice_number)                            |
|  - Hard rejection of expired procurement & audited supervisor overrides for POS                   |
|  - SQLite native Online Backup API, integrity audits, and pre-restore safety snapshots            |
|  - Immutable audit trail with serialized JSON before/after state deltas                           |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|  PHASES 8-9: Multi-Platform Expansion & Packaging (v2.0.0)                                        |
|  - Complete 12-module CustomTkinter UI with Deep Emerald branding                                 |
|  - Zero-dependency LAN HTTP daemon serving offline mobile companion PWA                           |
|  - Full native Android Studio companion application project (SDK 34) in android_app/              |
|  - Standalone PyInstaller Windows .exe builder and portable 44 MB distribution ZIP                |
|  - Git repository initialization and push to GitHub (github.com/asam0001/bill)                     |
+---------------------------------------------------------------------------------------------------+
```

---

## 🏛️ Phase 0: Legacy System Analysis & Shortcomings

The initial prototype of the pharmacy application was designed as a proof-of-concept CRUD desktop app. While functional for basic data entry, an in-depth architectural audit revealed severe risks that prevented deployment in high-volume, real-world pharmacies:

| Component | Legacy Implementation | Real-World Failure Mode |
| :--- | :--- | :--- |
| **Inventory Unit** | Stored inventory as floating-point strips (e.g., `9.66 strips`). | Cumulative rounding errors; impossible to reconcile physical loose tablets with database counts. |
| **Data Normalization** | Single table coupling medicine master information with batch details. | Could not support multiple active batches, varying expiry dates, or multi-distributor purchase histories. |
| **Financial Math** | Used standard Python binary `float` arithmetic. | IEEE-754 representation artifacts (e.g. `0.1 + 0.2 != 0.3`) caused discrepancies in tax and grand totals. |
| **Concurrency & POS** | Non-atomic `UPDATE stock = stock - x` without double-checking available quantity. | High-speed billing or concurrent counter checkouts could produce negative inventory counts. |
| **Expiry Control** | Expiry dates were informative strings without enforcement. | Staff could accidentally purchase or dispense expired drugs, causing severe regulatory and health violations. |
| **Purchase Entry** | No invoice duplication check. | Re-entering or double-scanning distributor bills artificially inflated stock and accounts payable. |
| **Backups** | Standard file copying (`shutil.copyfile`). | Corrupted database copies when executed against active SQLite write transactions. |
| **Audit Trail** | Fragmented string print logs. | No verifiable accountability for supervisor price overrides, manual inventory changes, or database restores. |
| **Platform Scope** | Desktop-only on single PC. | Staff had to walk back and forth from store aisles to cash register to verify shelf locations and batch prices. |

---

## 📐 The 10 Enterprise Pharmacy Directives

To elevate MediTrack into an enterprise-grade ERP, a comprehensive architectural overhaul was established around 10 non-negotiable rules:

1. **Establish a Single Source of Truth for Stock**: Authoritative quantity is strictly integer `total_tablets`. Full strips and loose tablets are always dynamically computed.
2. **Separate Medicine Master from Batch Inventory**: Master catalog (`medicines`) holds brand, generic, and shelf location; relational `medicine_batches` tracks batch numbers, expiry dates, supplier links, and stock.
3. **Centralized Money and Profit Calculation**: All currency arithmetic must use `Decimal` with `ROUND_HALF_UP` commercial rounding in a dedicated `utils/money.py` service.
4. **Real Transaction Safety in Billing**: Strict atomic transactions with double-check concurrency (`WHERE id = ? AND quantity >= ?`), automatic rollback on failure, and credit limit validation.
5. **Strict Expiry Enforcement**: Immediate rejection of expired distributor intake; hard block at POS with an immutable supervisor override audit trail.
6. **Duplicate Purchase Protection**: Compound uniqueness on `(supplier_id, purchase_invoice_number)` and validation that $\text{Purchase Rate} \le \text{Selling Price} \le \text{MRP}$.
7. **Real Database Backup System**: Migration to SQLite native Online Backup API (`sqlite3.Connection.backup()`), pre-restore integrity validation, and automatic safety rollback snapshots.
8. **Audit Log Normalization**: Unified `audit_logs` storing user ID, action type, and before/after state snapshots serialized as JSON.
9. **Clean Import & Staging Pipeline**: Distributor invoice imports staged in temporary tables with column mapping and validation before batch creation.
10. **UI Realignment with Business Logic**: CustomTkinter redesign adhering strictly to the **Deep Emerald** (`#166534`), **Soft Sage** (`#DCFCE7`), and **Warm Off-White** (`#F7F8F6`) visual palette.

---

## 🛠️ Detailed Implementation History (Phases 1 through 9)

---

### Phase 1: Database Foundation & Schema v2 Migration
* **Upgraded Database Engine** ([`database/db.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/database/db.py)):
  - Enforced `PRAGMA journal_mode = WAL` (Write-Ahead Logging) for non-blocking concurrent reads and writes.
  - Set `PRAGMA busy_timeout = 5000` to prevent database locks during multi-device access.
  - Implemented atomic `transaction()` context manager guaranteeing clean `COMMIT` or `ROLLBACK`.
  - Added 15 strategic performance indexes across barcode, FEFO expiry dates, and customer phone lookups.
  - Created staging tables `stock_adjustments` and `imported_invoices`.
* **Migration Runner** ([`database/migrations.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/database/migrations.py)):
  - Built an idempotent schema migration engine upgrading databases to Version 2.
  - Self-healing routine automatically decoupled legacy `old_medicines` foreign key artifacts.
  - Safely migrated `bills.bill_number` from `INTEGER PRIMARY KEY` to `TEXT PRIMARY KEY` to support standard formatted invoice strings (e.g. `MT-2026-000001`).

---

### Phase 2: Authoritative Inventory & FEFO Engine
* **Refactored Stock Service** ([`utils/medicine_service.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/utils/medicine_service.py)):
  - Enforced `total_tablets` as single source of truth.
  - Dynamic strip math: $\text{full\_strips} = \lfloor \text{total\_tablets} / \text{tablets\_per\_strip} \rfloor$, $\text{loose} = \text{total\_tablets} \pmod{\text{tablets\_per\_strip}}$.
  - Implemented **First-Expiry-First-Out (FEFO)** batch queries ensuring oldest non-expired batches are dispensed first.
  - Created automated stock classification status pills: `HEALTHY`, `LOW_STOCK`, `EXPIRING_SOON`, `EXPIRED`, `OUT_OF_STOCK`.
  - Implemented formal `adjust_stock()` audit engine for physical discrepancy reconciliations.
  - Implemented `authorize_expired_sale_override()` with cursor reuse for emergency dispensing.

---

### Phase 3: Centralized Money & Financial Engine
* **Created Centralized Money Service** ([`utils/money.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/utils/money.py)):
  - Replaced all binary float arithmetic with Python's `Decimal` type.
  - Implemented commercial rounding (`ROUND_HALF_UP`) to 2 decimal places.
  - Built financial calculation suite: `to_decimal()`, `quantize_money()`, `calculate_tablet_price()`, `calculate_discount()`, `calculate_tax()` (with split CGST/SGST), and `calculate_line_item()`.
  - Completely eradicated floating-point binary representation errors.

---

### Phase 4: Sales & POS Billing Engine
* **Upgraded Billing Engine** ([`utils/sales_service.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/utils/sales_service.py)):
  - Added double-check concurrency reduction:
    ```sql
    UPDATE medicine_batches 
    SET total_tablets = total_tablets - ? 
    WHERE id = ? AND total_tablets >= ?
    ```
  - Added patient credit limit verification: automatically warns or halts checkout if customer balance exceeds allowable threshold.
  - Implemented over-return protection preventing refunds exceeding original sold quantities.
  - Seamless support for Cash, UPI, Card, and Credit settlements.

---

### Phase 5: Purchase & Procurement Engine
* **Upgraded Procurement Service** ([`utils/purchase_service.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/utils/purchase_service.py)):
  - Integrated `utils/money.py` for Decimal invoice totals, line item taxes, and distributor discounts.
  - Added **Duplicate Purchase Protection**: Checks `(supplier_id, purchase_invoice_number)` before write.
  - Added **Procurement Expiry Safety**: Blocks entry of distributor medicines whose expiry date has already passed.
  - Added **Pricing Bounds Validation**: Enforces $\text{Purchase Rate} \le \text{Selling Price} \le \text{MRP}$.
  - Added double-entry `supplier_ledger` logging and purchase return debit notes.
  - Created dedicated automated test suite in [`tests/test_purchase_service.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/tests/test_purchase_service.py) (100% Pass).

---

### Phase 6: Disaster Recovery & Backup Engine
* **Upgraded Backup Engine** ([`utils/backup_service.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/utils/backup_service.py)):
  - Integrated SQLite's native **Online Backup API** (`sqlite3.Connection.backup()`) streaming live pages without database locks.
  - Implemented `verify_backup_integrity()` performing physical file verification, PRAGMA integrity check, and schema audit.
  - Added automatic **Emergency Pre-Restore Safety Snapshots** (`pre_restore_safety_*.db`) guarding against accidental bad restores.
  - Created automated test suite in [`tests/test_backup_service.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/tests/test_backup_service.py) (100% Pass).

---

### Phase 7: Immutable Audit Trail Engine
* **Upgraded Audit Service** ([`utils/audit_service.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/utils/audit_service.py)):
  - Harmonized schema v2 dual-column `date`/`timestamp` logging.
  - Implemented structured JSON serialization and deserialization for pre-mutation and post-mutation state deltas.
  - Enabled in-transaction cursor reuse preventing database locking during nested service operations.
  - Created automated test suite in [`tests/test_audit_service.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/tests/test_audit_service.py) (100% Pass).

---

### Phase 8: UI Modernization & Role Security
* **UI Redesign** ([`ui/`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/ui/)):
  - Standardized all 18 UI modules to CustomTkinter with the Deep Emerald palette.
  - Implemented role-based route guards in [`ui/main_window.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/ui/main_window.py):
    - `Cashier`: POS billing, customer search, sales history.
    - `Pharmacist`: Stock management, purchases, supplier returns, expiry tracker.
    - `Admin`: Unrestricted access, financial reports, accounts ledger, system settings, database restores.
  - Built keyboard-driven POS checkout with hotkeys (`F1` to `F9`, `Esc`).
  - Added dual invoice printing: 80mm thermal receipt and A4 tax invoice with dynamic UPI QR code.

---

### Phase 9: Multi-Platform Standalone Deployment, Mobile APK Suite, and Git Packaging
* **Branding & Assets** ([`assets/`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/assets/)):
  - Generated multi-resolution Windows desktop icon (`icon.ico`: 16px to 256px) and high-res vector emblem (`icon.png`).
* **Standalone Windows Executable**:
  - Engineered [`build_desktop.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/build_desktop.py) using PyInstaller to package `dist/MediTrack/MediTrack.exe` with bundled runtime dependencies, icons, and theme assets.
  - Created 44 MB portable distribution archive: `dist/MediTrack-v2.0-Windows-Portable.zip`.
  - Added 1-click desktop shortcut creators ([`create_desktop_shortcut.bat`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/create_desktop_shortcut.bat) and [`.ps1`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/create_desktop_shortcut.ps1)).
  - Enabled true zero-install USB portability: detects if application directory is writable and keeps `medical_shop.db` alongside the executable.
  - Added persistent path resolution in [`utils/pdf_service.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/utils/pdf_service.py) so generated invoices and reports are saved permanently rather than in temporary extraction directories.
  - Added clean shutdown hook (`WM_DELETE_WINDOW`) to eliminate background zombie processes.
* **Mobile Companion Suite**:
  - Developed zero-dependency LAN HTTP server ([`mobile_server.py`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/mobile_server.py)) on port `8080` with auto IP discovery and QR pairing.
  - Developed offline PWA ([`mobile/index.html`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/mobile/index.html), [`manifest.json`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/mobile/manifest.json), [`sw.js`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/mobile/sw.js)) with camera barcode scanning, shelf-rack locator, and direct ZIP download support.
  - Created full native Android Studio Gradle project in [`android_app/`](file:///C:/Users/Mruthyunjaya/.gemini/antigravity/scratch/medical_shop/android_app/) with target SDK 34, hardware camera permissions, cleartext LAN configuration, and launcher mipmaps.
* **Git Version Control & Remote Publishing**:
  - Initialized Git repository on `main` branch with clean `.gitignore` excluding transactional databases and temporary build artifacts.
  - Connected remote origin to `https://github.com/asam0001/bill.git`.
  - Pushed all application code, services, Android project, test suites, and documentation.

---

## 📊 Evolutionary Comparison (Legacy vs. Production v2.0.0)

| Architectural Dimension | Legacy Prototype (v1.0.0) | Production MediTrack ERP (v2.0.0) |
| :--- | :--- | :--- |
| **Inventory Accounting** | Floats (`9.66 strips`) | Authoritative integer `total_tablets`; strips and loose pills dynamically derived. |
| **Currency Arithmetic** | Standard `float` (rounding errors) | Centralized Python `Decimal` with commercial `ROUND_HALF_UP`. |
| **Database Concurrency** | SQLite default (locking on writes) | SQLite `WAL` mode + `busy_timeout = 5000` + 15 performance indexes. |
| **Transaction Safety** | Unprotected single queries | Atomic transactions with automatic rollback on error. |
| **Point of Sale** | Mouse-only CRUD | Keyboard-driven (`F1`-`F9`) with FEFO batch selection drawers. |
| **Receipt Output** | Basic generic PDF | 80mm thermal slip + A4 tax invoice with dynamic UPI QR code. |
| **Expiry Control** | Display only | Hard blocks on expired intake; audited supervisor override at POS. |
| **Supplier Intake** | Unchecked entry | Duplicate invoice detection (`supplier_id + invoice_number`) and price boundary checks. |
| **Backup & Recovery** | Unsafe file copy | Native SQLite Online Backup API, integrity audits, and safety snapshots. |
| **Audit Trails** | Print statements | Immutable database logs with serialized before/after JSON state deltas. |
| **Mobile Access** | None | Offline local LAN PWA + Native Android Studio Gradle APK project. |
| **Deployment** | Source code with manual pip | Standalone Windows `.exe`, portable 44 MB ZIP, and 1-click launchers. |
| **Git Repository** | Untracked | Structured Git repository pushed to `github.com/asam0001/bill`. |

---

## 🏁 Conclusion

Through these 9 phases, MediTrack ERP has evolved from a basic prototype into a complete, hardened pharmacy management ecosystem. It combines mathematical precision, regulatory compliance, fault tolerance, and multi-device usability without sacrificing its core offline-first independence.
