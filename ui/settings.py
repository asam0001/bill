import os
import webbrowser
import customtkinter as ctk
from tkinter import messagebox
from utils.settings_service import get_all_settings, update_settings
from utils.backup_service import backup_database, restore_database, list_backups
from mobile_server import get_local_ip
from ui.theme import Theme

class SettingsFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(fg_color=Theme.BG_WINDOW)
        
        # Configure layout (2 columns: Shop Settings left, Backup/Restore right)
        self.grid_columnconfigure(0, weight=1) # Left (Shop config & mobile pairing)
        self.grid_columnconfigure(1, weight=1) # Right (Database backup manager)
        self.grid_rowconfigure(0, weight=1)
        
        # --- LEFT PANEL: SHOP SETTINGS & MOBILE COMPANION ---
        self.left_panel = ctk.CTkFrame(self, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=10)
        self.left_panel.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="nsew")
        self.left_panel.grid_columnconfigure(0, weight=1)
        
        self.lbl_title = ctk.CTkLabel(self.left_panel, text="⚙️ Pharmacy Profile Settings", font=ctk.CTkFont(size=18, weight="bold"), text_color=Theme.PRIMARY)
        self.lbl_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Input Form Elements
        self.fields = {}
        fields_def = [
            ("Shop Trade Name *", "shop_name", "e.g. MediTrack Wellness Pharmacy"),
            ("Registered Pharmacist / Owner *", "owner_name", "e.g. Dr. Ramesh Verma"),
            ("Contact Phone *", "phone", "e.g. 9876543210"),
            ("GST Registration Number", "gst_number", "e.g. 29ABCDE1234F1Z5"),
            ("UPI ID for QR Billing", "upi_id", "e.g. pharmacy@upi"),
            ("Physical Store Address", "address", "e.g. Shop #4, Medical District")
        ]
        
        current_row = 1
        for label, key, placeholder in fields_def:
            lbl = ctk.CTkLabel(self.left_panel, text=label, font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
            lbl.grid(row=current_row, column=0, padx=20, pady=(6, 1), sticky="w")
            
            if key == "address":
                entry = ctk.CTkTextbox(self.left_panel, height=65, fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR, border_width=1, text_color=Theme.TEXT_MAIN)
            else:
                entry = ctk.CTkEntry(self.left_panel, placeholder_text=placeholder, fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR, text_color=Theme.TEXT_MAIN)
                
            entry.grid(row=current_row+1, column=0, padx=20, pady=(0, 6), sticky="ew")
            self.fields[key] = entry
            current_row += 2
            
        # Save Button
        self.btn_save_config = ctk.CTkButton(
            self.left_panel, 
            text="💾 Save Configuration", 
            height=36, 
            fg_color=Theme.SUCCESS, 
            hover_color=Theme.SUCCESS_HOVER,
            text_color="white",
            command=self.save_shop_settings
        )
        self.btn_save_config.grid(row=current_row, column=0, padx=20, pady=(12, 10), sticky="ew")
        current_row += 1

        # Mobile Companion Section
        self.mobile_frame = ctk.CTkFrame(self.left_panel, fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=8)
        self.mobile_frame.grid(row=current_row, column=0, padx=20, pady=(0, 15), sticky="ew")
        self.mobile_frame.grid_columnconfigure(0, weight=1)

        lbl_mob_title = ctk.CTkLabel(self.mobile_frame, text="📱 Mobile Companion App (Offline LAN PWA)", font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.PRIMARY)
        lbl_mob_title.pack(anchor="w", padx=15, pady=(10, 2))

        local_ip = get_local_ip()
        self.mobile_url = f"http://{local_ip}:8080"
        self.lbl_mob_url = ctk.CTkLabel(self.mobile_frame, text=f"Wi-Fi URL: {self.mobile_url}", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED)
        self.lbl_mob_url.pack(anchor="w", padx=15, pady=(0, 8))

        mob_btn_row = ctk.CTkFrame(self.mobile_frame, fg_color="transparent")
        mob_btn_row.pack(fill="x", padx=15, pady=(0, 10))
        mob_btn_row.grid_columnconfigure((0, 1), weight=1)

        self.btn_open_mob = ctk.CTkButton(
            mob_btn_row, text="🌐 Open Browser", height=30,
            fg_color=Theme.PRIMARY, hover_color=Theme.PRIMARY_HOVER,
            command=self.open_mobile_browser
        )
        self.btn_open_mob.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.btn_show_qr = ctk.CTkButton(
            mob_btn_row, text="📷 Pairing QR", height=30,
            fg_color=Theme.SECONDARY, hover_color=Theme.SECONDARY_HOVER,
            command=self.show_pairing_qr_dialog
        )
        self.btn_show_qr.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # Security & Password Section
        self.btn_change_pw = ctk.CTkButton(
            self.left_panel,
            text="🔐 Change Login Password",
            height=34,
            fg_color="#374151",
            hover_color="#1F2937",
            text_color="white",
            command=self.show_change_password_dialog
        )
        self.btn_change_pw.grid(row=current_row+1, column=0, padx=20, pady=(0, 15), sticky="ew")
        
        # --- RIGHT PANEL: BACKUP & RESTORE ---
        self.right_panel = ctk.CTkFrame(self, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=10)
        self.right_panel.grid(row=0, column=1, padx=(10, 15), pady=15, sticky="nsew")
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(3, weight=1)
        
        self.lbl_right_title = ctk.CTkLabel(self.right_panel, text="💾 Database Backup & Disaster Recovery", font=ctk.CTkFont(size=18, weight="bold"), text_color=Theme.SECONDARY)
        self.lbl_right_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Trigger Backup Box
        self.btn_backup = ctk.CTkButton(
            self.right_panel, 
            text="📥 Create Instant Online Backup", 
            height=40, 
            fg_color=Theme.SECONDARY, 
            hover_color=Theme.SECONDARY_HOVER,
            text_color="white",
            command=self.create_backup
        )
        self.btn_backup.grid(row=1, column=0, padx=20, pady=(5, 15), sticky="ew")
        
        # Backups List Section
        self.lbl_backups_list = ctk.CTkLabel(self.right_panel, text="Historical Backup Restore Points", font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.TEXT_LIGHT)
        self.lbl_backups_list.grid(row=2, column=0, padx=20, pady=(10, 2), sticky="w")
        
        self.backups_scroll = ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent")
        self.backups_scroll.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.backups_scroll.grid_columnconfigure(0, weight=1)
        
    def refresh(self):
        # Load Shop Configuration settings
        settings = get_all_settings()
        
        self.fields['shop_name'].delete(0, "end")
        self.fields['shop_name'].insert(0, settings.get('shop_name', ''))
        
        self.fields['owner_name'].delete(0, "end")
        self.fields['owner_name'].insert(0, settings.get('owner_name', ''))
        
        self.fields['phone'].delete(0, "end")
        self.fields['phone'].insert(0, settings.get('phone', ''))
        
        self.fields['gst_number'].delete(0, "end")
        self.fields['gst_number'].insert(0, settings.get('gst_number', ''))
        
        self.fields['upi_id'].delete(0, "end")
        self.fields['upi_id'].insert(0, settings.get('upi_id', ''))
        
        self.fields['address'].delete("1.0", "end")
        self.fields['address'].insert("1.0", settings.get('address', ''))
        
        # Update mobile url
        local_ip = get_local_ip()
        self.mobile_url = f"http://{local_ip}:8080"
        self.lbl_mob_url.configure(text=f"Wi-Fi URL: {self.mobile_url}")

        # Load Backup list
        self.populate_backups_list()
        
    def populate_backups_list(self):
        for child in self.backups_scroll.winfo_children():
            child.destroy()
            
        try:
            backups = list_backups()
        except Exception:
            backups = []
            
        if not backups:
            lbl_empty = ctk.CTkLabel(self.backups_scroll, text="No backup restore points found.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
            lbl_empty.pack(pady=20)
            return
            
        for idx, backup in enumerate(backups):
            row_bg = Theme.BG_WINDOW if idx % 2 == 0 else Theme.BG_PANEL
            row = ctk.CTkFrame(self.backups_scroll, fg_color=row_bg, border_color=Theme.BORDER_COLOR, border_width=1, height=44, corner_radius=5)
            row.pack(fill="x", pady=3, padx=2)
            row.grid_propagate(False)
            row.grid_rowconfigure(0, weight=1)
            row.grid_columnconfigure(0, weight=3) # Filename info
            row.grid_columnconfigure(1, weight=1) # Restore button
            
            # Tag safety snapshots
            tag = " [Emergency Snapshot]" if backup.get("is_safety_snapshot") else ""
            info_text = f"📄 {backup['filename']}{tag}\n🕒 {backup['time']} ({backup['size']})"
            lbl_info = ctk.CTkLabel(row, text=info_text, justify="left", font=ctk.CTkFont(size=10), text_color=Theme.TEXT_LIGHT, anchor="w")
            lbl_info.grid(row=0, column=0, padx=10, sticky="ew")
            
            # Restore trigger button
            btn_restore = ctk.CTkButton(
                row, 
                text="↩️ Restore", 
                width=70, 
                height=25, 
                fg_color=Theme.WARNING, 
                hover_color=Theme.WARNING_HOVER,
                text_color="white",
                command=lambda fname=backup['filename']: self.trigger_restore(fname)
            )
            btn_restore.grid(row=0, column=1, padx=10, sticky="")
            
    def save_shop_settings(self):
        shop_name = self.fields['shop_name'].get().strip()
        owner_name = self.fields['owner_name'].get().strip()
        phone = self.fields['phone'].get().strip()
        gst_number = self.fields['gst_number'].get().strip()
        upi_id = self.fields['upi_id'].get().strip()
        address = self.fields['address'].get("1.0", "end").strip()
        
        if not shop_name:
            messagebox.showerror("Validation Error", "Shop Name is required.")
            return
            
        settings_dict = {
            "shop_name": shop_name,
            "owner_name": owner_name,
            "phone": phone,
            "gst_number": gst_number,
            "upi_id": upi_id,
            "address": address
        }
        
        try:
            update_settings(settings_dict)
            messagebox.showinfo("Success", "Shop settings updated successfully.")
            self.refresh()
        except Exception as ex:
            messagebox.showerror("Error Saving", str(ex))
            
    def create_backup(self):
        try:
            backup_path = backup_database()
            messagebox.showinfo("Backup Successful", f"Database backed up successfully.\nFilename: {os.path.basename(backup_path)}")
            self.populate_backups_list()
        except Exception as ex:
            messagebox.showerror("Backup Failed", str(ex))
            
    def trigger_restore(self, backup_filename):
        confirm = messagebox.askyesno(
            "Confirm Database Restore",
            f"Are you sure you want to restore the database to '{backup_filename}'?\n\n"
            "An emergency safety snapshot of your current database will be saved automatically beforehand."
        )
        if confirm:
            try:
                restore_database(backup_filename)
                messagebox.showinfo("Restore Successful", "Database restored successfully.")
                self.refresh()
            except Exception as ex:
                messagebox.showerror("Restore Failed", str(ex))

    def open_mobile_browser(self):
        try:
            webbrowser.open(self.mobile_url)
        except Exception as ex:
            messagebox.showerror("Browser Error", f"Could not open browser: {ex}")

    def show_pairing_qr_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Mobile Companion Pairing")
        dialog.geometry("340x400")
        dialog.resizable(False, False)
        dialog.configure(fg_color=Theme.BG_WINDOW)
        dialog.transient(self)
        dialog.grab_set()

        lbl_header = ctk.CTkLabel(
            dialog, text="Scan with Phone Camera", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            text_color=Theme.PRIMARY
        )
        lbl_header.pack(pady=(18, 4))

        lbl_sub = ctk.CTkLabel(
            dialog, text=f"Connect phone to same Wi-Fi:\n{self.mobile_url}", 
            font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED
        )
        lbl_sub.pack(pady=(0, 12))

        try:
            import qrcode
            qr = qrcode.QRCode(box_size=6, border=2)
            qr.add_data(self.mobile_url)
            qr.make(fit=True)
            pil_img = qr.make_image(fill_color="#166534", back_color="white").get_image()
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(190, 190))

            lbl_qr = ctk.CTkLabel(dialog, image=ctk_img, text="")
            lbl_qr.pack(pady=4)
        except Exception as ex:
            lbl_err = ctk.CTkLabel(dialog, text=f"QR Error: {ex}", text_color=Theme.DANGER)
            lbl_err.pack(pady=20)

        btn_close = ctk.CTkButton(
            dialog, text="Done", width=120, height=32,
            fg_color=Theme.PRIMARY, hover_color=Theme.PRIMARY_HOVER,
            command=dialog.destroy
        )
        btn_close.pack(pady=16)

    def show_change_password_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Change Account Password")
        dialog.geometry("380x380")
        dialog.resizable(False, False)
        dialog.configure(fg_color=Theme.BG_WINDOW)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="🔐 Update Account Password", font=ctk.CTkFont(size=16, weight="bold"), text_color=Theme.PRIMARY).pack(pady=(20, 10))

        active_user = getattr(self.controller, "current_user", "admin") or "admin"
        ctk.CTkLabel(dialog, text=f"Active Account: {active_user}", font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.TEXT_MAIN).pack(pady=(0, 15))

        old_pw = ctk.CTkEntry(dialog, placeholder_text="Current Password...", show="*", width=280, height=35)
        old_pw.pack(pady=6)

        new_pw = ctk.CTkEntry(dialog, placeholder_text="New Password (min 6 characters)...", show="*", width=280, height=35)
        new_pw.pack(pady=6)

        confirm_pw = ctk.CTkEntry(dialog, placeholder_text="Confirm New Password...", show="*", width=280, height=35)
        confirm_pw.pack(pady=6)

        def save_pw():
            cur = old_pw.get().strip()
            npw = new_pw.get().strip()
            cpw = confirm_pw.get().strip()
            if not cur or not npw:
                messagebox.showerror("Error", "Please fill in all fields.", parent=dialog)
                return
            if npw != cpw:
                messagebox.showerror("Mismatch", "New password and confirmation do not match.", parent=dialog)
                return
            if len(npw) < 6:
                messagebox.showerror("Security Policy", "New password must be at least 6 characters long.", parent=dialog)
                return

            from utils.security import change_password
            ok, msg = change_password(active_user, cur, npw)
            if ok:
                messagebox.showinfo("Success", "Password updated successfully!", parent=dialog)
                dialog.destroy()
            else:
                messagebox.showerror("Failed", msg, parent=dialog)

        ctk.CTkButton(dialog, text="Update Password", fg_color=Theme.PRIMARY, hover_color=Theme.PRIMARY_HOVER, command=save_pw, width=280, height=38).pack(pady=16)
