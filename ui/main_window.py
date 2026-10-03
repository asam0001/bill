import os
import customtkinter as ctk
from database.db import init_db

# Set appearance and theme
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")
from ui.theme import Theme

# Import login view
from ui.login import LoginFrame

# Import module views
from ui.home import HomeFrame
from ui.billing import BillingFrame
from ui.purchases import PurchasesFrame
from ui.stock import StockFrame
from ui.expiry import ExpiryFrame
from ui.suppliers import SuppliersFrame
from ui.customers import CustomersFrame
from ui.sales_history import SalesHistoryFrame
from ui.returns import ReturnsFrame
from ui.reports import ReportsFrame
from ui.accounts import AccountsFrame
from ui.settings import SettingsFrame

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Initialize Database
        init_db()
        
        # Window configuration
        self.title("MediTrack Pharmacy ERP")
        self.geometry("1400x850")
        self.minsize(1200, 750)
        self.configure(fg_color=Theme.BG_WINDOW)
        
        # Load Window Icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass
        
        # Session state
        self.current_user = None
        self.current_role = None
        
        # Configure layout (2 columns: Sidebar and Content Container)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Left Sidebar (Initially hidden until login success)
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=Theme.BG_SIDEBAR)
        self.sidebar_frame.grid_propagate(False)
        
        # Title/Logo in sidebar
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="🏥 MediTrack ERP", font=ctk.CTkFont(size=18, weight="bold"), text_color="#FFFFFF")
        self.logo_label.pack(pady=(20, 15))
        
        # Active User indicator in sidebar
        self.user_lbl = ctk.CTkLabel(self.sidebar_frame, text="", font=ctk.CTkFont(size=11, slant="italic"), text_color="#A7B0A9")
        self.user_lbl.pack(pady=(0, 15))
        
        # Navigation Buttons list
        self.nav_buttons = {}
        self.nav_items = [
            ("Dashboard", HomeFrame),
            ("Billing / POS", BillingFrame),
            ("Purchases", PurchasesFrame),
            ("Stock Inventory", StockFrame),
            ("Expiry Tracker", ExpiryFrame),
            ("Suppliers", SuppliersFrame),
            ("Customers", CustomersFrame),
            ("Sales History", SalesHistoryFrame),
            ("Returns Manager", ReturnsFrame),
            ("Reports & Stats", ReportsFrame),
            ("Accounts / Ledger", AccountsFrame),
            ("System Settings", SettingsFrame)
        ]
        
        # Main Content Frame Container
        self.content_container = ctk.CTkFrame(self, corner_radius=0, fg_color=Theme.BG_WINDOW)
        self.content_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)
        
        self.active_frame = None
        
        # Load Login Screen by default
        self.show_login_screen()

        # Clean shutdown hook for background threads and mobile server
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def show_login_screen(self):
        # Hide sidebar
        self.sidebar_frame.grid_forget()
        # Clean active frame
        if self.active_frame is not None:
            self.active_frame.destroy()
            
        self.active_frame = LoginFrame(self.content_container, self)
        self.active_frame.grid(row=0, column=0, sticky="nsew")
        
    def on_login_success(self, username, role):
        self.current_user = username
        self.current_role = role
        
        # Configure and show sidebar
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.user_lbl.configure(text=f"User: {username} ({role})")
        
        # Clear existing navigation buttons
        for btn in self.nav_buttons.values():
            btn.destroy()
        self.nav_buttons.clear()
        
        # Populate sidebar items based on role authorization
        # Admin: everything
        # Pharmacist: No Accounts, Settings
        # Cashier: Only Dashboard, Billing, Stock, Sales History
        for name, frame_cls in self.nav_items:
            # Check permissions
            if role == "Cashier" and name not in ["Dashboard", "Billing / POS", "Stock Inventory", "Expiry Tracker", "Sales History"]:
                continue
            if role == "Pharmacist" and name in ["Accounts / Ledger", "System Settings"]:
                continue
                
            btn = ctk.CTkButton(
                self.sidebar_frame, 
                text=name, 
                anchor="w",
                height=35,
                fg_color="transparent",
                text_color="#F1F5F2",
                hover_color="#14532D",
                command=lambda n=name, f=frame_cls: self.select_frame(n, f)
            )
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[name] = btn
            
        # Add Logout Button at the bottom
        self.logout_btn = ctk.CTkButton(
            self.sidebar_frame, 
            text="🚪 Sign Out", 
            anchor="w",
            height=35,
            fg_color="transparent",
            text_color="#FCA5A5",
            hover_color="#7F1D1D",
            command=self.show_login_screen
        )
        self.logout_btn.pack(side="bottom", fill="x", padx=12, pady=15)
        
        # Select default frame
        self.select_frame("Dashboard", HomeFrame)
        
    def select_frame(self, name, frame_class):
        # Centralized Role Permission Validation
        role = self.current_role
        if role == "Cashier" and name not in ["Dashboard", "Billing / POS", "Stock Inventory", "Expiry Tracker", "Sales History"]:
            messagebox.showerror("Access Denied", f"Your role ({role}) does not have permission to access '{name}'.")
            return
        if role == "Pharmacist" and name in ["Accounts / Ledger", "System Settings"]:
            messagebox.showerror("Access Denied", f"Your role ({role}) does not have permission to access '{name}'.")
            return

        # Update active states for sidebar navigation buttons
        for btn_name, btn in self.nav_buttons.items():
            if btn_name == name:
                btn.configure(fg_color=Theme.PRIMARY, text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color="#F1F5F2")
                
        if self.active_frame is not None:
            self.active_frame.destroy()
            
        self.active_frame = frame_class(self.content_container, self)
        self.active_frame.grid(row=0, column=0, sticky="nsew")
        
        if hasattr(self.active_frame, "refresh"):
            self.active_frame.refresh()

    def on_close(self):
        """Ensures background mobile server and threads are cleanly terminated upon exit."""
        try:
            from mobile_server import get_mobile_server
            get_mobile_server().stop()
        except Exception:
            pass
        self.destroy()

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
