import customtkinter as ctk
import os
import subprocess
from tkinter import messagebox
from datetime import datetime
from utils.medicine_service import search_medicines, get_fefo_batches_for_medicine
from utils.customer_service import get_all_customers
from utils.sales_service import record_sale, generate_next_bill_number
from utils.pdf_service import generate_invoice_pdf
from ui.theme import Theme
from ui.components import PrimaryButton, SecondaryButton, DangerButton

class BillingFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(fg_color=Theme.BG_WINDOW)
        
        # POS Layout split: Left (60% width) for Search & Results, Right (40% width) for Cart & Receipt
        self.grid_columnconfigure(0, weight=3) # Left Area
        self.grid_columnconfigure(1, weight=2) # Right Area
        self.grid_rowconfigure(0, weight=1)
        
        self.cart = []
        self.active_customer_id = None
        self.all_customers = []
        
        # --- LEFT PANEL ---
        self.left_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.left_panel.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="nsew")
        self.left_panel.grid_columnconfigure(0, weight=1)
        self.left_panel.grid_rowconfigure(2, weight=1) # Search list results take up available space
        
        # F2 focus guide header
        self.header_left = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.header_left.grid(row=0, column=0, pady=(0, 10), sticky="ew")
        
        self.title_left = ctk.CTkLabel(self.header_left, text="🛒 POS Billing Terminal", font=ctk.CTkFont(size=22, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.title_left.pack(side="left")
        
        self.help_lbl = ctk.CTkLabel(self.header_left, text="[F2: Search]  [F4: New Bill]  [F6: Cust]  [F8: Pay]  [F10: Save]", font=ctk.CTkFont(size=10, weight="bold"), text_color=Theme.TEXT_MUTED)
        self.help_lbl.pack(side="right", padx=(10, 0))
        
        # Search Entry Bar
        self.search_entry = ctk.CTkEntry(self.left_panel, placeholder_text="F2 - Type Medicine Name, Generic, Brand, or Batch...", height=40, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, text_color=Theme.TEXT_MAIN)
        self.search_entry.grid(row=1, column=0, pady=(0, 10), sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.on_search)
        
        # Search Results Grid Scroll
        self.results_scroll = ctk.CTkScrollableFrame(self.left_panel, fg_color="transparent")
        self.results_scroll.grid(row=2, column=0, sticky="nsew")
        self.results_scroll.grid_columnconfigure(0, weight=1)
        
        # --- RIGHT PANEL ---
        self.right_panel = ctk.CTkFrame(self, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=10)
        self.right_panel.grid(row=0, column=1, padx=(10, 15), pady=15, sticky="nsew")
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(2, weight=1) # Receipt preview takes space
        
        # Header Checkout Title
        self.title_right = ctk.CTkLabel(self.right_panel, text="Invoice Summary", font=ctk.CTkFont(size=18, weight="bold"), text_color=Theme.PRIMARY)
        self.title_right.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")
        
        # Customer Selection Panel
        self.cust_panel = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.cust_panel.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="ew")
        self.cust_panel.grid_columnconfigure(0, weight=1)
        
        lbl_cname = ctk.CTkLabel(self.cust_panel, text="Customer (F6)", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_cname.grid(row=0, column=0, pady=(0, 2), sticky="w")
        
        # Combo selection box for customer names
        self.combo_customer = ctk.CTkComboBox(self.cust_panel, values=["Walk-in Cash Customer"], fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR, dropdown_fg_color=Theme.BG_PANEL, dropdown_text_color=Theme.TEXT_MAIN, command=self.on_customer_change)
        self.combo_customer.grid(row=1, column=0, pady=(0, 5), sticky="ew")
        self.combo_customer.set("Walk-in Cash Customer")
        
        inputs_grid = ctk.CTkFrame(self.cust_panel, fg_color="transparent")
        inputs_grid.grid(row=2, column=0, pady=2, sticky="ew")
        inputs_grid.grid_columnconfigure((0, 1), weight=1)
        
        lbl_pay = ctk.CTkLabel(inputs_grid, text="Payment (F8)", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_pay.grid(row=0, column=0, padx=(0, 5), pady=(0, 1), sticky="w")
        self.combo_payment = ctk.CTkComboBox(inputs_grid, values=["Cash", "UPI", "Card", "Unpaid"], fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR, command=lambda v: self.recalculate_totals())
        self.combo_payment.grid(row=1, column=0, padx=(0, 5), pady=(0, 5), sticky="ew")
        self.combo_payment.set("Cash")
        
        lbl_disc = ctk.CTkLabel(inputs_grid, text="Discount (%)", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_disc.grid(row=0, column=1, padx=(5, 0), pady=(0, 1), sticky="w")
        self.entry_discount_pct = ctk.CTkEntry(inputs_grid, placeholder_text="0")
        self.entry_discount_pct.grid(row=1, column=1, padx=(5, 0), pady=(0, 5), sticky="ew")
        self.entry_discount_pct.insert(0, "0")
        self.entry_discount_pct.bind("<KeyRelease>", self.recalculate_totals)
        
        # 3. Monospace Thermal Receipt Sheet Preview
        self.receipt_paper = ctk.CTkFrame(self.right_panel, fg_color="#F8FAFC", border_color="#E2E8F0", border_width=2, corner_radius=6)
        self.receipt_paper.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.right_panel.grid_rowconfigure(2, weight=1)
        
        self.receipt_textbox = ctk.CTkTextbox(self.receipt_paper, font=("Consolas", 10), fg_color="#FFFFFF", text_color="#1E293B", border_width=0, corner_radius=4)
        self.receipt_textbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Keyboard binds variables
        self.grand_total_val = 0.0
        
        # Checkout Button
        self.btn_checkout = ctk.CTkButton(self.right_panel, text="🔒 Save & Print (F10)", height=45, fg_color=Theme.SUCCESS, hover_color=Theme.SUCCESS_HOVER, command=self.checkout)
        self.btn_checkout.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        
        # Bind Global Keyboard Shortcuts
        self.bind_all_shortcuts()
        
    def bind_all_shortcuts(self):
        # Bind keys to controller main root if possible, or bind locally
        self.bind_all("<F2>", lambda e: self.search_entry.focus())
        self.bind_all("<F4>", lambda e: self.clear_cart())
        self.bind_all("<F6>", lambda e: self.combo_customer.focus())
        self.bind_all("<F8>", lambda e: self.combo_payment.focus())
        self.bind_all("<F10>", lambda e: self.checkout())
        
    def refresh(self):
        # Fetch customers suggestions
        self.all_customers = get_all_customers()
        self.customer_mapping = {c['name']: c['id'] for c in self.all_customers}
        
        cust_list = ["Walk-in Cash Customer"] + list(self.customer_mapping.keys())
        self.combo_customer.configure(values=cust_list)
        self.combo_customer.set("Walk-in Cash Customer")
        self.active_customer_id = None
        
        # Clean fields
        self.search_entry.delete(0, "end")
        self.clear_cart()
        self.search_entry.focus()
        
    def on_customer_change(self, val):
        if val in self.customer_mapping:
            self.active_customer_id = self.customer_mapping[val]
        else:
            self.active_customer_id = None
        self.recalculate_totals()
        
    def on_search(self, event=None):
        query = self.search_entry.get().strip()
        if not query:
            for child in self.results_scroll.winfo_children():
                child.destroy()
            return
            
        matches = search_medicines(query)
        
        # Populate results scroll
        for child in self.results_scroll.winfo_children():
            child.destroy()
            
        if not matches:
            lbl = ctk.CTkLabel(self.results_scroll, text="No matching medicines found in stock.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
            lbl.pack(pady=20)
            return
            
        for idx, med in enumerate(matches):
            bg = Theme.BG_WINDOW if idx % 2 == 0 else Theme.BG_PANEL
            frame = ctk.CTkFrame(self.results_scroll, fg_color=bg, height=45, corner_radius=5)
            frame.pack(fill="x", pady=2, padx=5)
            frame.grid_propagate(False)
            frame.grid_rowconfigure(0, weight=1)
            
            # Layout widths: Name (40%), Batch (15%), Expiry (15%), Stock (15%), Button (15%)
            frame.grid_columnconfigure(0, weight=40)
            frame.grid_columnconfigure(1, weight=15)
            frame.grid_columnconfigure(2, weight=15)
            frame.grid_columnconfigure(3, weight=15)
            frame.grid_columnconfigure(4, weight=15)
            
            lbl_name = ctk.CTkLabel(frame, text=med['name'], font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.TEXT_MAIN, anchor="w")
            lbl_name.grid(row=0, column=0, padx=10, sticky="ew")
            
            lbl_batch = ctk.CTkLabel(frame, text=med['batch'], font=ctk.CTkFont(size=11), text_color=Theme.TEXT_LIGHT)
            lbl_batch.grid(row=0, column=1, sticky="")
            
            lbl_exp = ctk.CTkLabel(frame, text=med['expiry_date'], font=ctk.CTkFont(size=11), text_color=Theme.WARNING if med['quantity'] <= med['reorder_level'] else Theme.TEXT_MUTED)
            lbl_exp.grid(row=0, column=2, sticky="")
            
            lbl_stock = ctk.CTkLabel(frame, text=f"{med['quantity']} tab", font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.SUCCESS if med['quantity'] > 0 else Theme.DANGER)
            lbl_stock.grid(row=0, column=3, sticky="")
            
            # Select/Add button
            btn_add = ctk.CTkButton(
                frame, 
                text="➕ Add", 
                width=55, 
                height=26, 
                fg_color=Theme.PRIMARY, 
                hover_color=Theme.PRIMARY_HOVER,
                command=lambda m=med: self.select_medicine_to_cart(m)
            )
            btn_add.grid(row=0, column=4, padx=5, sticky="")

    def select_medicine_to_cart(self, med):
        # Verify if medicine has multiple batches or handle directly
        # For simplicity, search_medicines already returned specific batches from database.
        # We can add this specific batch directly to cart, and ask for quantity!
        
        # Open small dialog/modal asking for quantity
        modal = ctk.CTkToplevel(self)
        modal.title("Add Item Quantity")
        modal.geometry("350x200")
        modal.grab_set()
        modal.resizable(False, False)
        
        modal.grid_columnconfigure(0, weight=1)
        
        lbl_title = ctk.CTkLabel(modal, text=med['name'], font=ctk.CTkFont(size=14, weight="bold"), text_color=Theme.PRIMARY)
        lbl_title.pack(pady=(20, 5))
        
        lbl_batch = ctk.CTkLabel(modal, text=f"Batch: {med['batch']} | Available: {med['quantity']} tab", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED)
        lbl_batch.pack(pady=(0, 15))
        
        # Qty input
        lbl_qty = ctk.CTkLabel(modal, text="Enter Quantity (Tablets) *", font=ctk.CTkFont(size=11, weight="bold"))
        lbl_qty.pack(pady=2)
        entry_qty = ctk.CTkEntry(modal, placeholder_text="e.g. 10", width=120)
        entry_qty.pack(pady=5)
        entry_qty.insert(0, "10")
        entry_qty.focus()
        
        # Bind keys inside modal
        entry_qty.bind("<Return>", lambda e: submit_qty())
        modal.bind("<Escape>", lambda e: modal.destroy())
        
        def submit_qty():
            try:
                qty = int(entry_qty.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid integer quantity.", parent=modal)
                return
                
            if qty <= 0:
                messagebox.showerror("Error", "Quantity must be greater than 0.", parent=modal)
                return
                
            if qty > med['quantity']:
                messagebox.showerror("Stock Alert", f"Insufficient stock. Available quantity: {med['quantity']} tablets.", parent=modal)
                return
                
            # Add to cart
            # Check if this batch is already in the cart
            existing_item = None
            for item in self.cart:
                if item['medicine_id'] == med['medicine_id'] and item['batch_number'] == med['batch']:
                    existing_item = item
                    break
                    
            if existing_item:
                if existing_item['quantity'] + qty > med['quantity']:
                    messagebox.showerror("Stock Alert", f"Cannot add. Total cart quantity exceeds available stock.", parent=modal)
                    return
                existing_item['quantity'] += qty
                existing_item['subtotal'] = existing_item['quantity'] * (med['selling_price'] / med['tablets_per_strip'])
            else:
                self.cart.append({
                    'medicine_id': med['medicine_id'],
                    'name': med['name'],
                    'batch_number': med['batch'],
                    'quantity': qty,
                    'price_per_tablet': med['selling_price'] / med['tablets_per_strip'],
                    'purchase_price_per_tablet': med['purchase_price'] / med['tablets_per_strip'],
                    'subtotal': qty * (med['selling_price'] / med['tablets_per_strip']),
                    'gst_percent': med['gst']
                })
                
            modal.destroy()
            self.search_entry.delete(0, "end")
            for child in self.results_scroll.winfo_children():
                child.destroy()
            self.search_entry.focus()
            self.recalculate_totals()
            
        btn_add = PrimaryButton(modal, text="Add to Cart", command=submit_qty, width=120)
        btn_add.pack(pady=10)

    def clear_cart(self):
        self.cart.clear()
        self.recalculate_totals()
        
    def recalculate_totals(self, event=None):
        cart_total = sum(item['subtotal'] for item in self.cart)
        
        discount_str = self.entry_discount_pct.get().strip()
        try:
            discount = float(discount_str) if discount_str else 0.0
        except ValueError:
            discount = 0.0
            
        if discount < 0.0 or discount > 100.0:
            discount = 0.0
            
        discount_amount = cart_total * discount / 100.0
        grand_total = cart_total - discount_amount
        self.grand_total_val = grand_total
        
        # Calculate split tax CGST/SGST (e.g. 12% total tax split into 6% CGST & 6% SGST)
        total_gst = 0.0
        for item in self.cart:
            item_sub = item['subtotal'] * (1 - discount/100.0)
            taxable = item_sub / (1 + item['gst_percent'] / 100.0)
            total_gst += (item_sub - taxable)
            
        cgst = total_gst / 2.0
        sgst = total_gst / 2.0
        
        # Format live receipt text
        cust_name = self.combo_customer.get()
        payment_mode = self.combo_payment.get()
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        receipt_text = (
            "===================================\n"
            "       MEDITRACK PHARMACY ERP       \n"
            "       POS retail invoice preview    \n"
            "===================================\n"
            f"Date: {date_str}\n"
            f"Customer: {cust_name[:20]}\n"
            f"Payment: {payment_mode}\n"
            "-----------------------------------\n"
            "ITEM            QTY   RATE   TOTAL\n"
            "-----------------------------------\n"
        )
        
        for idx, item in enumerate(self.cart):
            # Monospace layout formatting
            name_trunc = item['name'][:14].ljust(14)
            qty_str = str(item['quantity']).rjust(4)
            rate_str = f"{item['price_per_tablet']:.2f}".rjust(6)
            sub_str = f"₹{item['subtotal']:.2f}".rjust(7)
            receipt_text += f"{name_trunc} {qty_str} {rate_str} {sub_str}\n"
            
        receipt_text += (
            "-----------------------------------\n"
            f"Gross Total:            ₹{cart_total:.2f}\n"
            f"Discount ({discount:.1f}%):        ₹{discount_amount:.2f}\n"
            f"CGST Tax (split):       ₹{cgst:.2f}\n"
            f"SGST Tax (split):       ₹{sgst:.2f}\n"
            "-----------------------------------\n"
            f"GRAND TOTAL:            ₹{grand_total:.2f}\n"
            "===================================\n"
            "    * Thank you! Get Well Soon *    \n"
            "===================================\n"
        )
        
        self.receipt_textbox.configure(state="normal")
        self.receipt_textbox.delete("1.0", "end")
        self.receipt_textbox.insert("1.0", receipt_text)
        self.receipt_textbox.configure(state="disabled")

    def checkout(self):
        if not self.cart:
            messagebox.showerror("Checkout Error", "Your retail POS cart is empty.")
            return
            
        cust_name = self.combo_customer.get()
        payment_mode = self.combo_payment.get()
        
        if payment_mode == "Unpaid":
            if cust_name == "Walk-in Cash Customer" or not self.active_customer_id:
                messagebox.showerror("Credit Sale Error", "Please select a registered customer to process Credit/Unpaid sale.")
                return
                
        discount_str = self.entry_discount_pct.get().strip()
        try:
            discount = float(discount_str) if discount_str else 0.0
        except ValueError:
            messagebox.showerror("Discount Error", "Invalid discount percentage.")
            return
            
        # Call record_sale from service
        try:
            # Map cart items structure for sales service
            formatted_items = [
                {
                    'medicine_id': item['medicine_id'], 
                    'batch_number': item['batch_number'], 
                    'quantity': item['quantity']
                } for item in self.cart
            ]
            
            bill_num = record_sale(
                customer_id=self.active_customer_id,
                customer_name=cust_name,
                customer_phone="", # Phone resolved from database if customer selected
                payment_mode=payment_mode,
                cart_items=formatted_items,
                discount_percent=discount
            )
            
            # Print PDF automatically
            pdf_path = generate_invoice_pdf(bill_num)
            messagebox.showinfo("Success", f"Invoice #{bill_num} printed successfully. Grand Total: ₹{self.grand_total_val:.2f}")
            
            # Auto open PDF
            if os.path.exists(pdf_path):
                try:
                    if os.name == 'nt':
                        os.startfile(pdf_path)
                    elif os.name == 'posix':
                        subprocess.run(['open', pdf_path])
                except Exception:
                    pass
                    
            self.refresh()
        except Exception as ex:
            messagebox.showerror("Checkout Failed", f"Transaction Error: {str(ex)}")