import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime, timedelta
from utils.supplier_service import get_all_suppliers
from utils.purchase_service import record_purchase
from ui.theme import Theme
from ui.components import PrimaryButton, SecondaryButton, DangerButton

class PurchasesFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(fg_color=Theme.BG_WINDOW)
        
        # Grid layout: 2 columns
        # Left (Main): Invoice detail & Item additions & Current items list table
        # Right (Sidebar): Subtotals summary & Complete save buttons
        self.grid_columnconfigure(0, weight=3) # 75% width
        self.grid_columnconfigure(1, weight=1) # 25% width
        self.grid_rowconfigure(0, weight=1)
        
        self.items_cart = []
        self.suppliers = []
        self.supplier_mapping = {}
        
        # --- LEFT PANEL ---
        self.left_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.left_panel.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="nsew")
        self.left_panel.grid_columnconfigure(0, weight=1)
        self.left_panel.grid_rowconfigure(2, weight=1) # Table expands
        
        # Title
        self.title_lbl = ctk.CTkLabel(self.left_panel, text="📥 Record Purchase Invoice", font=ctk.CTkFont(size=22, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.title_lbl.grid(row=0, column=0, pady=(0, 10), sticky="w")
        
        # 1. Invoice Header details frame
        self.inv_header_frame = ctk.CTkFrame(self.left_panel, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=8)
        self.inv_header_frame.grid(row=1, column=0, pady=(0, 10), sticky="ew")
        
        # Grid inside header details (2 rows, 3 columns)
        for col_i in range(3):
            self.inv_header_frame.grid_columnconfigure(col_i, weight=1)
            
        lbl_inv = ctk.CTkLabel(self.inv_header_frame, text="Invoice No *", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_inv.grid(row=0, column=0, padx=15, pady=(8, 1), sticky="w")
        self.entry_invoice_num = ctk.CTkEntry(self.inv_header_frame, placeholder_text="e.g. PI-9908", fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.entry_invoice_num.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="ew")
        
        lbl_sup = ctk.CTkLabel(self.inv_header_frame, text="Supplier *", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_sup.grid(row=0, column=1, padx=15, pady=(8, 1), sticky="w")
        self.combo_supplier = ctk.CTkComboBox(self.inv_header_frame, values=["Select Supplier"], fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR, dropdown_fg_color=Theme.BG_PANEL, dropdown_text_color=Theme.TEXT_MAIN)
        self.combo_supplier.grid(row=1, column=1, padx=15, pady=(0, 10), sticky="ew")
        
        lbl_status = ctk.CTkLabel(self.inv_header_frame, text="Payment Status *", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_status.grid(row=0, column=2, padx=15, pady=(8, 1), sticky="w")
        self.combo_pay_status = ctk.CTkComboBox(self.inv_header_frame, values=["Unpaid", "Paid"], fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.combo_pay_status.grid(row=1, column=2, padx=15, pady=(0, 10), sticky="ew")
        self.combo_pay_status.set("Unpaid")
        
        # 2. Item Entry sub-form frame
        self.item_entry_frame = ctk.CTkFrame(self.left_panel, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=8)
        self.item_entry_frame.grid(row=2, column=0, pady=(0, 10), sticky="nsew")
        self.item_entry_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        # Entry row inputs layout
        lbl_med = ctk.CTkLabel(self.item_entry_frame, text="Medicine Name *", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_med.grid(row=0, column=0, padx=10, pady=(8, 1), sticky="w")
        self.entry_med_name = ctk.CTkEntry(self.item_entry_frame, placeholder_text="e.g. Paracetamol", fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.entry_med_name.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
        
        lbl_man = ctk.CTkLabel(self.item_entry_frame, text="Manufacturer", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_man.grid(row=0, column=1, padx=10, pady=(8, 1), sticky="w")
        self.entry_manufacturer = ctk.CTkEntry(self.item_entry_frame, placeholder_text="e.g. Abbott", fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.entry_manufacturer.grid(row=1, column=1, padx=10, pady=(0, 5), sticky="ew")
        
        lbl_batch = ctk.CTkLabel(self.item_entry_frame, text="Batch *", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_batch.grid(row=0, column=2, padx=10, pady=(8, 1), sticky="w")
        self.entry_batch = ctk.CTkEntry(self.item_entry_frame, placeholder_text="B-102", fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.entry_batch.grid(row=1, column=2, padx=10, pady=(0, 5), sticky="ew")
        
        lbl_exp = ctk.CTkLabel(self.item_entry_frame, text="Expiry (YYYY-MM-DD) *", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_exp.grid(row=0, column=3, padx=10, pady=(8, 1), sticky="w")
        self.entry_expiry = ctk.CTkEntry(self.item_entry_frame, placeholder_text="2027-12-31", fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.entry_expiry.grid(row=1, column=3, padx=10, pady=(0, 5), sticky="ew")
        
        # Entry row 2 inputs layout
        lbl_tps = ctk.CTkLabel(self.item_entry_frame, text="Tabs/Strip *", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_tps.grid(row=2, column=0, padx=10, pady=(5, 1), sticky="w")
        self.entry_tps = ctk.CTkEntry(self.item_entry_frame, placeholder_text="10", fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.entry_tps.grid(row=3, column=0, padx=10, pady=(0, 5), sticky="ew")
        self.entry_tps.insert(0, "10")
        
        lbl_sq = ctk.CTkLabel(self.item_entry_frame, text="Strips Qty *", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_sq.grid(row=2, column=1, padx=10, pady=(5, 1), sticky="w")
        self.entry_strips = ctk.CTkEntry(self.item_entry_frame, placeholder_text="10", fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.entry_strips.grid(row=3, column=1, padx=10, pady=(0, 5), sticky="ew")
        
        lbl_free = ctk.CTkLabel(self.item_entry_frame, text="Free Strips", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_free.grid(row=2, column=2, padx=10, pady=(5, 1), sticky="w")
        self.entry_free = ctk.CTkEntry(self.item_entry_frame, placeholder_text="0", fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.entry_free.grid(row=3, column=2, padx=10, pady=(0, 5), sticky="ew")
        self.entry_free.insert(0, "0")
        
        lbl_rate = ctk.CTkLabel(self.item_entry_frame, text="Buy Rate/Strip *", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_rate.grid(row=2, column=3, padx=10, pady=(5, 1), sticky="w")
        self.entry_rate = ctk.CTkEntry(self.item_entry_frame, placeholder_text="0.00", fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.entry_rate.grid(row=3, column=3, padx=10, pady=(0, 5), sticky="ew")
        
        # Entry row 3 inputs layout
        lbl_sell = ctk.CTkLabel(self.item_entry_frame, text="Sell Rate/Strip *", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_sell.grid(row=4, column=0, padx=10, pady=(5, 1), sticky="w")
        self.entry_sell = ctk.CTkEntry(self.item_entry_frame, placeholder_text="0.00", fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.entry_sell.grid(row=5, column=0, padx=10, pady=(0, 5), sticky="ew")
        
        lbl_mrp = ctk.CTkLabel(self.item_entry_frame, text="MRP/Strip *", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_mrp.grid(row=4, column=1, padx=10, pady=(5, 1), sticky="w")
        self.entry_mrp = ctk.CTkEntry(self.item_entry_frame, placeholder_text="0.00", fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.entry_mrp.grid(row=5, column=1, padx=10, pady=(0, 5), sticky="ew")
        
        lbl_disc = ctk.CTkLabel(self.item_entry_frame, text="Discount (%)", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_disc.grid(row=4, column=2, padx=10, pady=(5, 1), sticky="w")
        self.entry_discount = ctk.CTkEntry(self.item_entry_frame, placeholder_text="0.00", fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.entry_discount.grid(row=5, column=2, padx=10, pady=(0, 5), sticky="ew")
        self.entry_discount.insert(0, "0.00")
        
        lbl_gst = ctk.CTkLabel(self.item_entry_frame, text="GST Rate (%)", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_gst.grid(row=4, column=3, padx=10, pady=(5, 1), sticky="w")
        self.entry_gst = ctk.CTkEntry(self.item_entry_frame, placeholder_text="12.00", fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.entry_gst.grid(row=5, column=3, padx=10, pady=(0, 5), sticky="ew")
        self.entry_gst.insert(0, "12.00")
        
        # Add item button
        self.btn_add_item = SecondaryButton(self.item_entry_frame, text="➕ Add Item to List", command=self.add_item_to_cart)
        self.btn_add_item.grid(row=6, column=0, columnspan=4, padx=10, pady=10, sticky="ew")
        
        # 3. Cart Grid List table
        self.items_table_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.items_table_frame.grid(row=3, column=0, pady=(5, 0), sticky="nsew")
        self.left_panel.grid_rowconfigure(3, weight=2) # Cart grid table takes rest of expand space
        self.items_table_frame.grid_columnconfigure(0, weight=1)
        self.items_table_frame.grid_rowconfigure(1, weight=1)
        
        # Table Header
        self.table_header = ctk.CTkFrame(self.items_table_frame, fg_color=Theme.BG_PANEL, height=30, corner_radius=4)
        self.table_header.grid(row=0, column=0, sticky="ew")
        self.table_header.grid_propagate(False)
        self.table_header.grid_rowconfigure(0, weight=1)
        
        self.tbl_widths = [0.25, 0.12, 0.12, 0.10, 0.10, 0.10, 0.13, 0.08]
        cols = ["Medicine Name", "Batch", "Expiry", "Qty", "Free", "Rate", "Total Value", "Action"]
        for idx, (h_name, weight) in enumerate(zip(cols, self.tbl_widths)):
            self.table_header.grid_columnconfigure(idx, weight=int(weight * 100))
            lbl = ctk.CTkLabel(self.table_header, text=h_name, font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
            lbl.grid(row=0, column=idx, padx=5, sticky="w" if idx == 0 else "")
            
        # Table Scroll rows
        self.items_scroll = ctk.CTkScrollableFrame(self.items_table_frame, fg_color="transparent")
        self.items_scroll.grid(row=1, column=0, sticky="nsew")
        self.items_scroll.grid_columnconfigure(0, weight=1)
        
        # --- RIGHT SUMMARY PANEL ---
        self.right_panel = ctk.CTkFrame(self, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=10)
        self.right_panel.grid(row=0, column=1, padx=(10, 15), pady=15, sticky="nsew")
        self.right_panel.grid_columnconfigure(0, weight=1)
        
        self.summary_title = ctk.CTkLabel(self.right_panel, text="Summary & Totals", font=ctk.CTkFont(size=18, weight="bold"), text_color=Theme.PRIMARY)
        self.summary_title.pack(anchor="w", padx=20, pady=(20, 15))
        
        # Financial metric breakdown block
        self.metrics_container = ctk.CTkFrame(self.right_panel, fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=8)
        self.metrics_container.pack(fill="x", padx=20, pady=10)
        self.metrics_container.grid_columnconfigure((0, 1), weight=1)
        
        # Taxable Value
        lbl_tax = ctk.CTkLabel(self.metrics_container, text="Taxable Value:", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_LIGHT)
        lbl_tax.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        self.val_taxable = ctk.CTkLabel(self.metrics_container, text="₹0.00", font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.val_taxable.grid(row=0, column=1, padx=15, pady=(15, 5), sticky="e")
        
        # GST Amount
        lbl_gst = ctk.CTkLabel(self.metrics_container, text="GST Tax Amount:", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_LIGHT)
        lbl_gst.grid(row=1, column=0, padx=15, pady=5, sticky="w")
        self.val_gst = ctk.CTkLabel(self.metrics_container, text="₹0.00", font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.val_gst.grid(row=1, column=1, padx=15, pady=5, sticky="e")
        
        # Discount Amount
        lbl_disc = ctk.CTkLabel(self.metrics_container, text="Discount Received:", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_LIGHT)
        lbl_disc.grid(row=2, column=0, padx=15, pady=5, sticky="w")
        self.val_discount = ctk.CTkLabel(self.metrics_container, text="₹0.00", font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.val_discount.grid(row=2, column=1, padx=15, pady=5, sticky="e")
        
        # Grand Total
        lbl_grand = ctk.CTkLabel(self.metrics_container, text="Grand Total:", font=ctk.CTkFont(size=14, weight="bold"), text_color=Theme.SUCCESS)
        lbl_grand.grid(row=3, column=0, padx=15, pady=(10, 15), sticky="w")
        self.val_grand_total = ctk.CTkLabel(self.metrics_container, text="₹0.00", font=ctk.CTkFont(size=16, weight="bold"), text_color=Theme.SUCCESS)
        self.val_grand_total.grid(row=3, column=1, padx=15, pady=(10, 15), sticky="e")
        
        # Action Save
        self.btn_save_invoice = PrimaryButton(self.right_panel, text="🔒 Save & Submit Invoice", height=45, command=self.save_invoice)
        self.btn_save_invoice.pack(fill="x", padx=20, pady=20)
        
        # Action Clear
        self.btn_clear_invoice = ctk.CTkButton(self.right_panel, text="🧹 Reset Form", fg_color=Theme.BORDER_COLOR, hover_color=Theme.BG_WINDOW, text_color=Theme.TEXT_LIGHT, command=self.reset_all)
        self.btn_clear_invoice.pack(fill="x", padx=20, pady=(0, 20))
        
    def refresh(self):
        # Load suppliers list
        self.suppliers = get_all_suppliers()
        self.supplier_mapping = {s['name']: s['id'] for s in self.suppliers}
        options = ["Select Supplier"] + list(self.supplier_mapping.keys())
        self.combo_supplier.configure(values=options)
        self.combo_supplier.set("Select Supplier")
        
        self.reset_all()
        
    def reset_all(self):
        self.items_cart.clear()
        self.entry_invoice_num.delete(0, "end")
        self.combo_supplier.set("Select Supplier")
        self.combo_pay_status.set("Unpaid")
        self.clear_item_inputs()
        self.populate_items_table()
        self.recalculate_invoice_totals()
        
    def clear_item_inputs(self):
        self.entry_med_name.delete(0, "end")
        self.entry_manufacturer.delete(0, "end")
        self.entry_batch.delete(0, "end")
        self.entry_expiry.delete(0, "end")
        self.entry_strips.delete(0, "end")
        self.entry_rate.delete(0, "end")
        self.entry_sell.delete(0, "end")
        self.entry_mrp.delete(0, "end")
        
        # Defaults
        self.entry_tps.delete(0, "end")
        self.entry_tps.insert(0, "10")
        self.entry_free.delete(0, "end")
        self.entry_free.insert(0, "0")
        self.entry_discount.delete(0, "end")
        self.entry_discount.insert(0, "0.00")
        self.entry_gst.delete(0, "end")
        self.entry_gst.insert(0, "12.00")
        
    def add_item_to_cart(self):
        name = self.entry_med_name.get().strip()
        man = self.entry_manufacturer.get().strip()
        batch = self.entry_batch.get().strip()
        expiry = self.entry_expiry.get().strip()
        
        try:
            tps = int(self.entry_tps.get())
            strips = int(self.entry_strips.get())
            free = int(self.entry_free.get() or 0)
            rate = float(self.entry_rate.get())
            sell = float(self.entry_sell.get())
            mrp = float(self.entry_mrp.get())
            disc = float(self.entry_discount.get() or 0.0)
            gst = float(self.entry_gst.get() or 12.0)
        except ValueError:
            messagebox.showerror("Item Error", "Numeric input error. Please verify Quantity, Rate, MRP etc.")
            return
            
        if not name or not batch or not expiry:
            messagebox.showerror("Item Error", "Medicine name, batch number, and expiry date are required.")
            return
            
        try:
            datetime.strptime(expiry, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Item Error", "Expiry date must be in YYYY-MM-DD format.")
            return
            
        if rate < 0 or sell < 0 or mrp < 0 or strips <= 0 or tps <= 0:
            messagebox.showerror("Item Error", "Values cannot be negative, quantities must be greater than 0.")
            return
            
        if sell > mrp:
            messagebox.showerror("Item Error", "Selling Price cannot exceed MRP.")
            return
            
        # Add to cart
        # (store quantity in tablets, free in tablets)
        item_data = {
            'name': name,
            'manufacturer': man,
            'batch_number': batch,
            'expiry_date': expiry,
            'quantity': strips * tps,
            'free_quantity': free * tps,
            'purchase_price': rate,
            'selling_price': sell,
            'mrp': mrp,
            'discount_percent': disc,
            'gst_percent': gst,
            'tablets_per_strip': tps,
            'strips_purchased': strips,
            'free_strips': free
        }
        
        self.items_cart.append(item_data)
        self.clear_item_inputs()
        self.populate_items_table()
        self.recalculate_invoice_totals()
        
    def populate_items_table(self):
        for child in self.items_scroll.winfo_children():
            child.destroy()
            
        if not self.items_cart:
            lbl = ctk.CTkLabel(self.items_scroll, text="No items added to this purchase invoice yet.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
            lbl.pack(pady=30)
            return
            
        for idx, item in enumerate(self.items_cart):
            bg = Theme.BG_WINDOW if idx % 2 == 0 else Theme.BG_PANEL
            row_frame = ctk.CTkFrame(self.items_scroll, fg_color=bg, height=35, corner_radius=3)
            row_frame.pack(fill="x", pady=1)
            row_frame.grid_propagate(False)
            row_frame.grid_rowconfigure(0, weight=1)
            
            # Math
            subtotal_cost = item['strips_purchased'] * item['purchase_price'] * (1 - item['discount_percent'] / 100.0)
            with_tax = subtotal_cost * (1 + item['gst_percent'] / 100.0)
            
            vals = [
                item['name'],
                item['batch_number'],
                item['expiry_date'],
                f"{item['strips_purchased']} str",
                f"{item['free_strips']} str",
                f"₹{item['purchase_price']:.2f}",
                f"₹{with_tax:.2f}"
            ]
            
            for c_idx, (v, weight) in enumerate(zip(vals, self.tbl_widths)):
                row_frame.grid_columnconfigure(c_idx, weight=int(weight * 100))
                lbl = ctk.CTkLabel(row_frame, text=v, font=ctk.CTkFont(size=10), text_color=Theme.TEXT_MAIN, anchor="w" if c_idx == 0 else "center")
                lbl.grid(row=0, column=c_idx, padx=5, sticky="ew" if c_idx == 0 else "")
                
            # Delete btn column
            row_frame.grid_columnconfigure(7, weight=int(self.tbl_widths[7] * 100))
            btn_del = ctk.CTkButton(
                row_frame, 
                text="🗑️", 
                width=24, 
                height=22, 
                fg_color=Theme.DANGER, 
                hover_color=Theme.DANGER_HOVER,
                command=lambda pos=idx: self.remove_item_from_cart(pos)
            )
            btn_del.grid(row=0, column=7, sticky="")
            
    def remove_item_from_cart(self, pos):
        self.items_cart.pop(pos)
        self.populate_items_table()
        self.recalculate_invoice_totals()
        
    def recalculate_invoice_totals(self):
        taxable_sum = 0.0
        gst_sum = 0.0
        disc_sum = 0.0
        grand_total = 0.0
        
        for item in self.items_cart:
            gross = item['strips_purchased'] * item['purchase_price']
            disc = gross * (item['discount_percent'] / 100.0)
            taxable = gross - disc
            gst = taxable * (item['gst_percent'] / 100.0)
            total = taxable + gst
            
            taxable_sum += taxable
            gst_sum += gst
            disc_sum += disc
            grand_total += total
            
        self.val_taxable.configure(text=f"₹{taxable_sum:.2f}")
        self.val_gst.configure(text=f"₹{gst_sum:.2f}")
        self.val_discount.configure(text=f"₹{disc_sum:.2f}")
        self.val_grand_total.configure(text=f"₹{grand_total:.2f}")
        
        self.calculated_taxable = taxable_sum
        self.calculated_gst = gst_sum
        self.calculated_disc = disc_sum
        self.calculated_grand = grand_total
        
    def save_invoice(self):
        invoice_num = self.entry_invoice_num.get().strip()
        supplier_name = self.combo_supplier.get()
        pay_status = self.combo_pay_status.get()
        
        if not invoice_num:
            messagebox.showerror("Invoice Error", "Invoice Number is required.")
            return
            
        if supplier_name == "Select Supplier" or supplier_name not in self.supplier_mapping:
            messagebox.showerror("Invoice Error", "Please select a valid supplier.")
            return
            
        if not self.items_cart:
            messagebox.showerror("Invoice Error", "The itemized invoice list is empty.")
            return
            
        supplier_id = self.supplier_mapping[supplier_name]
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save invoice to database
        try:
            record_purchase(
                purchase_invoice_number=invoice_num,
                supplier_id=supplier_id,
                purchase_date=date_str,
                due_date=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                payment_status=pay_status,
                total_amount=self.calculated_taxable,
                discount_percent=0.0, # individual discount is computed per item
                gst_amount=self.calculated_gst,
                grand_total=self.calculated_grand,
                items=self.items_cart
            )
            messagebox.showinfo("Success", f"Purchase Invoice #{invoice_num} successfully saved to DB. Stock and ledger balances updated.")
            self.reset_all()
        except Exception as ex:
            messagebox.showerror("Database Transaction Error", str(ex))
