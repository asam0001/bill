import customtkinter as ctk
from tkinter import messagebox
from ui.theme import Theme
from database.db import get_connection

class LoginFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.configure(fg_color=Theme.BG_WINDOW)
        
        # Center Login Box
        self.grid_rowconfigure((0, 2), weight=1)
        self.grid_columnconfigure((0, 2), weight=1)
        
        self.login_box = ctk.CTkFrame(self, width=400, height=450, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=15)
        self.login_box.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")
        self.login_box.grid_propagate(False)
        
        self.login_box.grid_columnconfigure(0, weight=1)
        
        # Header / Title
        self.logo_label = ctk.CTkLabel(self.login_box, text="🏥 MediTrack ERP", font=ctk.CTkFont(size=24, weight="bold"), text_color=Theme.PRIMARY)
        self.logo_label.pack(pady=(40, 5))
        
        self.subtitle_label = ctk.CTkLabel(self.login_box, text="Pharmacy Management System", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED)
        self.subtitle_label.pack(pady=(0, 30))
        
        # Username Input
        self.username_label = ctk.CTkLabel(self.login_box, text="Username", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        self.username_label.pack(anchor="w", padx=40, pady=(10, 2))
        
        self.username_entry = ctk.CTkEntry(self.login_box, placeholder_text="Enter username...", height=35, fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.username_entry.pack(fill="x", padx=40, pady=(0, 15))
        
        # Password Input
        self.password_label = ctk.CTkLabel(self.login_box, text="Password", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        self.password_label.pack(anchor="w", padx=40, pady=(5, 2))
        
        self.password_entry = ctk.CTkEntry(self.login_box, placeholder_text="Enter password...", show="*", height=35, fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.password_entry.pack(fill="x", padx=40, pady=(0, 25))
        
        # Bind Enter key to login
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())
        self.password_entry.bind("<Return>", lambda e: self.attempt_login())
        
        # Login Button
        self.login_btn = ctk.CTkButton(
            self.login_box, 
            text="Secure Sign In", 
            height=40, 
            fg_color=Theme.PRIMARY, 
            hover_color=Theme.PRIMARY_HOVER,
            command=self.attempt_login
        )
        self.login_btn.pack(fill="x", padx=40, pady=10)
        
        # Auto focus username
        self.username_entry.focus()
        
    def attempt_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("Login Error", "Please fill in all fields.")
            return
            
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE username = ? AND password_hash = ?;", (username.lower(), password))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            role = row['role']
            self.controller.on_login_success(username, role)
        else:
            messagebox.showerror("Authentication Failed", "Invalid username or password.")
