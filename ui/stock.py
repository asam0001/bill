import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime, timedelta
from utils.medicine_service import (
    get_all_medicines, delete_medicine_batch, search_medicines, 
    update_medicine_batch, update_medicine_master, get_low_stock_medicines
)
from ui.theme import Theme
from ui.components import PageHeader, DataTable, PrimaryButton, SecondaryButton

class StockFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.configure(fg_color=Theme.BG_WINDOW)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        
        # 1. Header Area
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="Stock Inventory Management", font=ctk.CTkFont(size=24, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.title_label.pack(side="left")
        
        # Action Buttons in Header
        self.btn_purchase_list = SecondaryButton(self.header_frame, text="📋 Suggest Purchase List", width=160, command=self.generate_purchase_list)
        self.btn_purchase_list.pack(side="right", padx=(10, 0))
        
        # Search Bar
        self.search_entry = ctk.CTkEntry(self.header_frame, placeholder_text="Search stock by name or batch...", width=250)
        self.search_entry.pack(side="right", padx=(10, 0))
        self.search_entry.bind("<KeyRelease>", self.on_search)
        
        # 1.5. Segmented Filter Bar
        self.filter_var = ctk.StringVar(value="All Stock")
        self.filter_button = ctk.CTkSegmentedButton(self, values=["All Stock", "Low Stock", "Expiring Soon", "Expired"], variable=self.filter_var, command=self.on_filter_change, fg_color=Theme.BG_PANEL, selected_color=Theme.PRIMARY, selected_hover_color=Theme.PRIMARY)
        self.filter_button.grid(row=1, column=0, padx=20, pady=(5, 5), sticky="ew")
        
        # 2. Table Headers (Grid Layout Header)
        self.headers_frame = ctk.CTkFrame(self, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, border_width=1, height=35, corner_radius=5)
        self.headers_frame.grid(row=2, column=0, padx=20, pady=(5, 0), sticky="ew")
        self.headers_frame.grid_propagate(False)
        self.headers_frame.grid_rowconfigure(0, weight=1)
        
        headers = [
            ("Medicine Name", 0.20),
            ("Batch", 0.09),
            ("Expiry", 0.09),
            ("Strips / Stock", 0.15),
            ("Tab/Strip", 0.08),
            ("Total Tab", 0.08),
            ("Buy (₹)", 0.08),
            ("Sell (₹)", 0.08),
            ("MRP (₹)", 0.08),
            ("Action", 0.07)
        ]
        
        # Setup column layout widths using grid relative weights
        current_col = 0
        for text, weight in headers:
            col_weight = int(weight * 100)
            self.headers_frame.grid_columnconfigure(current_col, weight=col_weight)
            lbl = ctk.CTkLabel(self.headers_frame, text=text, font=ctk.CTkFont(size=11, weight="bold"), text_color="white")
            lbl.grid(row=0, column=current_col, padx=5, sticky="w" if current_col == 0 else "")
            current_col += 1
            
        # 3. Scrollable Stock List
        self.stock_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.stock_scroll.grid(row=3, column=0, padx=20, pady=(5, 15), sticky="nsew")
        self.stock_scroll.grid_columnconfigure(0, weight=1)
        
        self.all_stock = []
        
    def refresh(self):
        self.all_stock = get_all_medicines()
        self.search_entry.delete(0, "end")
        self.filter_var.set("All Stock")
        self.filter_button.set("All Stock")
        self.populate_stock_table(self.all_stock)
        
    def on_filter_change(self, value=None):
        if value is None:
            value = self.filter_var.get()
        filtered = self.all_stock
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        limit_soon = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        
        if value == "Low Stock":
            filtered = [med for med in self.all_stock if med['total_tablets'] < med['threshold']]
        elif value == "Expiring Soon":
            filtered = [med for med in self.all_stock if today_str <= med['expiry_date'] <= limit_soon]
        elif value == "Expired":
            filtered = [med for med in self.all_stock if med['expiry_date'] < today_str]
            
        # If there's search text, apply search filter on top of the segmented filter!
        search_text = self.search_entry.get().strip().lower()
        if search_text:
            filtered = [med for med in filtered if search_text in med['name'].lower() or search_text in med['batch'].lower()]
            
        self.populate_stock_table(filtered)
        
    def populate_stock_table(self, stock_list):
        # Clear existing rows
        for child in self.stock_scroll.winfo_children():
            child.destroy()
            
        if not stock_list:
            lbl_empty = ctk.CTkLabel(self.stock_scroll, text="No medicines in stock matching search criteria.", font=ctk.CTkFont(slant="italic"), text_color="gray50")
            lbl_empty.pack(pady=40)
            return
            
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")
        limit_soon = (today + timedelta(days=90)).strftime("%Y-%m-%d")
        
        for idx, med in enumerate(stock_list):
            # Check warning color coding
            exp_date = med['expiry_date']
            total_tabs = med['total_tablets']
            threshold = med['threshold']
            
            border_color = Theme.BORDER_COLOR
            border_width = 1
            row_bg = Theme.BG_WINDOW if idx % 2 == 0 else Theme.BG_PANEL
            
            # Identify critical state & pill badge styling
            badge_text = "🟢 Healthy"
            badge_fg = "#064E3B"
            badge_txt_color = "#A7F3D0"
            state_text_color = Theme.TEXT_MAIN
            
            if exp_date < today_str:
                badge_text = "🔴 Expired"
                badge_fg = "#7F1D1D"
                badge_txt_color = "#FCA5A5"
                border_color = Theme.DANGER
                state_text_color = Theme.DANGER
            elif exp_date <= limit_soon:
                badge_text = "⚠️ Expiring"
                badge_fg = "#78350F"
                badge_txt_color = "#FDE68A"
                border_color = Theme.WARNING
                state_text_color = Theme.WARNING
            elif total_tabs < threshold:
                badge_text = "🟡 Low Stock"
                badge_fg = "#713F12"
                badge_txt_color = "#FEF08A"
                border_color = Theme.SECONDARY
                state_text_color = Theme.WARNING
                
            # Create Row Frame
            row_frame = ctk.CTkFrame(
                self.stock_scroll, 
                fg_color=row_bg, 
                height=45, 
                corner_radius=5, 
                border_color=border_color, 
                border_width=border_width
            )
            row_frame.pack(fill="x", pady=3, padx=2)
            row_frame.grid_propagate(False)
            
            # Configure row column weights matching headers
            columns_weights = [20, 9, 9, 15, 8, 8, 8, 8, 8, 7]
            for col_idx, weight in enumerate(columns_weights):
                row_frame.grid_columnconfigure(col_idx, weight=weight)
                
            # Pack Columns
            # Name with status badge
            name_cell = ctk.CTkFrame(row_frame, fg_color="transparent")
            name_cell.grid(row=0, column=0, padx=8, sticky="ew")
            row_frame.grid_rowconfigure(0, weight=1)
            name_cell.grid_rowconfigure(0, weight=1)
            
            lbl_name = ctk.CTkLabel(name_cell, text=med['name'], font=ctk.CTkFont(size=12, weight="bold"), text_color=state_text_color, anchor="w")
            lbl_name.pack(side="left", fill="x", expand=True)
            
            lbl_badge = ctk.CTkLabel(name_cell, text=badge_text, font=ctk.CTkFont(size=9, weight="bold"), fg_color=badge_fg, text_color=badge_txt_color, corner_radius=8, height=18)
            lbl_badge.pack(side="right", padx=(5, 0))
            
            # Batch
            lbl_batch = ctk.CTkLabel(row_frame, text=med['batch'], font=ctk.CTkFont(size=11), text_color=Theme.TEXT_LIGHT)
            lbl_batch.grid(row=0, column=1, padx=5, sticky="")
            
            # Expiry
            lbl_exp = ctk.CTkLabel(row_frame, text=med['expiry_date'], font=ctk.CTkFont(size=11), text_color=state_text_color)
            lbl_exp.grid(row=0, column=2, padx=5, sticky="")
            
            # Strips Details String
            lbl_strips = ctk.CTkLabel(row_frame, text=med['stock_string'], font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_MAIN)
            lbl_strips.grid(row=0, column=3, padx=5, sticky="")
            
            # Tablets per strip
            lbl_tps = ctk.CTkLabel(row_frame, text=str(med['tablets_per_strip']), font=ctk.CTkFont(size=11), text_color=Theme.TEXT_LIGHT)
            lbl_tps.grid(row=0, column=4, padx=5, sticky="")
            
            # Total tablets
            lbl_tot = ctk.CTkLabel(row_frame, text=str(med['total_tablets']), font=ctk.CTkFont(size=11, weight="bold"), text_color=state_text_color)
            lbl_tot.grid(row=0, column=5, padx=5, sticky="")
            
            # Buy Price
            lbl_buy = ctk.CTkLabel(row_frame, text=f"₹{med['purchase_price']:.2f}", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_LIGHT)
            lbl_buy.grid(row=0, column=6, padx=5, sticky="")
            
            # Sell Price
            lbl_sell = ctk.CTkLabel(row_frame, text=f"₹{med['selling_price']:.2f}", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_LIGHT)
            lbl_sell.grid(row=0, column=7, padx=5, sticky="")
            
            # MRP
            lbl_mrp = ctk.CTkLabel(row_frame, text=f"₹{med['mrp']:.2f}", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_LIGHT)
            lbl_mrp.grid(row=0, column=8, padx=5, sticky="")
            
            # Action frame for Edit and Delete
            act_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            act_frame.grid(row=0, column=9, sticky="")
            
            btn_edit = ctk.CTkButton(
                act_frame, 
                text="✏️", 
                width=24, 
                height=24, 
                fg_color=Theme.SECONDARY, 
                hover_color=Theme.SECONDARY_HOVER,
                command=lambda m=med: self.open_edit_stock_modal(m)
            )
            btn_edit.pack(side="left", padx=2)
            
            btn_del = ctk.CTkButton(
                act_frame, 
                text="🗑️", 
                width=24, 
                height=24, 
                fg_color=Theme.DANGER, 
                hover_color=Theme.DANGER_HOVER,
                command=lambda m=med: self.confirm_delete_stock(m)
            )
            btn_del.pack(side="left", padx=2)
            
            row_frame.grid_rowconfigure(0, weight=1)

    def on_search(self, event=None):
        query = self.search_entry.get().strip()
        if not query:
            self.populate_stock_table(self.all_stock)
            return
            
        filtered = search_medicines(query)
        self.populate_stock_table(filtered)
        
    def confirm_delete_stock(self, med):
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete batch '{med['batch']}' of '{med['name']}'?")
        if confirm:
            try:
                delete_medicine_batch(med['id'])
                messagebox.showinfo("Success", "Medicine batch deleted successfully.")
                self.refresh()
            except Exception as ex:
                messagebox.showerror("Error", str(ex))
                
    def open_edit_stock_modal(self, med):
        # Modal config
        modal = ctk.CTkToplevel(self)
        modal.title("Edit Stock Item")
        modal.geometry("380x420")
        modal.grab_set()
        modal.resizable(False, False)
        
        modal.grid_columnconfigure(0, weight=1)
        
        title = ctk.CTkLabel(modal, text=f"Edit: {med['name']}", font=ctk.CTkFont(size=16, weight="bold"), text_color=Theme.PRIMARY)
        title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        lbl_batch = ctk.CTkLabel(modal, text=f"Batch: {med['batch']}  |  Expiry: {med['expiry_date']}", font=ctk.CTkFont(size=12, slant="italic"), text_color=Theme.TEXT_MUTED)
        lbl_batch.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")
        
        # Form fields
        lbl_sp = ctk.CTkLabel(modal, text="Selling Price (per Strip) *", font=ctk.CTkFont(size=11, weight="bold"))
        lbl_sp.grid(row=2, column=0, padx=20, pady=(5, 2), sticky="w")
        entry_sp = ctk.CTkEntry(modal)
        entry_sp.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")
        entry_sp.insert(0, str(med['selling_price']))
        
        lbl_mrp = ctk.CTkLabel(modal, text="MRP (per Strip) *", font=ctk.CTkFont(size=11, weight="bold"))
        lbl_mrp.grid(row=4, column=0, padx=20, pady=(5, 2), sticky="w")
        entry_mrp = ctk.CTkEntry(modal)
        entry_mrp.grid(row=5, column=0, padx=20, pady=(0, 10), sticky="ew")
        entry_mrp.insert(0, str(med['mrp']))
        
        lbl_th = ctk.CTkLabel(modal, text="Low Stock Alert Threshold (Tablets) *", font=ctk.CTkFont(size=11, weight="bold"))
        lbl_th.grid(row=6, column=0, padx=20, pady=(5, 2), sticky="w")
        entry_th = ctk.CTkEntry(modal)
        entry_th.grid(row=7, column=0, padx=20, pady=(0, 15), sticky="ew")
        entry_th.insert(0, str(med['threshold']))
        
        btn_row = ctk.CTkFrame(modal, fg_color="transparent")
        btn_row.grid(row=8, column=0, padx=20, pady=10, sticky="ew")
        btn_row.grid_columnconfigure((0, 1), weight=1)
        
        def save_changes():
            try:
                new_sp = float(entry_sp.get().strip())
                new_mrp = float(entry_mrp.get().strip())
                new_th = int(entry_th.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numeric values.", parent=modal)
                return
                
            if new_sp < 0 or new_mrp < 0 or new_th < 0:
                messagebox.showerror("Error", "Values cannot be negative.", parent=modal)
                return
                
            if new_sp > new_mrp:
                messagebox.showerror("Error", "Selling Price cannot exceed MRP.", parent=modal)
                return
                
            try:
                # 1. Update batch details
                update_medicine_batch(
                    batch_id=med['id'],
                    batch_number=med['batch_number'],
                    expiry_date=med['expiry_date'],
                    purchase_price=med['purchase_price'],
                    selling_price=new_sp,
                    mrp=new_mrp,
                    tablets_per_strip=med['tablets_per_strip'],
                    quantity=med['quantity'],
                    free_quantity=med['free_quantity'],
                    discount=med['discount'],
                    gst=med['gst'],
                    supplier_id=med['supplier_id'],
                    purchase_invoice=med['purchase_invoice'],
                    purchase_date=med['purchase_date']
                )
                # 2. Update medicine master details
                update_medicine_master(
                    medicine_id=med['medicine_id'],
                    name=med['name'],
                    manufacturer=med['manufacturer'],
                    generic_name=med['generic_name'],
                    brand=med['brand'],
                    category=med['category'],
                    dosage_form=med['dosage_form'],
                    strength=med['strength'],
                    pack_size=med['pack_size'],
                    unit=med['unit'],
                    hsn_code=med['hsn_code'],
                    gst_rate=med['gst_rate'],
                    prescription_required=med['prescription_required'],
                    reorder_level=new_th,
                    minimum_stock=med['minimum_stock'],
                    maximum_stock=med['maximum_stock'],
                    rack_shelf=med['rack_shelf'],
                    status=med['status']
                )
                messagebox.showinfo("Success", "Stock information updated successfully.", parent=modal)
                modal.destroy()
                self.refresh()
            except Exception as ex:
                messagebox.showerror("Error", str(ex), parent=modal)
                
        btn_save = PrimaryButton(btn_row, text="💾 Save Changes", command=save_changes)
        btn_save.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        btn_cancel = ctk.CTkButton(btn_row, text="❌ Cancel", fg_color="#5D6D7E", hover_color="#4D5656", command=modal.destroy)
        btn_cancel.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    def generate_purchase_list(self):
        # Open purchase generator view
        modal = ctk.CTkToplevel(self)
        modal.title("Suggested Purchase List (Reorder)")
        modal.geometry("700x500")
        modal.grab_set()
        
        modal.grid_columnconfigure(0, weight=1)
        modal.grid_rowconfigure(2, weight=1)
        
        header = ctk.CTkLabel(modal, text="📋 Suggested Restock & Purchase List", font=ctk.CTkFont(size=18, weight="bold"), text_color=Theme.PRIMARY)
        header.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        subheader = ctk.CTkLabel(modal, text="Based on active medicines currently falling below set reorder levels.", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED)
        subheader.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")
        
        # Reorder list data table
        table_frame = ctk.CTkFrame(modal, fg_color="transparent")
        table_frame.grid(row=2, column=0, padx=20, pady=5, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(1, weight=1)
        
        # Headers
        headers_bar = ctk.CTkFrame(table_frame, fg_color=Theme.BG_PANEL, height=35, corner_radius=5)
        headers_bar.grid(row=0, column=0, sticky="ew")
        headers_bar.grid_propagate(False)
        headers_bar.grid_rowconfigure(0, weight=1)
        
        widths = [0.4, 0.15, 0.15, 0.15, 0.15]
        cols = ["Medicine Name", "Current Stock", "Reorder Level", "Max Limit", "Suggest Qty"]
        for idx, (c_name, w) in enumerate(zip(cols, widths)):
            headers_bar.grid_columnconfigure(idx, weight=int(w * 100))
            lbl = ctk.CTkLabel(headers_bar, text=c_name, font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
            lbl.grid(row=0, column=idx, padx=10, sticky="w" if idx == 0 else "")
            
        # Data scroll
        scroll = ctk.CTkScrollableFrame(table_frame, fg_color="transparent")
        scroll.grid(row=1, column=0, pady=(5, 10), sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        
        low_items = get_low_stock_medicines()
        
        if not low_items:
            lbl_no = ctk.CTkLabel(scroll, text="All medicine stocks are currently healthy (above reorder thresholds).", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
            lbl_no.pack(pady=50)
        else:
            for idx, item in enumerate(low_items):
                bg = Theme.BG_WINDOW if idx % 2 == 0 else Theme.BG_PANEL
                r_frame = ctk.CTkFrame(scroll, fg_color=bg, height=40, corner_radius=4)
                r_frame.pack(fill="x", pady=2)
                r_frame.grid_propagate(False)
                r_frame.grid_rowconfigure(0, weight=1)
                
                # Math for suggested order: max_stock - current_stock
                suggested_restock = max(0, item['maximum_stock'] - item['total_tablets'])
                
                vals = [
                    item['name'], 
                    f"{item['total_tablets']} tab", 
                    f"{item['reorder_level']} tab", 
                    f"{item['maximum_stock']} tab", 
                    f"{suggested_restock} tab"
                ]
                
                for c_idx, (val, w) in enumerate(zip(vals, widths)):
                    r_frame.grid_columnconfigure(c_idx, weight=int(w * 100))
                    lbl = ctk.CTkLabel(r_frame, text=str(val), font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MAIN if c_idx != 4 else Theme.SUCCESS, anchor="w" if c_idx == 0 else "center")
                    lbl.grid(row=0, column=c_idx, padx=10, sticky="ew" if c_idx == 0 else "")
                    
        # Footer Action close
        btn_close = ctk.CTkButton(modal, text="Close List", command=modal.destroy)
        btn_close.grid(row=3, column=0, padx=20, pady=20)
