import os
import subprocess
import customtkinter as ctk
from tkinter import messagebox
from utils.sales_service import get_all_bills, get_bill_by_number, get_bill_items
from utils.pdf_service import generate_invoice_pdf
from ui.theme import Theme

class SalesHistoryFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(fg_color=Theme.BG_WINDOW)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # 1. Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="Sales History & Transactions", font=ctk.CTkFont(size=24, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.title_label.pack(side="left")
        
        # Search
        self.search_entry = ctk.CTkEntry(self.header_frame, placeholder_text="Search by bill number or customer name...", width=300, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, text_color=Theme.TEXT_MAIN)
        self.search_entry.pack(side="right")
        self.search_entry.bind("<KeyRelease>", self.on_search)
        
        # 2. Table Headers
        self.headers_frame = ctk.CTkFrame(self, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, border_width=1, height=35, corner_radius=5)
        self.headers_frame.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="ew")
        self.headers_frame.grid_propagate(False)
        self.headers_frame.grid_rowconfigure(0, weight=1)
        
        headers = [
            ("Bill No", 0.08),
            ("Date", 0.18),
            ("Customer Name", 0.25),
            ("Phone", 0.14),
            ("Payment", 0.10),
            ("Grand Total (₹)", 0.15),
            ("Action", 0.10)
        ]
        
        c_col = 0
        for text, weight in headers:
            col_weight = int(weight * 100)
            self.headers_frame.grid_columnconfigure(c_col, weight=col_weight)
            lbl = ctk.CTkLabel(self.headers_frame, text=text, font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
            lbl.grid(row=0, column=c_col, padx=5, sticky="w" if c_col == 2 else "")
            c_col += 1
            
        # 3. Scrollable Bills List
        self.bills_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.bills_scroll.grid(row=2, column=0, padx=20, pady=(5, 15), sticky="nsew")
        self.bills_scroll.grid_columnconfigure(0, weight=1)
        
        self.all_bills = []
        
    def refresh(self):
        self.all_bills = get_all_bills()
        self.search_entry.delete(0, "end")
        self.populate_bills_table(self.all_bills)
        
    def populate_bills_table(self, bills_list):
        for child in self.bills_scroll.winfo_children():
            child.destroy()
            
        if not bills_list:
            lbl_empty = ctk.CTkLabel(self.bills_scroll, text="No sales history found.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
            lbl_empty.pack(pady=40)
            return
            
        columns_weights = [8, 18, 25, 14, 10, 15, 10]
        
        for idx, bill in enumerate(bills_list):
            row_bg = Theme.BG_WINDOW if idx % 2 == 0 else Theme.BG_PANEL
            row_frame = ctk.CTkFrame(self.bills_scroll, fg_color=row_bg, border_color=Theme.BORDER_COLOR, border_width=1, height=45, corner_radius=5)
            row_frame.pack(fill="x", pady=3, padx=2)
            row_frame.grid_propagate(False)
            row_frame.grid_rowconfigure(0, weight=1)
            
            for c_idx, weight in enumerate(columns_weights):
                row_frame.grid_columnconfigure(c_idx, weight=weight)
                
            # Columns
            ctk.CTkLabel(row_frame, text=f"#{bill['bill_number']}", font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.TEXT_MAIN).grid(row=0, column=0, sticky="")
            ctk.CTkLabel(row_frame, text=bill['date'], font=ctk.CTkFont(size=11), text_color=Theme.TEXT_LIGHT).grid(row=0, column=1, sticky="")
            
            cust_name = bill['customer_name'] if bill['customer_name'] else "Walk-in Customer"
            ctk.CTkLabel(row_frame, text=cust_name, font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.TEXT_MAIN, anchor="w").grid(row=0, column=2, padx=10, sticky="ew")
            
            cust_phone = bill['customer_phone'] if bill['customer_phone'] else "N/A"
            ctk.CTkLabel(row_frame, text=cust_phone, font=ctk.CTkFont(size=11), text_color=Theme.TEXT_LIGHT).grid(row=0, column=3, sticky="")
            
            ctk.CTkLabel(row_frame, text=bill['payment_mode'], font=ctk.CTkFont(size=11), text_color=Theme.TEXT_LIGHT).grid(row=0, column=4, sticky="")
            
            ctk.CTkLabel(row_frame, text=f"₹{bill['grand_total']:.2f}", font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.SUCCESS).grid(row=0, column=5, sticky="")
            
            # Action button (View details)
            btn_view = ctk.CTkButton(
                row_frame, 
                text="👁️ View", 
                width=65, 
                height=26, 
                fg_color=Theme.SECONDARY, 
                hover_color=Theme.SECONDARY_HOVER,
                text_color="white",
                command=lambda b_num=bill['bill_number']: self.open_bill_details(b_num)
            )
            btn_view.grid(row=0, column=6, sticky="")

    def on_search(self, event=None):
        query = self.search_entry.get().strip().lower()
        if not query:
            self.populate_bills_table(self.all_bills)
            return
            
        filtered = []
        for b in self.all_bills:
            name = (b['customer_name'] or "").lower()
            num = str(b['bill_number'])
            if query in name or query in num:
                filtered.append(b)
                
        self.populate_bills_table(filtered)

    def open_bill_details(self, bill_number):
        # Create a detailed Toplevel modal window
        detail_win = ctk.CTkToplevel(self)
        detail_win.title(f"Bill Details - #{bill_number}")
        detail_win.geometry("700x550")
        detail_win.configure(fg_color=Theme.BG_WINDOW)
        detail_win.grab_set() # Focus modal
        detail_win.resizable(False, False)
        
        detail_win.grid_columnconfigure(0, weight=1)
        detail_win.grid_rowconfigure(2, weight=1)
        
        bill = get_bill_by_number(bill_number)
        items = get_bill_items(bill_number)
        
        # 1. Bill Details Meta Panel
        meta_panel = ctk.CTkFrame(detail_win, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=10)
        meta_panel.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        meta_panel.grid_columnconfigure((0, 1), weight=1)
        
        cust_name = bill['customer_name'] if bill['customer_name'] else "Walk-in Customer"
        cust_phone = bill['customer_phone'] if bill['customer_phone'] else "N/A"
        
        left_meta = (
            f"<b>Bill Number:</b> #{bill['bill_number']}\n"
            f"<b>Date:</b> {bill['date']}\n"
            f"<b>Payment Mode:</b> {bill['payment_mode']}"
        )
        
        right_meta = (
            f"<b>Customer Name:</b> {cust_name}\n"
            f"<b>Customer Phone:</b> {cust_phone}"
        )
        
        lbl_left = ctk.CTkLabel(meta_panel, text=left_meta, justify="left", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_LIGHT)
        lbl_left.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        lbl_right = ctk.CTkLabel(meta_panel, text=right_meta, justify="left", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_LIGHT)
        lbl_right.grid(row=0, column=1, padx=20, pady=15, sticky="w")
        
        # 2. Table Headers
        table_headers = ctk.CTkFrame(detail_win, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, border_width=1, height=30)
        table_headers.grid(row=1, column=0, padx=20, pady=(5, 0), sticky="ew")
        table_headers.grid_propagate(False)
        table_headers.grid_rowconfigure(0, weight=1)
        
        grid_cols = [
            ("S.No", 0.08),
            ("Medicine (Batch)", 0.40),
            ("Qty", 0.10),
            ("Price/Tab", 0.14),
            ("Subtotal", 0.16),
            ("Profit", 0.12)
        ]
        
        c_col = 0
        for text, weight in grid_cols:
            col_weight = int(weight * 100)
            table_headers.grid_columnconfigure(c_col, weight=col_weight)
            lbl = ctk.CTkLabel(table_headers, text=text, font=ctk.CTkFont(size=10, weight="bold"), text_color=Theme.TEXT_LIGHT)
            lbl.grid(row=0, column=c_col, padx=5, sticky="w" if c_col == 1 else "")
            c_col += 1
            
        # 3. Scrollable Items list
        items_scroll = ctk.CTkScrollableFrame(detail_win, fg_color="transparent")
        items_scroll.grid(row=2, column=0, padx=20, pady=5, sticky="nsew")
        items_scroll.grid_columnconfigure(0, weight=1)
        
        item_col_weights = [8, 40, 10, 14, 16, 12]
        
        for idx, item in enumerate(items):
            row_bg = Theme.BG_WINDOW if idx % 2 == 0 else Theme.BG_PANEL
            row = ctk.CTkFrame(items_scroll, fg_color=row_bg, border_color=Theme.BORDER_COLOR, border_width=1, height=35, corner_radius=3)
            row.pack(fill="x", pady=2, padx=2)
            row.grid_propagate(False)
            row.grid_rowconfigure(0, weight=1)
            
            for c_idx, weight in enumerate(item_col_weights):
                row.grid_columnconfigure(c_idx, weight=weight)
                
            ctk.CTkLabel(row, text=str(idx+1), font=ctk.CTkFont(size=11), text_color=Theme.TEXT_LIGHT).grid(row=0, column=0, sticky="")
            
            med_batch = f"{item['medicine_name']} (Batch: {item['batch']})"
            ctk.CTkLabel(row, text=med_batch, font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_MAIN, anchor="w").grid(row=0, column=1, padx=10, sticky="ew")
            
            ctk.CTkLabel(row, text=f"{item['quantity']} tab", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_LIGHT).grid(row=0, column=2, sticky="")
            ctk.CTkLabel(row, text=f"₹{item['price_per_tablet']:.2f}", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_LIGHT).grid(row=0, column=3, sticky="")
            ctk.CTkLabel(row, text=f"₹{item['subtotal']:.2f}", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_MAIN).grid(row=0, column=4, sticky="")
            ctk.CTkLabel(row, text=f"₹{item['profit']:.2f}", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED).grid(row=0, column=5, sticky="")

        # 4. Summary & Actions Footer
        summary_panel = ctk.CTkFrame(detail_win, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=10)
        summary_panel.grid(row=3, column=0, padx=20, pady=(5, 20), sticky="ew")
        summary_panel.grid_columnconfigure((0, 1), weight=1)
        
        totals_text = (
            f"<b>Gross Total:</b> ₹{bill['total_amount']:.2f}\n"
            f"<b>Discount Applied ({bill['discount']}%):</b> ₹{bill['discount_amount']:.2f}\n"
            f"<b>Grand Total:</b> <font color='{Theme.SUCCESS}'><b>₹{bill['grand_total']:.2f}</b></font>\n"
            f"<b>Estimated Profit Margin:</b> ₹{bill['total_profit']:.2f}"
        )
        
        lbl_summary = ctk.CTkLabel(summary_panel, text=totals_text, justify="left", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_LIGHT)
        lbl_summary.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # Re-print button
        btn_print = ctk.CTkButton(
            summary_panel, 
            text="🖨️ Re-generate PDF & Open", 
            fg_color=Theme.SUCCESS, 
            hover_color=Theme.SUCCESS_HOVER,
            text_color="white",
            command=lambda: self.print_bill_pdf(bill_number, detail_win)
        )
        btn_print.grid(row=0, column=1, padx=20, pady=15, sticky="e")
        
    def print_bill_pdf(self, bill_number, modal):
        try:
            pdf_path = generate_invoice_pdf(bill_number)
            messagebox.showinfo("Success", f"Invoice #{bill_number} PDF regenerated successfully.", parent=modal)
            
            # Open PDF
            if os.path.exists(pdf_path):
                if os.name == 'nt':
                    os.startfile(pdf_path)
                elif os.name == 'posix':
                    subprocess.run(['open', pdf_path])
        except Exception as ex:
            messagebox.showerror("Error", f"Failed to open PDF: {str(ex)}", parent=modal)
