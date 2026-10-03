import customtkinter as ctk
from tkinter import messagebox
from ui.theme import Theme
from utils.sales_service import get_unpaid_bills, pay_unpaid_bill, get_total_unpaid_amount

class UnpaidBillsFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.configure(fg_color=Theme.BG_WINDOW)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # 1. Header Area
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="ew")
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="💳 Debtors & Unpaid Bills Tracker", font=ctk.CTkFont(size=24, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.title_label.pack(side="left")
        
        # Search Box
        self.search_entry = ctk.CTkEntry(self.header_frame, placeholder_text="Search debtor name or phone...", width=300, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, text_color=Theme.TEXT_MAIN)
        self.search_entry.pack(side="right", padx=(10, 0))
        self.search_entry.bind("<KeyRelease>", self.on_search)
        
        # 2. Metrics & Table Headers Frame
        self.top_section = ctk.CTkFrame(self, fg_color="transparent")
        self.top_section.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.top_section.grid_columnconfigure(0, weight=1)
        
        # Outstanding Card
        self.outstanding_card = ctk.CTkFrame(self.top_section, fg_color=Theme.BG_PANEL, border_color=Theme.DANGER, border_width=1, corner_radius=10, height=80)
        self.outstanding_card.grid(row=0, column=0, pady=(0, 15), sticky="ew")
        self.outstanding_card.grid_propagate(False)
        self.outstanding_card.grid_columnconfigure(0, weight=1)
        
        self.lbl_card_title = ctk.CTkLabel(self.outstanding_card, text="TOTAL OUTSTANDING CREDIT (UNPAID BALANCE)", font=ctk.CTkFont(size=11, weight="normal"), text_color=Theme.TEXT_MUTED)
        self.lbl_card_title.grid(row=0, column=0, padx=20, pady=(10, 2), sticky="w")
        
        self.lbl_card_value = ctk.CTkLabel(self.outstanding_card, text="₹0.00", font=ctk.CTkFont(size=24, weight="bold"), text_color=Theme.DANGER)
        self.lbl_card_value.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")
        
        # Table Headers
        self.headers_frame = ctk.CTkFrame(self.top_section, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, border_width=1, height=35, corner_radius=5)
        self.headers_frame.grid(row=1, column=0, sticky="ew")
        self.headers_frame.grid_propagate(False)
        self.headers_frame.grid_rowconfigure(0, weight=1)
        
        headers = [
            ("Bill No", 0.08),
            ("Date", 0.18),
            ("Customer Name", 0.27),
            ("Phone", 0.15),
            ("Outstanding Amount (₹)", 0.18),
            ("Action", 0.14)
        ]
        
        c_col = 0
        for text, weight in headers:
            col_weight = int(weight * 100)
            self.headers_frame.grid_columnconfigure(c_col, weight=col_weight)
            lbl = ctk.CTkLabel(self.headers_frame, text=text, font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
            lbl.grid(row=0, column=c_col, padx=5, sticky="w" if c_col in [2] else "")
            c_col += 1
            
        # 3. Scrollable List of Debts
        self.debts_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.debts_scroll.grid(row=2, column=0, padx=20, pady=(5, 15), sticky="nsew")
        self.debts_scroll.grid_columnconfigure(0, weight=1)
        
        self.all_unpaid = []
        
    def refresh(self):
        # Refresh statistics card value
        total_outstanding = get_total_unpaid_amount()
        self.lbl_card_value.configure(text=f"₹{total_outstanding:.2f}")
        
        # Load unpaid bills
        self.all_unpaid = get_unpaid_bills()
        self.search_entry.delete(0, "end")
        self.populate_unpaid_table(self.all_unpaid)
        
    def populate_unpaid_table(self, list_items):
        # Clear rows
        for child in self.debts_scroll.winfo_children():
            child.destroy()
            
        if not list_items:
            lbl_empty = ctk.CTkLabel(self.debts_scroll, text="No unpaid balance records found.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
            lbl_empty.pack(pady=40)
            return
            
        columns_weights = [8, 18, 27, 15, 18, 14]
        
        for idx, bill in enumerate(list_items):
            row_bg = Theme.BG_WINDOW if idx % 2 == 0 else Theme.BG_PANEL
            row_frame = ctk.CTkFrame(self.debts_scroll, fg_color=row_bg, border_color=Theme.BORDER_COLOR, border_width=1, height=45, corner_radius=5)
            row_frame.pack(fill="x", pady=3, padx=2)
            row_frame.grid_propagate(False)
            row_frame.grid_rowconfigure(0, weight=1)
            
            # Left red accent stripe
            accent_bar = ctk.CTkFrame(row_frame, width=4, fg_color=Theme.DANGER, corner_radius=0)
            accent_bar.place(x=0, y=0, relheight=1.0)
            
            for c_idx, weight in enumerate(columns_weights):
                row_frame.grid_columnconfigure(c_idx, weight=weight)
                
            # Details columns
            ctk.CTkLabel(row_frame, text=f"#{bill['bill_number']}", font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.TEXT_MAIN).grid(row=0, column=0, sticky="")
            ctk.CTkLabel(row_frame, text=bill['date'], font=ctk.CTkFont(size=11), text_color=Theme.TEXT_LIGHT).grid(row=0, column=1, sticky="")
            
            name_val = bill['customer_name'] if bill['customer_name'] else "Unknown Customer"
            ctk.CTkLabel(row_frame, text=name_val, font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.TEXT_MAIN, anchor="w").grid(row=0, column=2, padx=10, sticky="ew")
            
            phone_val = bill['customer_phone'] if bill['customer_phone'] else "N/A"
            ctk.CTkLabel(row_frame, text=phone_val, font=ctk.CTkFont(size=11), text_color=Theme.TEXT_LIGHT).grid(row=0, column=3, sticky="")
            
            ctk.CTkLabel(row_frame, text=f"₹{bill['grand_total']:.2f}", font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.DANGER).grid(row=0, column=4, sticky="")
            
            # Pay button trigger
            btn_pay = ctk.CTkButton(
                row_frame, 
                text="✔️ Clear Pay", 
                width=85, 
                height=26, 
                fg_color=Theme.SUCCESS, 
                hover_color=Theme.SUCCESS_HOVER,
                text_color="white",
                command=lambda b=bill: self.open_payment_modal(b)
            )
            btn_pay.grid(row=0, column=5, sticky="")
            
    def on_search(self, event=None):
        query = self.search_entry.get().strip().lower()
        if not query:
            self.populate_unpaid_table(self.all_unpaid)
            return
            
        filtered = []
        for b in self.all_unpaid:
            name = (b['customer_name'] or "").lower()
            phone = (b['customer_phone'] or "").lower()
            num = str(b['bill_number'])
            if query in name or query in phone or query in num:
                filtered.append(b)
                
        self.populate_unpaid_table(filtered)
        
    def open_payment_modal(self, bill):
        modal = ctk.CTkToplevel(self)
        modal.title(f"Clear Unpaid Invoice #{bill['bill_number']}")
        modal.geometry("450x300")
        modal.configure(fg_color=Theme.BG_WINDOW)
        modal.grab_set()
        modal.resizable(False, False)
        
        modal.grid_columnconfigure(0, weight=1)
        
        # Details Panel
        details_lbl = ctk.CTkLabel(
            modal, 
            text=f"Clearing balance for {bill['customer_name']}\nOutstanding: ₹{bill['grand_total']:.2f}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=Theme.TEXT_MAIN,
            justify="center"
        )
        details_lbl.pack(pady=(30, 20))
        
        # Payment options selector
        lbl_pay_mode = ctk.CTkLabel(modal, text="Select Receive Payment Method", font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.TEXT_LIGHT)
        lbl_pay_mode.pack(pady=(10, 5))
        
        combo_pay = ctk.CTkComboBox(
            modal, 
            values=["Cash", "UPI", "Card"], 
            width=200,
            fg_color=Theme.BG_WINDOW, 
            border_color=Theme.BORDER_COLOR, 
            button_color=Theme.BORDER_COLOR, 
            button_hover_color=Theme.PRIMARY, 
            text_color=Theme.TEXT_MAIN, 
            dropdown_fg_color=Theme.BG_PANEL, 
            dropdown_text_color=Theme.TEXT_MAIN
        )
        combo_pay.pack(pady=(0, 25))
        combo_pay.set("Cash")
        
        # Buttons layout
        btn_frame = ctk.CTkFrame(modal, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=10)
        btn_frame.grid_columnconfigure((0, 1), weight=1)
        
        btn_cancel = ctk.CTkButton(
            btn_frame, 
            text="Cancel", 
            fg_color=Theme.BORDER_COLOR, 
            hover_color=Theme.BG_WINDOW, 
            text_color=Theme.TEXT_LIGHT,
            command=modal.destroy
        )
        btn_cancel.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        btn_confirm = ctk.CTkButton(
            btn_frame, 
            text="Confirm Payment", 
            fg_color=Theme.SUCCESS, 
            hover_color=Theme.SUCCESS_HOVER,
            text_color="white",
            command=lambda: self.process_clear_payment(bill['bill_number'], combo_pay.get(), modal)
        )
        btn_confirm.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
    def process_clear_payment(self, bill_number, payment_mode, modal_window):
        try:
            pay_unpaid_bill(bill_number, payment_mode)
            messagebox.showinfo("Success", f"Invoice #{bill_number} marked as PAID via {payment_mode}.", parent=modal_window)
            modal_window.destroy()
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to record payment: {str(e)}", parent=modal_window)
