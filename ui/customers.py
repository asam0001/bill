import customtkinter as ctk
from tkinter import messagebox
from utils.customer_service import (
    get_all_customers, get_customer_by_id, add_customer, update_customer, delete_customer, get_customer_ledger
)
from ui.theme import Theme
from ui.components import PrimaryButton, SecondaryButton, DangerButton

class CustomersFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(fg_color=Theme.BG_WINDOW)
        
        self.selected_customer_id = None
        self.all_customers = []
        
        # Configure layout (2 columns: Directory and Form/Ledger Panel)
        self.grid_columnconfigure(0, weight=3) # 45% width
        self.grid_columnconfigure(1, weight=4) # 55% width
        self.grid_rowconfigure(0, weight=1)
        
        # 1. Left Side: Directory
        self.directory_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.directory_frame.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="nsew")
        self.directory_frame.grid_columnconfigure(0, weight=1)
        self.directory_frame.grid_rowconfigure(2, weight=1)
        
        self.title_left = ctk.CTkLabel(self.directory_frame, text="Customer Registry", font=ctk.CTkFont(size=20, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.title_left.grid(row=0, column=0, pady=(0, 10), sticky="w")
        
        # Search Bar
        self.search_entry = ctk.CTkEntry(self.directory_frame, placeholder_text="Search customers by name...", fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, text_color=Theme.TEXT_MAIN)
        self.search_entry.grid(row=1, column=0, pady=(0, 10), sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.on_search)
        
        # Customer List Scroll
        self.list_scroll = ctk.CTkScrollableFrame(self.directory_frame, fg_color="transparent")
        self.list_scroll.grid(row=2, column=0, sticky="nsew")
        
        # 2. Right Side: Tabview (Profile Form & Ledger History)
        self.right_tabview = ctk.CTkTabview(self, fg_color=Theme.BG_PANEL, segmented_button_selected_color=Theme.PRIMARY, segmented_button_selected_hover_color=Theme.PRIMARY_HOVER)
        self.right_tabview.grid(row=0, column=1, padx=(10, 15), pady=15, sticky="nsew")
        
        self.tab_form = self.right_tabview.add("Profile Form")
        self.tab_ledger = self.right_tabview.add("Customer Ledger")
        
        # Form scroll container
        self.form_scroll = ctk.CTkScrollableFrame(self.tab_form, fg_color="transparent")
        self.form_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        self.form_scroll.grid_columnconfigure(0, weight=1)
        
        self.title_right = ctk.CTkLabel(self.form_scroll, text="Add New Customer", font=ctk.CTkFont(size=18, weight="bold"), text_color=Theme.PRIMARY)
        self.title_right.grid(row=0, column=0, padx=20, pady=(10, 10), sticky="w")
        
        # Fields
        self.fields = {}
        form_labels = [
            ("Customer Name *", "name"),
            ("Phone Number", "phone"),
            ("Email Address", "email"),
            ("GSTIN Number", "gst_number"),
            ("Credit Limit (₹)", "credit_limit"),
            ("Home / Billing Address", "address")
        ]
        
        current_row = 1
        for label_text, key in form_labels:
            lbl = ctk.CTkLabel(self.form_scroll, text=label_text, font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
            lbl.grid(row=current_row, column=0, padx=20, pady=(5, 1), sticky="w")
            
            if key == "address":
                entry = ctk.CTkTextbox(self.form_scroll, height=60, fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR, border_width=1, text_color=Theme.TEXT_MAIN)
            else:
                entry = ctk.CTkEntry(self.form_scroll, fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR, border_width=1, text_color=Theme.TEXT_MAIN)
                
            entry.grid(row=current_row+1, column=0, padx=20, pady=(0, 8), sticky="ew")
            self.fields[key] = entry
            current_row += 2
            
        # Display Outstanding Credit Balance
        self.lbl_outstanding_title = ctk.CTkLabel(self.form_scroll, text="Current Outstanding Balance (Dues)", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        self.lbl_outstanding_title.grid(row=current_row, column=0, padx=20, pady=(5, 1), sticky="w")
        self.lbl_outstanding_v = ctk.CTkLabel(self.form_scroll, text="₹0.00", font=ctk.CTkFont(size=16, weight="bold"), text_color=Theme.SUCCESS)
        self.lbl_outstanding_v.grid(row=current_row+1, column=0, padx=20, pady=(0, 10), sticky="w")
        current_row += 2
        
        # Action Buttons
        self.btn_frame = ctk.CTkFrame(self.form_scroll, fg_color="transparent")
        self.btn_frame.grid(row=current_row, column=0, padx=20, pady=15, sticky="ew")
        self.btn_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.save_btn = PrimaryButton(self.btn_frame, text="💾 Save Customer", command=self.save_customer)
        self.save_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.clear_btn = ctk.CTkButton(self.btn_frame, text="🧹 Clear Form", fg_color=Theme.BORDER_COLOR, hover_color=Theme.BG_WINDOW, text_color=Theme.TEXT_LIGHT, command=self.clear_form)
        self.clear_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.delete_btn = DangerButton(self.form_scroll, text="🗑️ Deactivate Customer", command=self.delete_customer)
        self.delete_btn.grid(row=current_row+1, column=0, padx=25, pady=(0, 15), sticky="ew")
        self.delete_btn.grid_remove()
        
        # Ledger frame
        self.ledger_frame = ctk.CTkFrame(self.tab_ledger, fg_color="transparent")
        self.ledger_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.lbl_ledger_title = ctk.CTkLabel(self.ledger_frame, text="Select a customer to view transaction ledgers.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
        self.lbl_ledger_title.pack(pady=20)
        
    def refresh(self):
        self.all_customers = get_all_customers(include_inactive=True)
        self.populate_list(self.all_customers)
        self.clear_form()
        
    def populate_list(self, customers):
        for child in self.list_scroll.winfo_children():
            child.destroy()
            
        if not customers:
            lbl_empty = ctk.CTkLabel(self.list_scroll, text="No customers found.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
            lbl_empty.pack(pady=20)
            return
            
        for customer in customers:
            is_selected = self.selected_customer_id == customer['id']
            bg_color = Theme.PRIMARY if is_selected else Theme.BG_PANEL
            border_color = Theme.PRIMARY_HOVER if is_selected else Theme.BORDER_COLOR
            
            is_active = customer.get('status', 'Active') == 'Active'
            opacity_text = Theme.TEXT_MAIN if is_active else Theme.TEXT_MUTED
            
            frame = ctk.CTkFrame(self.list_scroll, fg_color=bg_color, border_color=border_color, border_width=1, corner_radius=5, cursor="hand2")
            frame.pack(fill="x", pady=4, padx=5)
            
            # Outstanding dues color indicator stripe
            due = customer.get('outstanding_balance', 0.0)
            stripe_color = Theme.DANGER if due > 0 else Theme.SUCCESS
            stripe = ctk.CTkFrame(frame, width=4, fg_color=stripe_color, corner_radius=0)
            stripe.pack(side="left", fill="y")
            
            info_frame = ctk.CTkFrame(frame, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)
            
            name_text = customer['name'] if is_active else f"{customer['name']} (DEACTIVATED)"
            name_lbl = ctk.CTkLabel(info_frame, text=name_text, font=ctk.CTkFont(size=13, weight="bold"), text_color=opacity_text, anchor="w")
            name_lbl.pack(fill="x", pady=(2, 1))
            
            phone_val = customer['phone'] if customer['phone'] else "N/A"
            gst_val = customer['gst_number'] if customer['gst_number'] else "No GSTIN"
            meta_lbl = ctk.CTkLabel(info_frame, text=f"📞 {phone_val}  |  🏷️ {gst_val}", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED, anchor="w")
            meta_lbl.pack(fill="x", pady=(0, 2))
            
            # Balance Tag on right
            bal_lbl = ctk.CTkLabel(frame, text=f"₹{due:.2f}", font=ctk.CTkFont(size=13, weight="bold"), text_color=stripe_color)
            bal_lbl.pack(side="right", padx=15)
            
            # Binding clicks
            for widget in [frame, info_frame, name_lbl, meta_lbl, bal_lbl]:
                widget.bind("<Button-1>", lambda event, c=customer: self.load_customer_to_form(c))

    def load_customer_to_form(self, customer):
        self.selected_customer_id = customer['id']
        self.title_right.configure(text=f"Edit: {customer['name']}", text_color=Theme.SECONDARY)
        self.save_btn.configure(text="Update Customer", fg_color=Theme.SECONDARY, hover_color=Theme.SECONDARY_HOVER)
        
        # Populate
        self.fields['name'].delete(0, "end")
        self.fields['name'].insert(0, customer['name'])
        
        self.fields['phone'].delete(0, "end")
        self.fields['phone'].insert(0, customer['phone'] or "")
        
        self.fields['email'].delete(0, "end")
        self.fields['email'].insert(0, customer['email'] or "")
        
        self.fields['gst_number'].delete(0, "end")
        self.fields['gst_number'].insert(0, customer['gst_number'] or "")
        
        self.fields['credit_limit'].delete(0, "end")
        self.fields['credit_limit'].insert(0, str(customer['credit_limit']))
        
        self.fields['address'].delete("1.0", "end")
        self.fields['address'].insert("1.0", customer['address'] or "")
        
        self.lbl_outstanding_v.configure(
            text=f"₹{customer['outstanding_balance']:.2f}",
            text_color=Theme.DANGER if customer['outstanding_balance'] > 0 else Theme.SUCCESS
        )
        
        if customer['status'] == 'Active':
            self.delete_btn.configure(text="🗑️ Deactivate Customer", fg_color=Theme.DANGER)
            self.delete_btn.grid()
        else:
            self.delete_btn.configure(text="🔄 Reactivate Customer", fg_color=Theme.SUCCESS)
            self.delete_btn.grid()
            
        self.populate_list(self.all_customers)
        self.show_customer_ledger(customer)

    def clear_form(self):
        self.selected_customer_id = None
        self.title_right.configure(text="Add New Customer", text_color=Theme.PRIMARY)
        self.save_btn.configure(text="Save Customer", fg_color=Theme.SUCCESS, hover_color=Theme.SUCCESS_HOVER)
        
        for k in ['name', 'phone', 'email', 'gst_number', 'credit_limit']:
            self.fields[k].delete(0, "end")
            
        self.fields['credit_limit'].insert(0, "5000.00")
        self.fields['address'].delete("1.0", "end")
        self.lbl_outstanding_v.configure(text="₹0.00", text_color=Theme.SUCCESS)
        self.delete_btn.grid_remove()
        
        for child in self.ledger_frame.winfo_children():
            child.destroy()
        self.lbl_ledger_title = ctk.CTkLabel(self.ledger_frame, text="Select a customer to view transaction ledgers.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
        self.lbl_ledger_title.pack(pady=20)

    def on_search(self, event=None):
        query = self.search_entry.get().strip().lower()
        if not query:
            self.populate_list(self.all_customers)
            return
        filtered = [c for c in self.all_customers if query in c['name'].lower()]
        self.populate_list(filtered)

    def save_customer(self):
        name = self.fields['name'].get().strip()
        phone = self.fields['phone'].get().strip()
        email = self.fields['email'].get().strip()
        gst = self.fields['gst_number'].get().strip()
        address = self.fields['address'].get("1.0", "end").strip()
        
        if not name:
            messagebox.showerror("Validation Error", "Customer Name is required.")
            return
            
        try:
            limit = float(self.fields['credit_limit'].get().strip() or 5000.0)
        except ValueError:
            messagebox.showerror("Error", "Credit Limit must be a valid number.")
            return
            
        try:
            if self.selected_customer_id:
                cust = get_customer_by_id(self.selected_customer_id)
                update_customer(
                    customer_id=self.selected_customer_id,
                    name=name,
                    phone=phone,
                    email=email,
                    address=address,
                    gst_number=gst,
                    credit_limit=limit,
                    status=cust['status']
                )
                messagebox.showinfo("Success", "Customer updated.")
            else:
                add_customer(
                    name=name,
                    phone=phone,
                    email=email,
                    address=address,
                    gst_number=gst,
                    credit_limit=limit
                )
                messagebox.showinfo("Success", "Customer registered successfully.")
            self.refresh()
        except Exception as ex:
            messagebox.showerror("Database Error", str(ex))

    def delete_customer(self):
        if not self.selected_customer_id:
            return
        cust = get_customer_by_id(self.selected_customer_id)
        if cust['status'] == 'Active':
            confirm = messagebox.askyesno("Confirm Deactivation", "Are you sure you want to deactivate this customer?")
            if confirm:
                delete_customer(self.selected_customer_id)
                messagebox.showinfo("Success", "Customer deactivated.")
                self.refresh()
        else:
            update_customer(
                customer_id=self.selected_customer_id,
                name=cust['name'],
                phone=cust['phone'],
                email=cust['email'],
                address=cust['address'],
                gst_number=cust['gst_number'],
                credit_limit=cust['credit_limit'],
                status='Active'
            )
            messagebox.showinfo("Success", "Customer reactivated successfully.")
            self.refresh()

    def show_customer_ledger(self, customer):
        for child in self.ledger_frame.winfo_children():
            child.destroy()
            
        header = ctk.CTkLabel(self.ledger_frame, text=f"Ledger: {customer['name']}", font=ctk.CTkFont(size=14, weight="bold"), text_color=Theme.PRIMARY)
        header.pack(anchor="w", pady=(0, 10))
        
        # Table Headers
        t_header = ctk.CTkFrame(self.ledger_frame, fg_color=Theme.BG_PANEL, height=30, corner_radius=3)
        t_header.pack(fill="x", pady=2)
        t_header.grid_propagate(False)
        t_header.grid_rowconfigure(0, weight=1)
        
        cols = ["Date", "Type", "Ref Bill", "Debit (+)", "Credit (-)", "Balance"]
        w = [0.20, 0.15, 0.15, 0.15, 0.15, 0.20]
        for idx, (c_name, weight) in enumerate(zip(cols, w)):
            t_header.grid_columnconfigure(idx, weight=int(weight * 100))
            lbl = ctk.CTkLabel(t_header, text=c_name, font=ctk.CTkFont(size=10, weight="bold"), text_color=Theme.TEXT_LIGHT)
            lbl.grid(row=0, column=idx, padx=5, sticky="w" if idx == 0 else "")
            
        scroll = ctk.CTkScrollableFrame(self.ledger_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        scroll.grid_columnconfigure(0, weight=1)
        
        logs = get_customer_ledger(customer['id'])
        if not logs:
            lbl_no = ctk.CTkLabel(scroll, text="No ledger entries for this customer.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
            lbl_no.pack(pady=30)
            return
            
        for idx, log in enumerate(logs):
            bg = Theme.BG_WINDOW if idx % 2 == 0 else Theme.BG_PANEL
            r = ctk.CTkFrame(scroll, fg_color=bg, height=35, corner_radius=3)
            r.pack(fill="x", pady=1)
            r.grid_propagate(False)
            r.grid_rowconfigure(0, weight=1)
            
            # Debit increases outstanding balance, credit (payments) decreases it
            vals = [
                log['date'][:10],
                log['type'],
                log['reference_id'] or 'N/A',
                f"₹{log['debit']:.2f}" if log['debit'] > 0 else "-",
                f"₹{log['credit']:.2f}" if log['credit'] > 0 else "-",
                f"₹{log['balance']:.2f}"
            ]
            
            for c_idx, (v, weight) in enumerate(zip(vals, w)):
                r.grid_columnconfigure(c_idx, weight=int(weight * 100))
                
                t_color = Theme.TEXT_MAIN
                if c_idx == 3 and log['debit'] > 0:
                    t_color = Theme.DANGER
                elif c_idx == 4 and log['credit'] > 0:
                    t_color = Theme.SUCCESS
                    
                lbl = ctk.CTkLabel(r, text=v, font=ctk.CTkFont(size=10), text_color=t_color, anchor="w" if c_idx == 0 else "center")
                lbl.grid(row=0, column=c_idx, padx=5, sticky="ew" if c_idx == 0 else "")
