import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from utils.customer_service import get_all_customers, record_customer_payment
from utils.supplier_service import get_all_suppliers, record_supplier_payment
from ui.theme import Theme
from ui.components import PrimaryButton, SecondaryButton, StatCard

class AccountsFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(fg_color=Theme.BG_WINDOW)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        
        # 1. Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        
        self.title_lbl = ctk.CTkLabel(self.header_frame, text="💼 Financial Accounts & Ledger", font=ctk.CTkFont(size=24, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.title_lbl.pack(side="left")
        
        # 2. Stat Cards Summary Row
        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.stats_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.card_receivable = StatCard(self.stats_frame, title="Total Outstanding Receivables (Dues from Customers)", value="₹0.00", color_accent=Theme.SECONDARY, icon="📥")
        self.card_receivable.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        self.card_payable = StatCard(self.stats_frame, title="Total Outstanding Payables (Owed to Suppliers)", value="₹0.00", color_accent=Theme.DANGER, icon="📤")
        self.card_payable.grid(row=0, column=1, padx=(10, 0), sticky="ew")
        
        # 3. Tabview (Receivables / Payables)
        self.tabview = ctk.CTkTabview(self, fg_color=Theme.BG_PANEL, segmented_button_selected_color=Theme.PRIMARY, segmented_button_selected_hover_color=Theme.PRIMARY_HOVER)
        self.tabview.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        self.tab_recv = self.tabview.add("Customer Receivables (Outstanding Dues)")
        self.tab_pay = self.tabview.add("Supplier Payables (Unpaid Purchases)")
        
        # 4. Table Headers
        self.headers_bar = ctk.CTkFrame(self, fg_color=Theme.BG_PANEL, height=35, corner_radius=5)
        self.headers_bar.grid(row=3, column=0, padx=20, pady=(5, 0), sticky="ew")
        self.headers_bar.grid_propagate(False)
        self.headers_bar.grid_rowconfigure(0, weight=1)
        
        self.col_widths = [0.35, 0.2, 0.25, 0.2]
        headers = ["Name", "Contact Phone", "Outstanding Balance", "Action"]
        for idx, (h_name, w) in enumerate(zip(headers, self.col_widths)):
            self.headers_bar.grid_columnconfigure(idx, weight=int(w * 100))
            lbl = ctk.CTkLabel(self.headers_bar, text=h_name, font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
            lbl.grid(row=0, column=idx, padx=10, sticky="w" if idx == 0 else "")
            
        # 5. Scrollable Data Grid
        self.data_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.data_scroll.grid(row=4, column=0, padx=20, pady=(5, 15), sticky="nsew")
        self.grid_rowconfigure(4, weight=1)
        self.data_scroll.grid_columnconfigure(0, weight=1)
        
        self.customers_data = []
        self.suppliers_data = []
        
        # Connect tab change listener to refresh list
        # custom listener requires binding variables or tracking tabs
        self.tabview.configure(command=self.on_tab_changed)
        
    def refresh(self):
        # Fetch stats sums
        self.customers_data = [c for c in get_all_customers() if c['outstanding_balance'] > 0]
        self.suppliers_data = [s for s in get_all_suppliers() if s['current_balance'] > 0]
        
        sum_recv = sum(c['outstanding_balance'] for c in self.customers_data)
        sum_pay = sum(s['current_balance'] for s in self.suppliers_data)
        
        self.card_receivable.update_value(f"₹{sum_recv:.2f}")
        self.card_payable.update_value(f"₹{sum_pay:.2f}")
        
        self.on_tab_changed()
        
    def on_tab_changed(self):
        # Clear list
        for child in self.data_scroll.winfo_children():
            child.destroy()
            
        active_tab = self.tabview.get()
        
        if "Customer" in active_tab:
            data = self.customers_data
            is_recv = True
        else:
            data = self.suppliers_data
            is_recv = False
            
        if not data:
            lbl = ctk.CTkLabel(self.data_scroll, text="No active ledger balances in this section.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
            lbl.pack(pady=40)
            return
            
        for idx, item in enumerate(data):
            bg = Theme.BG_WINDOW if idx % 2 == 0 else Theme.BG_PANEL
            row_frame = ctk.CTkFrame(self.data_scroll, fg_color=bg, height=45, corner_radius=5)
            row_frame.pack(fill="x", pady=2, padx=1)
            row_frame.grid_propagate(False)
            row_frame.grid_rowconfigure(0, weight=1)
            
            bal = item['outstanding_balance'] if is_recv else item['current_balance']
            color = Theme.SECONDARY if is_recv else Theme.DANGER
            
            vals = [
                item['name'],
                item['phone'] or "N/A",
                f"₹{bal:.2f}"
            ]
            
            for c_idx, (v, w) in enumerate(zip(vals, self.col_widths)):
                row_frame.grid_columnconfigure(c_idx, weight=int(w * 100))
                lbl = ctk.CTkLabel(row_frame, text=str(v), font=ctk.CTkFont(size=11, weight="bold" if c_idx == 2 else "normal"), text_color=color if c_idx == 2 else Theme.TEXT_MAIN, anchor="w" if c_idx == 0 else "center")
                lbl.grid(row=0, column=c_idx, padx=10, sticky="ew" if c_idx == 0 else "")
                
            # Action button
            row_frame.grid_columnconfigure(3, weight=int(self.col_widths[3] * 100))
            btn_text = "📥 Clear Dues" if is_recv else "📤 Pay Invoice"
            btn_action = ctk.CTkButton(
                row_frame, 
                text=btn_text, 
                width=100, 
                height=26, 
                fg_color=Theme.PRIMARY, 
                hover_color=Theme.PRIMARY_HOVER,
                command=lambda val=item, r=is_recv: self.open_payment_modal(val, r)
            )
            btn_action.grid(row=0, column=3, sticky="")
            
    def open_payment_modal(self, item, is_recv):
        modal = ctk.CTkToplevel(self)
        modal.title("Clear Ledger Dues")
        modal.geometry("360x300")
        modal.grab_set()
        modal.resizable(False, False)
        
        modal.grid_columnconfigure(0, weight=1)
        
        title_text = f"Clear Dues: {item['name']}"
        title = ctk.CTkLabel(modal, text=title_text, font=ctk.CTkFont(size=15, weight="bold"), text_color=Theme.PRIMARY)
        title.pack(pady=(20, 5))
        
        curr_bal = item['outstanding_balance'] if is_recv else item['current_balance']
        lbl_bal = ctk.CTkLabel(modal, text=f"Total Pending Dues: ₹{curr_bal:.2f}", font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.DANGER)
        lbl_bal.pack(pady=(0, 15))
        
        # Form
        lbl_amt = ctk.CTkLabel(modal, text="Enter Paid Amount (₹) *", font=ctk.CTkFont(size=11, weight="bold"))
        lbl_amt.pack(pady=1)
        entry_amount = ctk.CTkEntry(modal, placeholder_text="0.00", width=160)
        entry_amount.pack(pady=4)
        entry_amount.insert(0, f"{curr_bal:.2f}")
        
        lbl_mode = ctk.CTkLabel(modal, text="Payment Mode *", font=ctk.CTkFont(size=11, weight="bold"))
        lbl_mode.pack(pady=1)
        combo_mode = ctk.CTkComboBox(modal, values=["Cash", "UPI", "Bank Card"], width=160)
        combo_mode.pack(pady=4)
        combo_mode.set("Cash")
        
        def save():
            try:
                amt = float(entry_amount.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Invalid numeric value.", parent=modal)
                return
                
            if amt <= 0 or amt > curr_bal:
                messagebox.showerror("Error", f"Amount must be between ₹0.01 and ₹{curr_bal:.2f}.", parent=modal)
                return
                
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                if is_recv:
                    record_customer_payment(
                        customer_id=item['id'],
                        date_str=date_str,
                        amount=amt,
                        payment_mode=combo_mode.get(),
                        reference_no="COL-LEDG",
                        description="Manual ledger outstanding settlement collections"
                    )
                else:
                    record_supplier_payment(
                        supplier_id=item['id'],
                        date_str=date_str,
                        amount=amt,
                        payment_mode=combo_mode.get(),
                        reference_no="PAY-LEDG",
                        description="Manual ledger supplier purchase payment"
                    )
                    
                messagebox.showinfo("Success", "Payment recorded successfully, ledger balances adjusted.", parent=modal)
                modal.destroy()
                self.refresh()
            except Exception as ex:
                messagebox.showerror("Error", str(ex), parent=modal)
                
        btn_pay = PrimaryButton(modal, text="💾 Save Payment", command=save, width=160)
        btn_pay.pack(pady=15)
