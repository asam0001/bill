import customtkinter as ctk
from ui.theme import Theme

class PageHeader(ctk.CTkFrame):
    def __init__(self, parent, title_text, search_placeholder=None, on_search_callback=None, right_widget_cls=None, right_widget_args=None):
        super().__init__(parent, fg_color="transparent")
        
        self.pack(fill="x", padx=20, pady=(15, 10))
        
        # Left Side Title
        self.title_label = ctk.CTkLabel(self, text=title_text, font=ctk.CTkFont(size=24, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.title_label.pack(side="left")
        
        # Right Side Search or Action Widget
        if search_placeholder and on_search_callback:
            self.search_entry = ctk.CTkEntry(self, placeholder_text=search_placeholder, width=300, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, text_color=Theme.TEXT_MAIN)
            self.search_entry.pack(side="right", padx=(10, 0))
            self.search_entry.bind("<KeyRelease>", on_search_callback)
            self.search_entry_ref = self.search_entry
            
        if right_widget_cls:
            args = right_widget_args or {}
            self.right_widget = right_widget_cls(self, **args)
            self.right_widget.pack(side="right", padx=(10, 0))

class StatCard(ctk.CTkFrame):
    def __init__(self, parent, title, value, color_accent=Theme.PRIMARY, icon="📈"):
        super().__init__(parent, fg_color=Theme.BG_CARD, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=10, height=85)
        
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        
        # Top-left title
        self.lbl_title = ctk.CTkLabel(self, text=title.upper(), font=ctk.CTkFont(size=10, weight="bold"), text_color=Theme.TEXT_MUTED)
        self.lbl_title.grid(row=0, column=0, padx=15, pady=(12, 2), sticky="w")
        
        # Bottom-left value
        self.lbl_value = ctk.CTkLabel(self, text=value, font=ctk.CTkFont(size=20, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.lbl_value.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="w")
        
        # Right icon/accent pill
        self.lbl_icon = ctk.CTkLabel(self, text=icon, font=ctk.CTkFont(size=22))
        self.lbl_icon.place(relx=0.85, rely=0.5, anchor="center")
        
        # Thin colored bar on the left edge
        self.accent_bar = ctk.CTkFrame(self, width=4, fg_color=color_accent, corner_radius=0)
        self.accent_bar.place(x=0, y=0, relheight=1.0)
        
    def update_value(self, new_val):
        self.lbl_value.configure(text=str(new_val))

class DataTable(ctk.CTkScrollableFrame):
    def __init__(self, parent, headers_with_weights):
        # headers_with_weights list of tuples: [("Name", 0.4), ("Phone", 0.3), ...]
        super().__init__(parent, fg_color="transparent")
        self.headers_with_weights = headers_with_weights
        
        self.grid_columnconfigure(0, weight=1)
        self.row_index = 0
        
    def clear(self):
        for child in self.winfo_children():
            child.destroy()
        self.row_index = 0
        
    def add_row(self, col_values, border_accent=None, actions=None):
        # col_values: list of strings/widgets matching column headers length
        # actions: list of dicts [{'text': '✏️', 'command': cmd, 'fg': color}, ...]
        row_bg = Theme.BG_WINDOW if self.row_index % 2 == 0 else Theme.BG_PANEL
        
        row_frame = ctk.CTkFrame(self, fg_color=row_bg, border_color=border_accent or Theme.BORDER_COLOR, border_width=1 if border_accent else 0, height=45, corner_radius=5)
        row_frame.pack(fill="x", pady=3, padx=2)
        row_frame.grid_propagate(False)
        row_frame.grid_rowconfigure(0, weight=1)
        
        # Accent indicator
        if border_accent:
            accent_bar = ctk.CTkFrame(row_frame, width=4, fg_color=border_accent, corner_radius=0)
            accent_bar.place(x=0, y=0, relheight=1.0)
            
        # Add values
        c_col = 0
        for val_idx, (header_text, weight) in enumerate(self.headers_with_weights):
            col_weight = int(weight * 100)
            row_frame.grid_columnconfigure(c_col, weight=col_weight)
            
            # Last column reserved for actions if actions list is present and column header is 'Action'
            if header_text == "Action" and actions:
                act_container = ctk.CTkFrame(row_frame, fg_color="transparent")
                act_container.grid(row=0, column=c_col, sticky="")
                for btn_info in actions:
                    btn = ctk.CTkButton(
                        act_container, 
                        text=btn_info['text'], 
                        width=btn_info.get('width', 26), 
                        height=26, 
                        fg_color=btn_info.get('fg', Theme.SECONDARY), 
                        hover_color=btn_info.get('hover', Theme.SECONDARY_HOVER),
                        command=btn_info['command']
                    )
                    btn.pack(side="left", padx=2)
            else:
                # Standard column
                val = col_values[val_idx] if val_idx < len(col_values) else ""
                
                if isinstance(val, ctk.CTkLabel):
                    val.master = row_frame
                    val.grid(row=0, column=c_col, padx=10, sticky="w" if c_col == 0 else "")
                else:
                    lbl = ctk.CTkLabel(row_frame, text=str(val), font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MAIN, anchor="w" if c_col == 0 else "center")
                    lbl.grid(row=0, column=c_col, padx=10, sticky="ew" if c_col == 0 else "")
            c_col += 1
            
        self.row_index += 1
        return row_frame

class PrimaryButton(ctk.CTkButton):
    def __init__(self, parent, **kwargs):
        kwargs.setdefault('fg_color', Theme.PRIMARY)
        kwargs.setdefault('hover_color', Theme.PRIMARY_HOVER)
        kwargs.setdefault('text_color', 'white')
        kwargs.setdefault('height', 35)
        super().__init__(parent, **kwargs)

class SecondaryButton(ctk.CTkButton):
    def __init__(self, parent, **kwargs):
        kwargs.setdefault('fg_color', Theme.SECONDARY)
        kwargs.setdefault('hover_color', Theme.SECONDARY_HOVER)
        kwargs.setdefault('text_color', 'white')
        kwargs.setdefault('height', 35)
        super().__init__(parent, **kwargs)

class DangerButton(ctk.CTkButton):
    def __init__(self, parent, **kwargs):
        kwargs.setdefault('fg_color', Theme.DANGER)
        kwargs.setdefault('hover_color', Theme.DANGER_HOVER)
        kwargs.setdefault('text_color', 'white')
        kwargs.setdefault('height', 35)
        super().__init__(parent, **kwargs)
