import customtkinter as ctk
from datetime import datetime
from ui.theme import Theme
from utils.dashboard_service import get_dashboard_stats

class HomeFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.configure(fg_color=Theme.BG_WINDOW)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 1. Welcome Header Area
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        
        # Title & Date
        self.title_label = ctk.CTkLabel(self.header_frame, text="🏥 MediTrack ERP Dashboard", font=ctk.CTkFont(size=24, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.title_label.pack(side="left")
        
        self.date_label = ctk.CTkLabel(self.header_frame, text="", font=ctk.CTkFont(size=13, weight="bold"), text_color=Theme.TEXT_MUTED)
        self.date_label.pack(side="right", padx=10)
        self.update_clock()
        
        # Scrollable container for home contents
        self.scroll_container = ctk.CTkScrollableFrame(self, fg_color=Theme.BG_WINDOW)
        self.scroll_container.grid(row=1, column=0, padx=20, pady=5, sticky="nsew")
        self.scroll_container.grid_columnconfigure(0, weight=1)
        
        # Metrics Cards Row (Grid: 4 columns)
        self.cards_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        self.cards_frame.grid(row=0, column=0, sticky="ew", pady=(0, 25))
        for col in range(4):
            self.cards_frame.grid_columnconfigure(col, weight=1)
            
        self.metric_cards = {}
        self.create_metric_cards()
        
        # Section Label: Shortcuts Grid
        self.shortcut_header = ctk.CTkLabel(self.scroll_container, text="Quick Access Modules", font=ctk.CTkFont(size=16, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.shortcut_header.grid(row=1, column=0, sticky="w", pady=(10, 15))
        
        # Shortcuts Grid (3 columns, 3 rows)
        self.grid_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        self.grid_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        for col in range(3):
            self.grid_frame.grid_columnconfigure(col, weight=1)
            
        self.create_navigation_grid()
        
    def create_card(self, parent, title, value, col, color=None):
        card = ctk.CTkFrame(parent, fg_color=Theme.BG_CARD, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=10, height=95)
        card.grid(row=0, column=col, padx=8, pady=5, sticky="nsew")
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        
        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11, weight="normal"), text_color=Theme.TEXT_MUTED)
        lbl_title.grid(row=0, column=0, padx=12, pady=(10, 2), sticky="w")
        
        lbl_val = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=20, weight="bold"), text_color=color if color else Theme.TEXT_MAIN)
        lbl_val.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="w")
        
        return lbl_val
 
    def create_metric_cards(self):
        self.metric_cards['today_sales'] = self.create_card(self.cards_frame, "Today's Sales", "₹0.00", 0, Theme.SUCCESS)
        self.metric_cards['today_profit'] = self.create_card(self.cards_frame, "Today's Net Profit", "₹0.00", 1, Theme.SUCCESS)
        self.metric_cards['unpaid_total'] = self.create_card(self.cards_frame, "Customer Dues (Receivables)", "₹0.00", 2, Theme.DANGER)
        self.metric_cards['low_stock'] = self.create_card(self.cards_frame, "Low Stock Alerts", "0", 3, Theme.WARNING)
        
    def create_navigation_grid(self):
        # We need to import all frame classes inside the function to avoid circular dependencies
        from ui.billing import BillingFrame
        from ui.stock import StockFrame
        from ui.purchases import PurchasesFrame
        from ui.sales_history import SalesHistoryFrame
        from ui.reports import ReportsFrame
        from ui.suppliers import SuppliersFrame
        from ui.customers import CustomersFrame
        from ui.returns import ReturnsFrame
        from ui.accounts import AccountsFrame
        from ui.expiry import ExpiryFrame
        
        shortcuts = [
            # (Title, Description, Icon, Frame Class, Active Tab Name, Color Accent, Grid Row, Grid Col)
            ("Billing / POS", "Checkout customers, apply discounts, select payment mode.", "🛒", BillingFrame, "Billing / POS", Theme.PRIMARY, 0, 0),
            ("Stock Inventory", "Track medicine batches, reorder lists, and product master details.", "📦", StockFrame, "Stock Inventory", Theme.SUCCESS, 0, 1),
            ("Buy / Purchases", "Record bulk inventory invoices, add batches, and update prices.", "📥", PurchasesFrame, "Purchases", Theme.SECONDARY, 0, 2),
            ("Sales History", "Search past invoices, review items, and reprint receipts.", "📜", SalesHistoryFrame, "Sales History", Theme.PRIMARY, 1, 0),
            ("Reports & Analytics", "Visual line graphs of revenue, margins, and sales exports.", "📊", ReportsFrame, "Reports & Stats", Theme.SUCCESS, 1, 1),
            ("Suppliers Directory", "Registry of wholesale distributors and credit ledgers.", "🤝", SuppliersFrame, "Suppliers", Theme.SECONDARY, 1, 2),
            ("Customer Dues", "Track credit customer limits, outstanding balances, and bills.", "👤", CustomersFrame, "Customers", Theme.DANGER, 2, 0),
            ("Ledger & Payments", "Log collections and payables to clear pending invoices.", "💼", AccountsFrame, "Accounts / Ledger", Theme.WARNING, 2, 1),
            ("Expiry Tracker", "Audit expiring and critical medicine stock batches.", "⏳", ExpiryFrame, "Expiry Tracker", Theme.TEXT_MUTED, 2, 2)
        ]
        
        for name, desc, icon, frame_cls, tab_name, accent, row, col in shortcuts:
            self.create_shortcut_tile(self.grid_frame, name, desc, icon, frame_cls, tab_name, accent, row, col)
            
    def create_shortcut_tile(self, parent, name, desc, icon, frame_cls, tab_name, accent, row, col):
        tile = ctk.CTkFrame(parent, fg_color=Theme.BG_CARD, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=10, cursor="hand2")
        tile.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        
        # Grid weight config for parent frame to ensure correct cell sizes
        parent.grid_rowconfigure(row, weight=1)
        
        # Left Accent bar
        accent_bar = ctk.CTkFrame(tile, width=4, fg_color=accent, corner_radius=0)
        accent_bar.pack(side="left", fill="y")
        
        # Content Frame
        content_frame = ctk.CTkFrame(tile, fg_color="transparent")
        content_frame.pack(side="left", fill="both", expand=True)
        
        # Inner content Layout
        header_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(15, 5))
        
        lbl_icon = ctk.CTkLabel(header_frame, text=icon, font=ctk.CTkFont(size=20))
        lbl_icon.pack(side="left", padx=(0, 10))
        
        lbl_name = ctk.CTkLabel(header_frame, text=name, font=ctk.CTkFont(size=14, weight="bold"), text_color=Theme.TEXT_MAIN)
        lbl_name.pack(side="left")
        
        lbl_desc = ctk.CTkLabel(content_frame, text=desc, font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED, justify="left", wraplength=220)
        lbl_desc.pack(fill="x", padx=15, pady=(0, 15), anchor="w")
        
        # Interactive Hover Effects
        def on_enter(event, t=tile, c=accent):
            t.configure(border_color=c)
            
        def on_leave(event, t=tile):
            t.configure(border_color=Theme.BORDER_COLOR)
            
        def on_click(event, n=tab_name, fc=frame_cls):
            self.controller.select_frame(n, fc)
            
        # Bind events recursively to children so clicking anywhere works
        for widget in [tile, accent_bar, content_frame, header_frame, lbl_icon, lbl_name, lbl_desc]:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            widget.bind("<Button-1>", on_click)
            
    def refresh(self):
        # Fetch stats from db
        stats = get_dashboard_stats()
        
        # Update metric cards
        self.metric_cards['today_sales'].configure(text=f"₹{stats['today_sales']:.2f}")
        self.metric_cards['today_profit'].configure(text=f"₹{stats['today_profit']:.2f}")
        self.metric_cards['unpaid_total'].configure(text=f"₹{stats['unpaid_total']:.2f}")
        self.metric_cards['low_stock'].configure(text=str(stats['low_stock_count']))
        
    def update_clock(self):
        now_str = datetime.now().strftime("%A, %d %B %Y  |  %I:%M:%S %p")
        self.date_label.configure(text=now_str)
        self.after(1000, self.update_clock)
