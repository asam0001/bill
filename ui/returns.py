import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from utils.sales_service import get_bill_by_number, get_bill_items, record_sales_return
from utils.supplier_service import get_all_suppliers
from utils.medicine_service import get_all_medicines, search_medicines
from utils.purchase_service import record_purchase_return
from ui.theme import Theme
from ui.components import PrimaryButton, SecondaryButton

class ReturnsFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(fg_color=Theme.BG_WINDOW)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 1. Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="ew")
        
        self.title_lbl = ctk.CTkLabel(self.header_frame, text="🔄 Sales & Purchase Returns Manager", font=ctk.CTkFont(size=22, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.title_lbl.pack(side="left")
        
        # 2. Tabview
        self.tabview = ctk.CTkTabview(self, fg_color=Theme.BG_PANEL, segmented_button_selected_color=Theme.PRIMARY, segmented_button_selected_hover_color=Theme.PRIMARY_HOVER)
        self.tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        self.tab_sales = self.tabview.add("Sales / Customer Returns")
        self.tab_purchase = self.tabview.add("Purchase / Supplier Returns")
        
        self.setup_sales_returns_tab()
        self.setup_purchase_returns_tab()
        
    def setup_sales_returns_tab(self):
        # 2 columns layout inside Sales Returns
        self.tab_sales.grid_columnconfigure(0, weight=3) # Original Bill items
        self.tab_sales.grid_columnconfigure(1, weight=2) # Returned cart
        self.tab_sales.grid_rowconfigure(1, weight=1)
        
        # Top bill search row
        search_row = ctk.CTkFrame(self.tab_sales, fg_color="transparent")
        search_row.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        
        lbl = ctk.CTkLabel(search_row, text="Enter Bill Number:", font=ctk.CTkFont(size=12, weight="bold"))
        lbl.pack(side="left", padx=5)
        self.entry_bill_num = ctk.CTkEntry(search_row, placeholder_text="e.g. MT-2026-000001", width=220)
        self.entry_bill_num.pack(side="left", padx=5)
        
        btn_find = SecondaryButton(search_row, text="🔍 Retrieve Bill Items", command=self.retrieve_bill)
        btn_find.pack(side="left", padx=5)
        
        # Left Panel (Original Items table)
        left_p = ctk.CTkFrame(self.tab_sales, fg_color="transparent")
        left_p.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        left_p.grid_columnconfigure(0, weight=1)
        left_p.grid_rowconfigure(1, weight=1)
        
        lbl_orig = ctk.CTkLabel(left_p, text="Original Invoice Items", font=ctk.CTkFont(size=13, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_orig.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        # Table Header
        orig_header = ctk.CTkFrame(left_p, fg_color=Theme.BG_PANEL, height=30, corner_radius=3)
        orig_header.grid(row=1, column=0, sticky="ew")
        orig_header.grid_propagate(False)
        orig_header.grid_rowconfigure(0, weight=1)
        
        self.orig_w = [0.4, 0.15, 0.15, 0.15, 0.15]
        cols = ["Medicine Name", "Batch", "Billed Qty", "Rate", "Action"]
        for idx, (c_name, weight) in enumerate(zip(cols, self.orig_w)):
            orig_header.grid_columnconfigure(idx, weight=int(weight * 100))
            lbl = ctk.CTkLabel(orig_header, text=c_name, font=ctk.CTkFont(size=10, weight="bold"), text_color=Theme.TEXT_LIGHT)
            lbl.grid(row=0, column=idx, padx=5, sticky="w" if idx == 0 else "")
            
        # Table Scroll
        self.orig_scroll = ctk.CTkScrollableFrame(left_p, fg_color="transparent")
        self.orig_scroll.grid(row=2, column=0, sticky="nsew")
        left_p.grid_rowconfigure(2, weight=1)
        self.orig_scroll.grid_columnconfigure(0, weight=1)
        
        # Right Panel (Return items cart)
        right_p = ctk.CTkFrame(self.tab_sales, fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=8)
        right_p.grid(row=1, column=1, padx=10, pady=5, sticky="nsew")
        right_p.grid_columnconfigure(0, weight=1)
        right_p.grid_rowconfigure(1, weight=1)
        
        lbl_ret = ctk.CTkLabel(right_p, text="Returned Items List", font=ctk.CTkFont(size=13, weight="bold"), text_color=Theme.PRIMARY)
        lbl_ret.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        
        # Scroll container
        self.ret_scroll = ctk.CTkScrollableFrame(right_p, fg_color="transparent")
        self.ret_scroll.grid(row=1, column=0, padx=15, sticky="nsew")
        self.ret_scroll.grid_columnconfigure(0, weight=1)
        
        # Summary & submit return
        summary_f = ctk.CTkFrame(right_p, fg_color="transparent")
        summary_f.grid(row=2, column=0, padx=15, pady=15, sticky="ew")
        summary_f.grid_columnconfigure((0, 1), weight=1)
        
        lbl_tot = ctk.CTkLabel(summary_f, text="Refund Total:", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_tot.grid(row=0, column=0, sticky="w")
        self.val_refund_total = ctk.CTkLabel(summary_f, text="₹0.00", font=ctk.CTkFont(size=14, weight="bold"), text_color=Theme.SUCCESS)
        self.val_refund_total.grid(row=0, column=1, sticky="e")
        
        self.btn_submit_sales_return = PrimaryButton(right_p, text="🔒 Complete Sales Return", command=self.submit_sales_return)
        self.btn_submit_sales_return.grid(row=3, column=0, padx=15, pady=(0, 15), sticky="ew")
        
        self.sales_cart = []
        self.bill_items_list = []
        self.sales_refund_sum = 0.0
        
    def retrieve_bill(self):
        bill_num = self.entry_bill_num.get().strip()
        if not bill_num:
            messagebox.showerror("Error", "Please input a bill number.")
            return
            
        bill = get_bill_by_number(bill_num)
        if not bill:
            messagebox.showerror("Error", f"Invoice #{bill_num} not found.")
            return
            
        self.bill_items_list = get_bill_items(bill_num)
        self.sales_cart.clear()
        self.populate_original_items()
        self.populate_sales_return_cart()
        
    def populate_original_items(self):
        for child in self.orig_scroll.winfo_children():
            child.destroy()
            
        if not self.bill_items_list:
            lbl = ctk.CTkLabel(self.orig_scroll, text="No items found in invoice.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
            lbl.pack(pady=30)
            return
            
        for idx, item in enumerate(self.bill_items_list):
            bg = Theme.BG_WINDOW if idx % 2 == 0 else Theme.BG_PANEL
            r = ctk.CTkFrame(self.orig_scroll, fg_color=bg, height=35, corner_radius=3)
            r.pack(fill="x", pady=1)
            r.grid_propagate(False)
            r.grid_rowconfigure(0, weight=1)
            
            vals = [
                item['medicine_name'],
                item['batch'],
                f"{item['quantity']} tab",
                f"₹{item['price_per_tablet']:.2f}"
            ]
            
            for c_idx, (v, weight) in enumerate(zip(vals, self.orig_w)):
                r.grid_columnconfigure(c_idx, weight=int(weight * 100))
                lbl = ctk.CTkLabel(r, text=v, font=ctk.CTkFont(size=10), text_color=Theme.TEXT_MAIN, anchor="w" if c_idx == 0 else "center")
                lbl.grid(row=0, column=c_idx, padx=5, sticky="ew" if c_idx == 0 else "")
                
            # Add to return list button
            r.grid_columnconfigure(4, weight=int(self.orig_w[4] * 100))
            btn_add = ctk.CTkButton(
                r, 
                text="↩️ Return", 
                width=65, 
                height=22, 
                fg_color=Theme.PRIMARY, 
                hover_color=Theme.PRIMARY_HOVER,
                command=lambda itm=item: self.open_return_qty_modal(itm)
            )
            btn_add.grid(row=0, column=4, sticky="")
            
    def open_return_qty_modal(self, item):
        # modal quantity popup
        modal = ctk.CTkToplevel(self)
        modal.title("Return Qty")
        modal.geometry("300x180")
        modal.grab_set()
        modal.resizable(False, False)
        
        modal.grid_columnconfigure(0, weight=1)
        
        lbl_title = ctk.CTkLabel(modal, text=f"Return: {item['medicine_name']}", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_title.pack(pady=(15, 5))
        
        lbl_max = ctk.CTkLabel(modal, text=f"Billed Qty: {item['quantity']} tablets", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED)
        lbl_max.pack(pady=(0, 10))
        
        entry_qty = ctk.CTkEntry(modal, placeholder_text="e.g. 5", width=100)
        entry_qty.pack(pady=5)
        entry_qty.insert(0, str(item['quantity']))
        
        def save():
            try:
                qty = int(entry_qty.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Invalid quantity.", parent=modal)
                return
                
            if qty <= 0 or qty > item['quantity']:
                messagebox.showerror("Error", f"Quantity must be between 1 and {item['quantity']}.", parent=modal)
                return
                
            # Add to return cart
            # check if exists
            for cart_item in self.sales_cart:
                if cart_item['medicine_id'] == item['medicine_id'] and cart_item['batch_number'] == item['batch']:
                    cart_item['quantity'] = qty
                    modal.destroy()
                    self.populate_sales_return_cart()
                    return
                    
            self.sales_cart.append({
                'medicine_id': item['medicine_id'],
                'medicine_name': item['medicine_name'],
                'batch_number': item['batch'],
                'quantity': qty,
                'price_per_tablet': item['price_per_tablet'],
                'gst_percent': item['gst_percent']
            })
            
            modal.destroy()
            self.populate_sales_return_cart()
            
        btn_ok = PrimaryButton(modal, text="Confirm", command=save, width=100)
        btn_ok.pack(pady=10)
        
    def populate_sales_return_cart(self):
        for child in self.ret_scroll.winfo_children():
            child.destroy()
            
        if not self.sales_cart:
            lbl = ctk.CTkLabel(self.ret_scroll, text="No items added for refund return.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
            lbl.pack(pady=30)
            self.val_refund_total.configure(text="₹0.00")
            self.sales_refund_sum = 0.0
            return
            
        total_refund = 0.0
        for idx, item in enumerate(self.sales_cart):
            sub = item['quantity'] * item['price_per_tablet']
            total_refund += sub
            
            bg = Theme.BG_WINDOW if idx % 2 == 0 else Theme.BG_PANEL
            r = ctk.CTkFrame(self.ret_scroll, fg_color=bg, height=35, corner_radius=3)
            r.pack(fill="x", pady=2)
            r.grid_propagate(False)
            r.grid_rowconfigure(0, weight=1)
            
            lbl_name = ctk.CTkLabel(r, text=f"{item['medicine_name']} ({item['quantity']} tab)", font=ctk.CTkFont(size=11, weight="bold"), anchor="w")
            lbl_name.pack(side="left", padx=10, fill="x", expand=True)
            
            lbl_val = ctk.CTkLabel(r, text=f"₹{sub:.2f}", font=ctk.CTkFont(size=11), text_color=Theme.SUCCESS)
            lbl_val.pack(side="left", padx=10)
            
            btn_del = ctk.CTkButton(
                r, 
                text="🗑️", 
                width=24, 
                height=22, 
                fg_color=Theme.DANGER, 
                hover_color=Theme.DANGER_HOVER,
                command=lambda pos=idx: self.remove_sales_cart_item(pos)
            )
            btn_del.pack(side="right", padx=5)
            
        self.val_refund_total.configure(text=f"₹{total_refund:.2f}")
        self.sales_refund_sum = total_refund
        
    def remove_sales_cart_item(self, pos):
        self.sales_cart.pop(pos)
        self.populate_sales_return_cart()
        
    def submit_sales_return(self):
        if not self.sales_cart:
            messagebox.showerror("Error", "The sales return list is empty.")
            return
            
        bill_num = self.entry_bill_num.get().strip()
        try:
            record_sales_return(bill_num, self.sales_cart, refund_mode="Cash")
            messagebox.showinfo("Success", f"Sales return recorded successfully. Refund Total: ₹{self.sales_refund_sum:.2f}")
            self.sales_cart.clear()
            self.bill_items_list.clear()
            self.entry_bill_num.delete(0, "end")
            self.populate_original_items()
            self.populate_sales_return_cart()
        except Exception as ex:
            messagebox.showerror("Return Error", str(ex))
            
    # --- PURCHASE RETURNS TAB ---
    def setup_purchase_returns_tab(self):
        self.tab_purchase.grid_columnconfigure(0, weight=2) # Return sub-form
        self.tab_purchase.grid_columnconfigure(1, weight=3) # Cart grid list
        self.tab_purchase.grid_rowconfigure(0, weight=1)
        
        # Left form
        form_frame = ctk.CTkFrame(self.tab_purchase, fg_color="transparent")
        form_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        form_frame.grid_columnconfigure(0, weight=1)
        
        lbl_title = ctk.CTkLabel(form_frame, text="Supplier Return Form", font=ctk.CTkFont(size=14, weight="bold"), text_color=Theme.PRIMARY)
        lbl_title.grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        lbl_sup = ctk.CTkLabel(form_frame, text="Select Supplier *", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_sup.grid(row=1, column=0, sticky="w", pady=(5, 1))
        self.combo_supplier = ctk.CTkComboBox(form_frame, values=["Select Supplier"], fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR, dropdown_fg_color=Theme.BG_PANEL, dropdown_text_color=Theme.TEXT_MAIN)
        self.combo_supplier.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        
        lbl_ref = ctk.CTkLabel(form_frame, text="Reference Invoice Number *", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_ref.grid(row=3, column=0, sticky="w", pady=(5, 1))
        self.entry_ref_invoice = ctk.CTkEntry(form_frame, placeholder_text="e.g. INVC-991", fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.entry_ref_invoice.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        
        # Search medicine to return
        lbl_med = ctk.CTkLabel(form_frame, text="Search Stock Medicine *", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_med.grid(row=5, column=0, sticky="w", pady=(5, 1))
        self.entry_med_search = ctk.CTkEntry(form_frame, placeholder_text="Type to search stock...", fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR)
        self.entry_med_search.grid(row=6, column=0, sticky="ew", pady=(0, 10))
        self.entry_med_search.bind("<KeyRelease>", self.on_med_search_change)
        
        # List results matching stock
        self.med_results = []
        self.med_results_combobox = ctk.CTkComboBox(form_frame, values=["Search Results"], fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR, command=self.on_med_selected)
        self.med_results_combobox.grid(row=7, column=0, sticky="ew", pady=(0, 10))
        
        # Row layout for Quantity & Rate inputs
        row_inputs = ctk.CTkFrame(form_frame, fg_color="transparent")
        row_inputs.grid(row=8, column=0, sticky="ew", pady=5)
        row_inputs.grid_columnconfigure((0, 1), weight=1)
        
        lbl_qty = ctk.CTkLabel(row_inputs, text="Return Qty (Tablets) *", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_qty.grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.entry_p_qty = ctk.CTkEntry(row_inputs, placeholder_text="10")
        self.entry_p_qty.grid(row=1, column=0, sticky="ew", padx=(0, 5), pady=(0, 5))
        
        lbl_rate = ctk.CTkLabel(row_inputs, text="Purchase Rate/Strip *", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_rate.grid(row=0, column=1, sticky="w", padx=(5, 0))
        self.entry_p_rate = ctk.CTkEntry(row_inputs, placeholder_text="0.00")
        self.entry_p_rate.grid(row=1, column=1, sticky="ew", padx=(5, 0), pady=(0, 5))
        
        self.btn_add_p_item = SecondaryButton(form_frame, text="➕ Add to Supplier Return Cart", command=self.add_purchase_return_item)
        self.btn_add_p_item.grid(row=9, column=0, sticky="ew", pady=10)
        
        # Right cart panel
        right_cart = ctk.CTkFrame(self.tab_purchase, fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=8)
        right_cart.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        right_cart.grid_columnconfigure(0, weight=1)
        right_cart.grid_rowconfigure(1, weight=1)
        
        lbl_rc = ctk.CTkLabel(right_cart, text="Returned Items to Supplier", font=ctk.CTkFont(size=13, weight="bold"), text_color=Theme.PRIMARY)
        lbl_rc.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        
        self.p_ret_scroll = ctk.CTkScrollableFrame(right_cart, fg_color="transparent")
        self.p_ret_scroll.grid(row=1, column=0, padx=15, sticky="nsew")
        self.p_ret_scroll.grid_columnconfigure(0, weight=1)
        
        p_summary = ctk.CTkFrame(right_cart, fg_color="transparent")
        p_summary.grid(row=2, column=0, padx=15, pady=15, sticky="ew")
        p_summary.grid_columnconfigure((0, 1), weight=1)
        
        lbl_rsum = ctk.CTkLabel(p_summary, text="Refund Credit Claim:", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_rsum.grid(row=0, column=0, sticky="w")
        self.val_p_refund = ctk.CTkLabel(p_summary, text="₹0.00", font=ctk.CTkFont(size=14, weight="bold"), text_color=Theme.SUCCESS)
        self.val_p_refund.grid(row=0, column=1, sticky="e")
        
        self.btn_save_p_return = PrimaryButton(right_cart, text="🔒 Complete Purchase Return", command=self.submit_purchase_return)
        self.btn_save_p_return.grid(row=3, column=0, padx=15, pady=(0, 15), sticky="ew")
        
        self.purchase_cart = []
        self.purchase_refund_sum = 0.0
        self.suppliers_list = []
        self.supplier_map = {}
        self.selected_med_data = None
        
    def refresh(self):
        # Refresh suppliers dropdown
        self.suppliers_list = get_all_suppliers()
        self.supplier_map = {s['name']: s['id'] for s in self.suppliers_list}
        options = ["Select Supplier"] + list(self.supplier_map.keys())
        self.combo_supplier.configure(values=options)
        self.combo_supplier.set("Select Supplier")
        
        # Reset sales tab
        self.entry_bill_num.delete(0, "end")
        self.sales_cart.clear()
        self.bill_items_list.clear()
        self.populate_original_items()
        self.populate_sales_return_cart()
        
        # Reset purchase tab
        self.entry_ref_invoice.delete(0, "end")
        self.entry_med_search.delete(0, "end")
        self.med_results_combobox.configure(values=["Search Results"])
        self.med_results_combobox.set("Search Results")
        self.entry_p_qty.delete(0, "end")
        self.entry_p_rate.delete(0, "end")
        self.purchase_cart.clear()
        self.selected_med_data = None
        self.populate_purchase_return_cart()
        
    def on_med_search_change(self, event=None):
        query = self.entry_med_search.get().strip()
        if not query:
            return
        matches = search_medicines(query)
        self.med_results = matches
        options = [f"{m['name']} - Batch: {m['batch']} (Avail: {m['quantity']})" for m in matches]
        if not options:
            options = ["No results found"]
        self.med_results_combobox.configure(values=options)
        self.med_results_combobox.set(options[0] if options else "Search Results")
        
    def on_med_selected(self, val):
        if not self.med_results:
            return
        # Find match
        for m in self.med_results:
            label = f"{m['name']} - Batch: {m['batch']} (Avail: {m['quantity']})"
            if label == val:
                self.selected_med_data = m
                self.entry_p_qty.delete(0, "end")
                self.entry_p_qty.insert(0, str(m['quantity']))
                self.entry_p_rate.delete(0, "end")
                self.entry_p_rate.insert(0, str(m['purchase_price']))
                break
                
    def add_purchase_return_item(self):
        if not self.selected_med_data:
            messagebox.showerror("Error", "Please select a stock medicine from the search results.")
            return
            
        try:
            qty = int(self.entry_p_qty.get().strip())
            rate = float(self.entry_p_rate.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric values entered.")
            return
            
        if qty <= 0 or qty > self.selected_med_data['quantity']:
            messagebox.showerror("Error", f"Quantity must be between 1 and {self.selected_med_data['quantity']}.")
            return
            
        # Add to cart
        self.purchase_cart.append({
            'medicine_id': self.selected_med_data['medicine_id'],
            'name': self.selected_med_data['name'],
            'batch_number': self.selected_med_data['batch'],
            'quantity': qty,
            'purchase_price': rate,
            'gst_percent': self.selected_med_data['gst'],
            'tablets_per_strip': self.selected_med_data['tablets_per_strip']
        })
        
        # Clean selections
        self.selected_med_data = None
        self.entry_med_search.delete(0, "end")
        self.med_results_combobox.configure(values=["Search Results"])
        self.med_results_combobox.set("Search Results")
        self.entry_p_qty.delete(0, "end")
        self.entry_p_rate.delete(0, "end")
        
        self.populate_purchase_return_cart()
        
    def populate_purchase_return_cart(self):
        for child in self.p_ret_scroll.winfo_children():
            child.destroy()
            
        if not self.purchase_cart:
            lbl = ctk.CTkLabel(self.p_ret_scroll, text="No items added to supplier return list.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
            lbl.pack(pady=30)
            self.val_p_refund.configure(text="₹0.00")
            self.purchase_refund_sum = 0.0
            return
            
        total_refund = 0.0
        for idx, item in enumerate(self.purchase_cart):
            # rate is per strip, qty is in tablets
            sub = (item['quantity'] / item['tablets_per_strip']) * item['purchase_price'] * (1 + item['gst_percent'] / 100.0)
            total_refund += sub
            
            bg = Theme.BG_WINDOW if idx % 2 == 0 else Theme.BG_PANEL
            r = ctk.CTkFrame(self.p_ret_scroll, fg_color=bg, height=35, corner_radius=3)
            r.pack(fill="x", pady=2)
            r.grid_propagate(False)
            r.grid_rowconfigure(0, weight=1)
            
            lbl_name = ctk.CTkLabel(r, text=f"{item['name']} ({item['quantity']} tab)", font=ctk.CTkFont(size=11, weight="bold"), anchor="w")
            lbl_name.pack(side="left", padx=10, fill="x", expand=True)
            
            lbl_val = ctk.CTkLabel(r, text=f"₹{sub:.2f}", font=ctk.CTkFont(size=11), text_color=Theme.SUCCESS)
            lbl_val.pack(side="left", padx=10)
            
            btn_del = ctk.CTkButton(
                r, 
                text="🗑️", 
                width=24, 
                height=22, 
                fg_color=Theme.DANGER, 
                hover_color=Theme.DANGER_HOVER,
                command=lambda pos=idx: self.remove_purchase_cart_item(pos)
            )
            btn_del.pack(side="right", padx=5)
            
        self.val_p_refund.configure(text=f"₹{total_refund:.2f}")
        self.purchase_refund_sum = total_refund
        
    def remove_purchase_cart_item(self, pos):
        self.purchase_cart.pop(pos)
        self.populate_purchase_return_cart()
        
    def submit_purchase_return(self):
        sup_name = self.combo_supplier.get()
        ref_inv = self.entry_ref_invoice.get().strip()
        
        if sup_name == "Select Supplier" or sup_name not in self.supplier_map:
            messagebox.showerror("Error", "Please select a valid supplier.")
            return
            
        if not ref_inv:
            messagebox.showerror("Error", "Original reference invoice number is required.")
            return
            
        if not self.purchase_cart:
            messagebox.showerror("Error", "The supplier return list is empty.")
            return
            
        supplier_id = self.supplier_map[sup_name]
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            record_purchase_return(
                supplier_id=supplier_id,
                return_date=date_str,
                total_refund=self.purchase_refund_sum,
                reference_invoice=ref_inv,
                returned_items=self.purchase_cart
            )
            messagebox.showinfo("Success", f"Purchase return registered successfully. Supplier credit adjusted: ₹{self.purchase_refund_sum:.2f}")
            self.refresh()
        except Exception as ex:
            messagebox.showerror("Return Error", str(ex))
