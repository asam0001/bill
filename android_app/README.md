# MediTrack Mobile — Native Android Companion Application

This directory contains the production-ready Android companion project for **MediTrack ERP**.

---

## Architecture Overview

MediTrack provides two convenient mobile integration pathways:

### Option 1: Instant Zero-Build PWA (Recommended for Speed & Simplicity)
1. Ensure your PC/Laptop running MediTrack and your mobile device (Android or iPhone/iPad) are on the **same Wi-Fi network** or **Mobile Hotspot**.
2. On your MediTrack desktop ERP, navigate to **System Settings** -> **Mobile Companion Pairing**.
3. Scan the displayed QR code with your mobile camera, or type the URL (e.g. `http://192.168.1.15:8080`) into Chrome or Safari.
4. Tap **"Install MediTrack"** or **"Add to Home Screen"**.
5. The application will install as a standalone app with offline caching and camera barcode scanning.

---

### Option 2: Native Android APK (Standard Android Package)
This folder is a standard Android Studio Gradle project configured with:
- Target SDK 34 (Android 14) / Min SDK 24 (Android 7.0+).
- Full-screen immersion with custom Deep Emerald brand theme (`#166534`).
- Local LAN cleartext HTTP support for intranet communication (`network_security_config.xml`).
- Hardware camera permissions and web permission bridge for barcode and QR scanning.
- Pull-to-refresh and persistent desktop server address storage with change-dialog.

### How to Build the APK in Android Studio
1. Open **Android Studio**.
2. Select **Open** and choose this directory: `medical_shop/android_app`.
3. Allow Gradle to synchronize dependencies.
4. Click **Build** > **Build Bundle(s) / APK(s)** > **Build APK(s)**.
5. Transfer the generated `app-debug.apk` to your Android device via USB, Bluetooth, or messaging app and install.

---

## Features on Mobile
- ⚡ **Rapid Counter Billing**: Add loose or strip medicines to mobile cart and submit directly to desktop database.
- 💊 **Inventory & Shelf Locator**: Search 5,000+ medicines, batches, and view precise shelf/rack locations.
- 📷 **Aisle Barcode Scanner**: Scan barcodes directly from camera preview to find batch stock and pricing.
- ⚠️ **Expiry Watchlist**: Monitor medicines expiring within the next 90 days right from your phone.
