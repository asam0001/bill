import customtkinter as ctk
from datetime import datetime, timedelta
from utils.medicine_service import get_expired_medicines, get_expiring_soon_medicines
from ui.theme import Theme
from ui.components import PageHeader, DataTable, StatCard

class ExpiryFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.configure(fg_color=Theme.BG_WINDOW)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        
        # 1. Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        
        self.title = ctk.CTkLabel(self.header_frame, text="⏳ Medicine Expiry Tracker", font=ctk.CTkFont(size=24, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.title.pack(side="left")
        
        # 2. Expiry Metrics Row
        self.metrics_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.metrics_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.metrics_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        self.card_expired = StatCard(self.metrics_frame, title="Already Expired", value="0", color_accent=Theme.DANGER, icon="🔴")
        self.card_expired.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        self.card_critical = StatCard(self.metrics_frame, title="Critical (<30 Days)", value="0", color_accent=Theme.WARNING, icon="⚠️")
        self.card_critical.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.card_warning = StatCard(self.metrics_frame, title="Warning (<90 Days)", value="0", color_accent=Theme.SECONDARY, icon="🟡")
        self.card_warning.grid(row=0, column=2, padx=5, sticky="ew")
        
        self.card_upcoming = StatCard(self.metrics_frame, title="Upcoming (<180 Days)", value="0", color_accent=Theme.SUCCESS, icon="🔵")
        self.card_upcoming.grid(row=0, column=3, padx=(5, 0), sticky="ew")
        
        # 3. Filter Bar (Segmented Button)
        self.filter_var = ctk.StringVar(value="Expired")
        self.filter_btn = ctk.CTkSegmentedButton(
            self, 
            values=["Expired", "Critical (<30d)", "Warning (<90d)", "Upcoming (<180d)"], 
            variable=self.filter_var, 
            command=self.on_filter_change,
            fg_color=Theme.BG_PANEL, 
            selected_color=Theme.PRIMARY, 
            selected_hover_color=Theme.PRIMARY
        )
        self.filter_btn.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="ew")
        
        # 4. Table Headers
        self.headers_bar = ctk.CTkFrame(self, fg_color=Theme.BG_PANEL, height=35, corner_radius=5)
        self.headers_bar.grid(row=3, column=0, padx=20, pady=(5, 0), sticky="ew")
        self.headers_bar.grid_propagate(False)
        self.headers_bar.grid_rowconfigure(0, weight=1)
        
        self.column_weights = [0.3, 0.1, 0.12, 0.12, 0.23, 0.13]
        headers = ["Medicine Name", "Batch", "Expiry Date", "Qty (Tablets)", "Supplier", "Rack Shelf"]
        for idx, (h_name, w) in enumerate(zip(headers, self.column_weights)):
            self.headers_bar.grid_columnconfigure(idx, weight=int(w * 100))
            lbl = ctk.CTkLabel(self.headers_bar, text=h_name, font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
            lbl.grid(row=0, column=idx, padx=10, sticky="w" if idx == 0 else "")
            
        # 5. Scrollable Data Grid
        self.data_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.data_scroll.grid(row=4, column=0, padx=20, pady=(5, 15), sticky="nsew")
        self.grid_rowconfigure(4, weight=1)
        self.data_scroll.grid_columnconfigure(0, weight=1)
        
    def refresh(self):
        # Update metrics values
        expired_count = len(get_expired_medicines())
        crit_count = len(get_expiring_soon_medicines(days_threshold=30))
        warn_count = len(get_expiring_soon_medicines(days_threshold=90))
        upc_count = len(get_expiring_soon_medicines(days_threshold=180))
        
        self.card_expired.update_value(expired_count)
        self.card_critical.update_value(crit_count)
        self.card_warning.update_value(warn_count)
        self.card_upcoming.update_value(upc_count)
        
        self.on_filter_change()
        
    def on_filter_change(self, value=None):
        if value is None:
            value = self.filter_var.get()
            
        # Clear table
        for child in self.data_scroll.winfo_children():
            child.destroy()
            
        # Get data
        if value == "Expired":
            data = get_expired_medicines()
            accent_color = Theme.DANGER
        elif "Critical" in value:
            data = get_expiring_soon_medicines(days_threshold=30)
            accent_color = Theme.WARNING
        elif "Warning" in value:
            data = get_expiring_soon_medicines(days_threshold=90)
            accent_color = Theme.SECONDARY
        else:
            data = get_expiring_soon_medicines(days_threshold=180)
            accent_color = Theme.SUCCESS
            
        if not data:
            lbl = ctk.CTkLabel(self.data_scroll, text=f"No medicines found in '{value}' warning state.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
            lbl.pack(pady=40)
            return
            
        for idx, med in enumerate(data):
            bg = Theme.BG_WINDOW if idx % 2 == 0 else Theme.BG_PANEL
            row_frame = ctk.CTkFrame(self.data_scroll, fg_color=bg, height=40, corner_radius=5)
            row_frame.pack(fill="x", pady=2, padx=1)
            row_frame.grid_propagate(False)
            row_frame.grid_rowconfigure(0, weight=1)
            
            # Left accent color block
            bar = ctk.CTkFrame(row_frame, width=4, fg_color=accent_color, corner_radius=0)
            bar.place(x=0, y=0, relheight=1.0)
            
            col_vals = [
                med['name'],
                med['batch'],
                med['expiry_date'],
                f"{med['total_tablets']} tab",
                med['supplier_name'] or "N/A",
                med['rack_shelf'] or "N/A"
            ]
            
            for c_idx, (val, w) in enumerate(zip(col_vals, self.column_weights)):
                row_frame.grid_columnconfigure(c_idx, weight=int(w * 100))
                lbl = ctk.CTkLabel(row_frame, text=str(val), font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MAIN if c_idx != 2 else accent_color, anchor="w" if c_idx == 0 else "center")
                lbl.grid(row=0, column=c_idx, padx=10, sticky="ew" if c_idx == 0 else "")
