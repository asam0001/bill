import customtkinter as ctk
from tkinter import messagebox
from utils.supplier_service import (
    get_all_suppliers, add_supplier, update_supplier, delete_supplier, get_supplier_ledger
)
from ui.theme import Theme
from ui.components import PrimaryButton, SecondaryButton, DangerButton

class SuppliersFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(fg_color=Theme.BG_WINDOW)
        
        self.selected_supplier_id = None
        self.all_suppliers = []
        
        # Configure layout (2 columns: Directory and Manage/Ledger Panel)
        self.grid_columnconfigure(0, weight=3) # 45% width
        self.grid_columnconfigure(1, weight=4) # 55% width
        self.grid_rowconfigure(0, weight=1)
        
        # 1. Left Side: Directory
        self.directory_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.directory_frame.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="nsew")
        self.directory_frame.grid_columnconfigure(0, weight=1)
        self.directory_frame.grid_rowconfigure(2, weight=1)
        
        self.title_left = ctk.CTkLabel(self.directory_frame, text="Supplier Directory", font=ctk.CTkFont(size=20, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.title_left.grid(row=0, column=0, pady=(0, 10), sticky="w")
        
        # Search Bar
        self.search_entry = ctk.CTkEntry(self.directory_frame, placeholder_text="Search suppliers by name...", fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, text_color=Theme.TEXT_MAIN)
        self.search_entry.grid(row=1, column=0, pady=(0, 10), sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.on_search)
        
        # Supplier List
        self.list_scroll = ctk.CTkScrollableFrame(self.directory_frame, fg_color="transparent")
        self.list_scroll.grid(row=2, column=0, sticky="nsew")
        
        # 2. Right Side: Tabview (Profile Form & Ledger History)
        self.right_tabview = ctk.CTkTabview(self, fg_color=Theme.BG_PANEL, segmented_button_selected_color=Theme.PRIMARY, segmented_button_selected_hover_color=Theme.PRIMARY_HOVER, text_color=Theme.TEXT_MAIN)
        self.right_tabview.grid(row=0, column=1, padx=(10, 15), pady=15, sticky="nsew")
        
        self.tab_form = self.right_tabview.add("Profile Form")
        self.tab_ledger = self.right_tabview.add("Supplier Ledger")
        
        # Setup form fields inside Scrollable Frame for Profile Form to handle smaller resolutions cleanly
        self.form_scroll = ctk.CTkScrollableFrame(self.tab_form, fg_color="transparent")
        self.form_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        self.form_scroll.grid_columnconfigure(0, weight=1)
        
        self.title_right = ctk.CTkLabel(self.form_scroll, text="Add New Supplier", font=ctk.CTkFont(size=18, weight="bold"), text_color=Theme.PRIMARY)
        self.title_right.grid(row=0, column=0, padx=20, pady=(10, 10), sticky="w")
        
        # Form inputs dictionary
        self.fields = {}
        form_labels = [
            ("Supplier Name *", "name"),
            ("Contact Person", "contact_person"),
            ("Phone Number", "phone"),
            ("Email Address", "email"),
            ("GSTIN / Tax No", "gst_number"),
            ("Payment Terms (e.g. Net 30)", "payment_terms"),
            ("Opening Balance (₹)", "opening_balance"),
            ("Business Address", "address")
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
            
        # Display Current Balance (Read-only status card inside form)
        self.lbl_curr_bal_title = ctk.CTkLabel(self.form_scroll, text="Current Credit Balance (Owed Amount)", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_LIGHT)
        self.lbl_curr_bal_title.grid(row=current_row, column=0, padx=20, pady=(5, 1), sticky="w")
        self.lbl_curr_bal_v = ctk.CTkLabel(self.form_scroll, text="₹0.00", font=ctk.CTkFont(size=16, weight="bold"), text_color=Theme.SUCCESS)
        self.lbl_curr_bal_v.grid(row=current_row+1, column=0, padx=20, pady=(0, 10), sticky="w")
        current_row += 2
        
        # Action Buttons
        self.btn_frame = ctk.CTkFrame(self.form_scroll, fg_color="transparent")
        self.btn_frame.grid(row=current_row, column=0, padx=20, pady=15, sticky="ew")
        self.btn_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.save_btn = PrimaryButton(self.btn_frame, text="💾 Save Supplier", command=self.save_supplier)
        self.save_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.clear_btn = ctk.CTkButton(self.btn_frame, text="🧹 Clear", fg_color=Theme.BORDER_COLOR, hover_color=Theme.BG_WINDOW, text_color=Theme.TEXT_LIGHT, command=self.clear_form)
        self.clear_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.delete_btn = DangerButton(self.form_scroll, text="🗑️ Deactivate Supplier", command=self.delete_supplier)
        self.delete_btn.grid(row=current_row+1, column=0, padx=25, pady=(0, 15), sticky="ew")
        self.delete_btn.grid_remove() # Hide initially
        
        # Setup Ledger History inside Ledger Tab
        self.ledger_frame = ctk.CTkFrame(self.tab_ledger, fg_color="transparent")
        self.ledger_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.lbl_ledger_title = ctk.CTkLabel(self.ledger_frame, text="Select a supplier to view ledger history.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
        self.lbl_ledger_title.pack(pady=20)
        
    def refresh(self):
        self.all_suppliers = get_all_suppliers(include_inactive=True)
        self.populate_list(self.all_suppliers)
        self.clear_form()
        
    def populate_list(self, suppliers):
        for child in self.list_scroll.winfo_children():
            child.destroy()
            
        if not suppliers:
            lbl_empty = ctk.CTkLabel(self.list_scroll, text="No suppliers found.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
            lbl_empty.pack(pady=20)
            return
            
        for supplier in suppliers:
            is_selected = self.selected_supplier_id == supplier['id']
            bg_color = Theme.PRIMARY if is_selected else Theme.BG_PANEL
            border_color = Theme.PRIMARY_HOVER if is_selected else Theme.BORDER_COLOR
            
            # Deactivated suppliers shown faded
            is_active = supplier.get('status', 'Active') == 'Active'
            opacity_text = Theme.TEXT_MAIN if is_active else Theme.TEXT_MUTED
            
            frame = ctk.CTkFrame(self.list_scroll, fg_color=bg_color, border_color=border_color, border_width=1, corner_radius=5, cursor="hand2")
            frame.pack(fill="x", pady=4, padx=5)
            
            # Left stripe colored red/green depending on balance
            bal = supplier.get('current_balance', 0.0)
            stripe_color = Theme.DANGER if bal > 0 else Theme.SUCCESS
            stripe = ctk.CTkFrame(frame, width=4, fg_color=stripe_color, corner_radius=0)
            stripe.pack(side="left", fill="y")
            
            # Content layout
            info_frame = ctk.CTkFrame(frame, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)
            
            name_text = supplier['name'] if is_active else f"{supplier['name']} (DEACTIVATED)"
            name_lbl = ctk.CTkLabel(info_frame, text=name_text, font=ctk.CTkFont(size=13, weight="bold"), text_color=opacity_text, anchor="w")
            name_lbl.pack(fill="x", pady=(2, 1))
            
            phone_val = supplier['phone'] if supplier['phone'] else "N/A"
            gst_val = supplier['gst_number'] if supplier['gst_number'] else "No GSTIN"
            meta_lbl = ctk.CTkLabel(info_frame, text=f"📞 {phone_val}  |  🏷️ {gst_val}", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED, anchor="w")
            meta_lbl.pack(fill="x", pady=(0, 2))
            
            # Balance Tag on right
            bal_lbl = ctk.CTkLabel(frame, text=f"₹{bal:.2f}", font=ctk.CTkFont(size=13, weight="bold"), text_color=stripe_color)
            bal_lbl.pack(side="right", padx=15)
            
            # Clicks
            for widget in [frame, info_frame, name_lbl, meta_lbl, bal_lbl]:
                widget.bind("<Button-1>", lambda event, s=supplier: self.load_supplier_to_form(s))

    def load_supplier_to_form(self, supplier):
        self.selected_supplier_id = supplier['id']
        self.title_right.configure(text=f"Edit: {supplier['name']}", text_color=Theme.SECONDARY)
        self.save_btn.configure(text="Update Details", fg_color=Theme.SECONDARY, hover_color=Theme.SECONDARY_HOVER)
        
        # Populate
        self.fields['name'].delete(0, "end")
        self.fields['name'].insert(0, supplier['name'])
        
        self.fields['contact_person'].delete(0, "end")
        self.fields['contact_person'].insert(0, supplier['contact_person'] or "")
        
        self.fields['phone'].delete(0, "end")
        self.fields['phone'].insert(0, supplier['phone'] or "")
        
        self.fields['email'].delete(0, "end")
        self.fields['email'].insert(0, supplier['email'] or "")
        
        self.fields['gst_number'].delete(0, "end")
        self.fields['gst_number'].insert(0, supplier['gst_number'] or "")
        
        self.fields['payment_terms'].delete(0, "end")
        self.fields['payment_terms'].insert(0, supplier['payment_terms'] or "Net 30")
        
        self.fields['opening_balance'].delete(0, "end")
        self.fields['opening_balance'].insert(0, str(supplier['opening_balance']))
        self.fields['opening_balance'].configure(state="disabled") # Cannot edit opening balance directly
        
        self.fields['address'].delete("1.0", "end")
        self.fields['address'].insert("1.0", supplier['address'] or "")
        
        self.lbl_curr_bal_v.configure(
            text=f"₹{supplier['current_balance']:.2f}",
            text_color=Theme.DANGER if supplier['current_balance'] > 0 else Theme.SUCCESS
        )
        
        if supplier['status'] == 'Active':
            self.delete_btn.configure(text="🗑️ Deactivate Supplier", fg_color=Theme.DANGER)
            self.delete_btn.grid()
        else:
            self.delete_btn.configure(text="🔄 Reactivate Supplier", fg_color=Theme.SUCCESS)
            self.delete_btn.grid()
            
        self.populate_list(self.all_suppliers)
        
        # Show Ledger
        self.show_supplier_ledger(supplier)

    def clear_form(self):
        self.selected_supplier_id = None
        self.title_right.configure(text="Add New Supplier", text_color=Theme.PRIMARY)
        self.save_btn.configure(text="Save Supplier", fg_color=Theme.SUCCESS, hover_color=Theme.SUCCESS_HOVER)
        
        for k in ['name', 'contact_person', 'phone', 'email', 'gst_number', 'payment_terms', 'opening_balance']:
            self.fields[k].configure(state="normal")
            self.fields[k].delete(0, "end")
            
        self.fields['opening_balance'].insert(0, "0.00")
        self.fields['payment_terms'].insert(0, "Net 30")
        self.fields['address'].delete("1.0", "end")
        self.lbl_curr_bal_v.configure(text="₹0.00", text_color=Theme.SUCCESS)
        
        self.delete_btn.grid_remove()
        
        # Reset ledger tab text
        for child in self.ledger_frame.winfo_children():
            child.destroy()
        self.lbl_ledger_title = ctk.CTkLabel(self.ledger_frame, text="Select a supplier to view ledger history.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
        self.lbl_ledger_title.pack(pady=20)

    def on_search(self, event=None):
        query = self.search_entry.get().strip().lower()
        if not query:
            self.populate_list(self.all_suppliers)
            return
        filtered = [s for s in self.all_suppliers if query in s['name'].lower()]
        self.populate_list(filtered)

    def save_supplier(self):
        name = self.fields['name'].get().strip()
        person = self.fields['contact_person'].get().strip()
        phone = self.fields['phone'].get().strip()
        email = self.fields['email'].get().strip()
        gst = self.fields['gst_number'].get().strip()
        terms = self.fields['payment_terms'].get().strip()
        address = self.fields['address'].get("1.0", "end").strip()
        
        if not name:
            messagebox.showerror("Validation Error", "Supplier Name is required.")
            return
            
        try:
            if self.selected_supplier_id:
                # Update (retrieve existing record first to keep status)
                supp = get_supplier_by_id(self.selected_supplier_id)
                update_supplier(
                    supplier_id=self.selected_supplier_id,
                    name=name,
                    phone=phone,
                    email=email,
                    address=address,
                    contact_person=person,
                    gst_number=gst,
                    payment_terms=terms,
                    status=supp['status']
                )
                messagebox.showinfo("Success", "Supplier info updated.")
            else:
                # Insert
                try:
                    op_bal = float(self.fields['opening_balance'].get().strip() or 0.0)
                except ValueError:
                    messagebox.showerror("Error", "Opening Balance must be a number.")
                    return
                add_supplier(
                    name=name,
                    phone=phone,
                    email=email,
                    address=address,
                    contact_person=person,
                    gst_number=gst,
                    payment_terms=terms,
                    opening_balance=op_bal
                )
                messagebox.showinfo("Success", "Supplier registered.")
            self.refresh()
        except Exception as ex:
            messagebox.showerror("Database Error", str(ex))

    def delete_supplier(self):
        if not self.selected_supplier_id:
            return
        supp = get_supplier_by_id(self.selected_supplier_id)
        if supp['status'] == 'Active':
            confirm = messagebox.askyesno("Confirm Deactivation", "Are you sure you want to deactivate this supplier?")
            if confirm:
                delete_supplier(self.selected_supplier_id)
                messagebox.showinfo("Success", "Supplier marked Inactive.")
                self.refresh()
        else:
            # Reactivate
            update_supplier(
                supplier_id=self.selected_supplier_id,
                name=supp['name'],
                phone=supp['phone'],
                email=supp['email'],
                address=supp['address'],
                contact_person=supp['contact_person'],
                gst_number=supp['gst_number'],
                payment_terms=supp['payment_terms'],
                status='Active'
            )
            messagebox.showinfo("Success", "Supplier reactivated successfully.")
            self.refresh()

    def show_supplier_ledger(self, supplier):
        for child in self.ledger_frame.winfo_children():
            child.destroy()
            
        header = ctk.CTkLabel(self.ledger_frame, text=f"Ledger: {supplier['name']}", font=ctk.CTkFont(size=14, weight="bold"), text_color=Theme.PRIMARY)
        header.pack(anchor="w", pady=(0, 10))
        
        # Table Headers
        t_header = ctk.CTkFrame(self.ledger_frame, fg_color=Theme.BG_PANEL, height=30, corner_radius=3)
        t_header.pack(fill="x", pady=2)
        t_header.grid_propagate(False)
        t_header.grid_rowconfigure(0, weight=1)
        
        cols = ["Date", "Type", "Ref", "Debit (-)", "Credit (+)", "Balance"]
        w = [0.20, 0.15, 0.15, 0.15, 0.15, 0.20]
        for idx, (c_name, weight) in enumerate(zip(cols, w)):
            t_header.grid_columnconfigure(idx, weight=int(weight * 100))
            lbl = ctk.CTkLabel(t_header, text=c_name, font=ctk.CTkFont(size=10, weight="bold"), text_color=Theme.TEXT_LIGHT)
            lbl.grid(row=0, column=idx, padx=5, sticky="w" if idx == 0 else "")
            
        # Ledger rows scroll
        scroll = ctk.CTkScrollableFrame(self.ledger_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        scroll.grid_columnconfigure(0, weight=1)
        
        logs = get_supplier_ledger(supplier['id'])
        if not logs:
            lbl_no = ctk.CTkLabel(scroll, text="No ledger entries for this supplier.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED)
            lbl_no.pack(pady=30)
            return
            
        for idx, log in enumerate(logs):
            bg = Theme.BG_WINDOW if idx % 2 == 0 else Theme.BG_PANEL
            r = ctk.CTkFrame(scroll, fg_color=bg, height=35, corner_radius=3)
            r.pack(fill="x", pady=1)
            r.grid_propagate(False)
            r.grid_rowconfigure(0, weight=1)
            
            vals = [
                log['date'][:10], # Just date part
                log['type'],
                log['reference_id'] or 'N/A',
                f"₹{log['debit']:.2f}" if log['debit'] > 0 else "-",
                f"₹{log['credit']:.2f}" if log['credit'] > 0 else "-",
                f"₹{log['balance']:.2f}"
            ]
            
            for c_idx, (v, weight) in enumerate(zip(vals, w)):
                r.grid_columnconfigure(c_idx, weight=int(weight * 100))
                
                # Colors
                t_color = Theme.TEXT_MAIN
                if c_idx == 3 and log['debit'] > 0:
                    t_color = Theme.SUCCESS
                elif c_idx == 4 and log['credit'] > 0:
                    t_color = Theme.DANGER
                    
                lbl = ctk.CTkLabel(r, text=v, font=ctk.CTkFont(size=10), text_color=t_color, anchor="w" if c_idx == 0 else "center")
                lbl.grid(row=0, column=c_idx, padx=5, sticky="ew" if c_idx == 0 else "")
