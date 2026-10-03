import customtkinter as ctk
from utils.dashboard_service import get_dashboard_stats
from utils.medicine_service import get_expired_medicines, get_expiring_soon_medicines, get_low_stock_medicines
from ui.theme import Theme

class DashboardFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.configure(fg_color=Theme.BG_WINDOW)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 1. Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="Dashboard Overview", font=ctk.CTkFont(size=24, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.title_label.pack(side="left")
        
        self.refresh_btn = ctk.CTkButton(self.header_frame, text="🔄 Refresh", width=100, fg_color=Theme.PRIMARY, hover_color=Theme.PRIMARY_HOVER, command=self.refresh)
        self.refresh_btn.pack(side="right")
        
        # Scrollable container for dashboard contents
        self.scroll_container = ctk.CTkScrollableFrame(self, fg_color=Theme.BG_WINDOW)
        self.scroll_container.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.scroll_container.grid_columnconfigure(0, weight=1)
        
        # Cards Layout (Grid: 4 columns)
        self.cards_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        self.cards_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        for col in range(5):
            self.cards_frame.grid_columnconfigure(col, weight=1)
            
        self.cards = {}
        self.create_cards()
        
        # Alerts/Warnings Lists Layout (Side-by-side or stacked panels)
        self.alerts_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        self.alerts_frame.grid(row=1, column=0, sticky="ew", pady=10)
        self.alerts_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="alerts")
        
        self.create_alert_panels()
        
    def create_card(self, parent, title, value, row, col, color=None):
        card = ctk.CTkFrame(parent, fg_color=Theme.BG_CARD, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=10, height=110)
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        
        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12, weight="normal"), text_color=Theme.TEXT_MUTED)
        lbl_title.grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")
        
        lbl_val = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=22, weight="bold"), text_color=color if color else Theme.TEXT_MAIN)
        lbl_val.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="w")
        
        return lbl_val
        
    def create_cards(self):
        # Row 1 of cards
        self.cards['today_sales'] = self.create_card(self.cards_frame, "Today's Sales", "₹0.00", 0, 0, Theme.SUCCESS)
        self.cards['today_profit'] = self.create_card(self.cards_frame, "Today's Profit", "₹0.00", 0, 1, Theme.SUCCESS)
        self.cards['low_stock'] = self.create_card(self.cards_frame, "Low Stock Items", "0", 0, 2, Theme.WARNING)
        self.cards['expiring_soon'] = self.create_card(self.cards_frame, "Expiring Soon (<90d)", "0", 0, 3, Theme.WARNING)
        self.cards['expired'] = self.create_card(self.cards_frame, "Expired Medicines", "0", 0, 4, Theme.DANGER)
        
        # Row 2 of cards
        self.cards['life_sales'] = self.create_card(self.cards_frame, "Lifetime Sales", "₹0.00", 1, 0, Theme.SECONDARY)
        self.cards['life_profit'] = self.create_card(self.cards_frame, "Lifetime Profit", "₹0.00", 1, 1, Theme.SECONDARY)
        self.cards['total_meds'] = self.create_card(self.cards_frame, "Total Medicines", "0", 1, 2, Theme.TEXT_MAIN)
        self.cards['total_batches'] = self.create_card(self.cards_frame, "Total Batches in Stock", "0", 1, 3, Theme.TEXT_MAIN)
        
    def create_alert_panels(self):
        # 1. Expired Medicines Panel (Red)
        self.panel_expired = ctk.CTkFrame(self.alerts_frame, fg_color=Theme.BG_PANEL, border_color=Theme.DANGER, border_width=1, corner_radius=10, height=350)
        self.panel_expired.grid(row=0, column=0, padx=8, sticky="nsew")
        self.panel_expired.grid_rowconfigure(1, weight=1)
        self.panel_expired.grid_columnconfigure(0, weight=1)
        
        title_exp = ctk.CTkLabel(self.panel_expired, text="🔴 Expired Medicines", font=ctk.CTkFont(size=14, weight="bold"), text_color=Theme.DANGER)
        title_exp.grid(row=0, column=0, padx=12, pady=10, sticky="w")
        
        self.scroll_expired = ctk.CTkScrollableFrame(self.panel_expired, fg_color="transparent")
        self.scroll_expired.grid(row=1, column=0, padx=8, pady=5, sticky="nsew")
        
        # 2. Expiring Soon Panel (Orange)
        self.panel_expiring = ctk.CTkFrame(self.alerts_frame, fg_color=Theme.BG_PANEL, border_color=Theme.WARNING, border_width=1, corner_radius=10, height=350)
        self.panel_expiring.grid(row=0, column=1, padx=8, sticky="nsew")
        self.panel_expiring.grid_rowconfigure(1, weight=1)
        self.panel_expiring.grid_columnconfigure(0, weight=1)
        
        title_soon = ctk.CTkLabel(self.panel_expiring, text="🟡 Expiring Soon", font=ctk.CTkFont(size=14, weight="bold"), text_color=Theme.WARNING)
        title_soon.grid(row=0, column=0, padx=12, pady=10, sticky="w")
        
        self.scroll_expiring = ctk.CTkScrollableFrame(self.panel_expiring, fg_color="transparent")
        self.scroll_expiring.grid(row=1, column=0, padx=8, pady=5, sticky="nsew")
        
        # 3. Low Stock Panel (Yellow)
        self.panel_low_stock = ctk.CTkFrame(self.alerts_frame, fg_color=Theme.BG_PANEL, border_color=Theme.SECONDARY, border_width=1, corner_radius=10, height=350)
        self.panel_low_stock.grid(row=0, column=2, padx=8, sticky="nsew")
        self.panel_low_stock.grid_rowconfigure(1, weight=1)
        self.panel_low_stock.grid_columnconfigure(0, weight=1)
        
        title_low = ctk.CTkLabel(self.panel_low_stock, text="⚠️ Low Stock Alert (<20 tabs)", font=ctk.CTkFont(size=14, weight="bold"), text_color=Theme.SECONDARY)
        title_low.grid(row=0, column=0, padx=12, pady=10, sticky="w")
        
        self.scroll_low_stock = ctk.CTkScrollableFrame(self.panel_low_stock, fg_color="transparent")
        self.scroll_low_stock.grid(row=1, column=0, padx=8, pady=5, sticky="nsew")
        
    def populate_alert_list(self, scroll_widget, items, item_type):
        # Clear scroll widget children
        for child in scroll_widget.winfo_children():
            child.destroy()
            
        if not items:
            lbl_empty = ctk.CTkLabel(scroll_widget, text=f"No {item_type} items.", font=ctk.CTkFont(slant="italic"), text_color="gray50")
            lbl_empty.pack(pady=10)
            return
            
        for item in items:
            frame = ctk.CTkFrame(scroll_widget, fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=5)
            frame.pack(fill="x", pady=4, padx=2)
            
            name_lbl = ctk.CTkLabel(frame, text=item['name'], font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.TEXT_MAIN, anchor="w")
            name_lbl.pack(fill="x", padx=10, pady=(6, 2))
            
            meta_str = f"Batch: {item['batch']}"
            if item_type == "expired" or item_type == "expiring soon":
                meta_str += f" | Expiry: {item['expiry_date']}"
            else: # low stock
                meta_str += f" | Qty: {item['total_tablets']} tabs ({item['stock_string']})"
                
            meta_lbl = ctk.CTkLabel(frame, text=meta_str, font=ctk.CTkFont(size=10), text_color=Theme.TEXT_MUTED, anchor="w")
            meta_lbl.pack(fill="x", padx=10, pady=(0, 6))
            
            # Interactive click to restock if low stock
            if item_type == "low stock":
                frame.configure(cursor="hand2")
                frame.bind("<Button-1>", lambda event, it=item: self.goto_purchases_restock(it))
                name_lbl.bind("<Button-1>", lambda event, it=item: self.goto_purchases_restock(it))
                meta_lbl.bind("<Button-1>", lambda event, it=item: self.goto_purchases_restock(it))

    def refresh(self):
        # Fetch stats from db services
        stats = get_dashboard_stats()
        
        # Populate cards
        self.cards['today_sales'].configure(text=f"₹{stats['today_sales']:.2f}")
        self.cards['today_profit'].configure(text=f"₹{stats['today_profit']:.2f}")
        self.cards['low_stock'].configure(text=str(stats['low_stock_count']))
        self.cards['expiring_soon'].configure(text=str(stats['expiring_soon_count']))
        self.cards['expired'].configure(text=str(stats['expired_count']))
        self.cards['life_sales'].configure(text=f"₹{stats['lifetime_sales']:.2f}")
        self.cards['life_profit'].configure(text=f"₹{stats['lifetime_profit']:.2f}")
        self.cards['total_meds'].configure(text=str(stats['total_medicines']))
        self.cards['total_batches'].configure(text=str(stats['total_batches']))
        
        # Populate alerts lists
        expired_list = get_expired_medicines()
        expiring_list = get_expiring_soon_medicines()
        low_stock_list = get_low_stock_medicines()
        
        self.populate_alert_list(self.scroll_expired, expired_list, "expired")
        self.populate_alert_list(self.scroll_expiring, expiring_list, "expiring soon")
        self.populate_alert_list(self.scroll_low_stock, low_stock_list, "low stock")
        
    def goto_purchases_restock(self, item):
        from ui.purchases import PurchasesFrame
        self.controller.select_frame("Buy / Purchases", PurchasesFrame)
        if hasattr(self.controller.active_frame, "prefill_restock"):
            self.controller.active_frame.prefill_restock(
                item['name'], 
                item['manufacturer'], 
                item['tablets_per_strip'], 
                item['threshold']
            )
