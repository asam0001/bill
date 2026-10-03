import os
import subprocess
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime

# Matplotlib integration
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from utils.sales_service import get_report_sales_data, get_report_top_sold, get_report_top_profitable
from utils.pdf_service import generate_report_pdf, generate_report_excel
from ui.theme import Theme

class ReportsFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(fg_color=Theme.BG_WINDOW)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Current active filter
        self.active_filter = "weekly" # Default
        
        # 1. Header Area
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="Sales & Analytics Reports", font=ctk.CTkFont(size=24, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.title_label.pack(side="left")
        
        # Export Buttons
        self.export_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.export_frame.pack(side="right")
        
        self.btn_export_pdf = ctk.CTkButton(self.export_frame, text="📄 Export PDF", width=100, fg_color=Theme.DANGER, hover_color=Theme.DANGER_HOVER, text_color="white", command=self.export_pdf)
        self.btn_export_pdf.pack(side="right", padx=5)
        
        self.btn_export_excel = ctk.CTkButton(self.export_frame, text="📊 Export Excel", width=110, fg_color=Theme.SUCCESS, hover_color=Theme.SUCCESS_HOVER, text_color="white", command=self.export_excel)
        self.btn_export_excel.pack(side="right", padx=5)
        
        # 2. Filters & Metrics Bar
        self.filters_bar = ctk.CTkFrame(self, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=10, height=80)
        self.filters_bar.grid(row=1, column=0, padx=20, pady=(5, 10), sticky="ew")
        self.filters_bar.grid_propagate(False)
        self.filters_bar.grid_rowconfigure(0, weight=1)
        self.filters_bar.grid_columnconfigure(0, weight=2) # Segmented buttons
        self.filters_bar.grid_columnconfigure((1, 2), weight=3) # Key Indicators
        
        # Segmented Button
        self.filter_buttons = ctk.CTkSegmentedButton(
            self.filters_bar, 
            values=["Daily", "Weekly", "Monthly", "Yearly"],
            command=self.on_filter_change,
            height=35,
            selected_color=Theme.PRIMARY,
            selected_hover_color=Theme.PRIMARY_HOVER
        )
        self.filter_buttons.grid(row=0, column=0, padx=15, pady=20, sticky="w")
        self.filter_buttons.set("Weekly")
        
        # Revenue Metric
        self.rev_metric = ctk.CTkFrame(self.filters_bar, fg_color="transparent")
        self.rev_metric.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        lbl_rev_t = ctk.CTkLabel(self.rev_metric, text="Total Revenue / Sales", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED)
        lbl_rev_t.pack(anchor="center", pady=(5, 2))
        self.lbl_rev_v = ctk.CTkLabel(self.rev_metric, text="₹0.00", font=ctk.CTkFont(size=20, weight="bold"), text_color=Theme.SECONDARY)
        self.lbl_rev_v.pack(anchor="center")
        
        # Profit Metric
        self.prof_metric = ctk.CTkFrame(self.filters_bar, fg_color="transparent")
        self.prof_metric.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        
        lbl_prof_t = ctk.CTkLabel(self.prof_metric, text="Net Profit / Margin", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED)
        lbl_prof_t.pack(anchor="center", pady=(5, 2))
        self.lbl_prof_v = ctk.CTkLabel(self.prof_metric, text="₹0.00", font=ctk.CTkFont(size=20, weight="bold"), text_color=Theme.SUCCESS)
        self.lbl_prof_v.pack(anchor="center")
        
        # 3. Main Split View (Left: Chart, Right: Top 10 Lists)
        self.main_split = ctk.CTkFrame(self, fg_color="transparent")
        self.main_split.grid(row=2, column=0, padx=20, pady=(5, 15), sticky="nsew")
        self.main_split.grid_columnconfigure(0, weight=5) # Chart (60% width)
        self.main_split.grid_columnconfigure(1, weight=4) # Top 10 Lists (40% width)
        self.main_split.grid_rowconfigure(0, weight=1)
        
        # Left Panel (Chart)
        self.chart_panel = ctk.CTkFrame(self.main_split, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=10)
        self.chart_panel.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        self.chart_panel.grid_columnconfigure(0, weight=1)
        self.chart_panel.grid_rowconfigure(1, weight=1)
        
        self.lbl_chart_title = ctk.CTkLabel(self.chart_panel, text="Sales & Profit Trend Line", font=ctk.CTkFont(size=14, weight="bold"), text_color=Theme.TEXT_MAIN)
        self.lbl_chart_title.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        
        self.chart_container = ctk.CTkFrame(self.chart_panel, fg_color="transparent")
        self.chart_container.grid(row=1, column=0, padx=15, pady=(5, 15), sticky="nsew")
        self.chart_container.grid_columnconfigure(0, weight=1)
        self.chart_container.grid_rowconfigure(0, weight=1)
        
        # Setup Matplotlib Figure
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots(figsize=(6, 3.5), facecolor=Theme.BG_PANEL)
        self.fig.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_container)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew")
        
        # Right Panel (Top 10 Lists)
        self.top_lists_panel = ctk.CTkFrame(self.main_split, fg_color="transparent")
        self.top_lists_panel.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        self.top_lists_panel.grid_columnconfigure(0, weight=1)
        self.top_lists_panel.grid_rowconfigure((0, 1), weight=1)
        
        # Top 10 Selling List Frame
        self.top_sold_frame = ctk.CTkFrame(self.top_lists_panel, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=10)
        self.top_sold_frame.grid(row=0, column=0, pady=(0, 10), sticky="nsew")
        self.top_sold_frame.grid_columnconfigure(0, weight=1)
        self.top_sold_frame.grid_rowconfigure(1, weight=1)
        
        self.lbl_ts_title = ctk.CTkLabel(self.top_sold_frame, text="Top 10 Selling Medicines", font=ctk.CTkFont(size=13, weight="bold"), text_color=Theme.SECONDARY)
        self.lbl_ts_title.grid(row=0, column=0, padx=15, pady=(12, 4), sticky="w")
        
        self.ts_scroll = ctk.CTkScrollableFrame(self.top_sold_frame, fg_color="transparent")
        self.ts_scroll.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        
        # Top 10 Profitable List Frame
        self.top_prof_frame = ctk.CTkFrame(self.top_lists_panel, fg_color=Theme.BG_PANEL, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=10)
        self.top_prof_frame.grid(row=1, column=0, pady=(10, 0), sticky="nsew")
        self.top_prof_frame.grid_columnconfigure(0, weight=1)
        self.top_prof_frame.grid_rowconfigure(1, weight=1)
        
        self.lbl_tp_title = ctk.CTkLabel(self.top_prof_frame, text="Top 10 Profitable Medicines", font=ctk.CTkFont(size=13, weight="bold"), text_color=Theme.SUCCESS)
        self.lbl_tp_title.grid(row=0, column=0, padx=15, pady=(12, 4), sticky="w")
        
        self.tp_scroll = ctk.CTkScrollableFrame(self.top_prof_frame, fg_color="transparent")
        self.tp_scroll.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        
        self.sales_data = []
        self.top_sold_data = []
        self.top_prof_data = []
        
    def refresh(self):
        self.on_filter_change(self.active_filter)
        
    def on_filter_change(self, value):
        self.active_filter = value.lower()
        
        # Retrieve report data
        self.sales_data = get_report_sales_data(self.active_filter)
        self.top_sold_data = get_report_top_sold(self.active_filter)
        self.top_prof_data = get_report_top_profitable(self.active_filter)
        
        # Compute metrics
        revenue_sum = sum(b['grand_total'] for b in self.sales_data)
        profit_sum = sum(b['total_profit'] for b in self.sales_data)
        
        # Update metrics labels
        self.lbl_rev_v.configure(text=f"₹{revenue_sum:.2f}")
        self.lbl_prof_v.configure(text=f"₹{profit_sum:.2f}")
        
        # Update Top 10 lists
        self.populate_top_lists()
        
        # Update Chart
        self.draw_chart()
        
    def populate_top_lists(self):
        # 1. Top Selling
        for child in self.ts_scroll.winfo_children():
            child.destroy()
            
        if not self.top_sold_data:
            ctk.CTkLabel(self.ts_scroll, text="No sales data found.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED).pack(pady=10)
        else:
            for idx, item in enumerate(self.top_sold_data, 1):
                f = ctk.CTkFrame(self.ts_scroll, fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=3)
                f.pack(fill="x", pady=2)
                
                name_batch = f"{idx}. {item['medicine_name']} (Batch: {item['batch']})"
                ctk.CTkLabel(f, text=name_batch, font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_MAIN, anchor="w").pack(side="left", padx=10, pady=5)
                ctk.CTkLabel(f, text=f"{item['total_sold']} tab", font=ctk.CTkFont(size=11), text_color=Theme.SECONDARY).pack(side="right", padx=10, pady=5)
                
        # 2. Top Profitable
        for child in self.tp_scroll.winfo_children():
            child.destroy()
            
        if not self.top_prof_data:
            ctk.CTkLabel(self.tp_scroll, text="No sales data found.", font=ctk.CTkFont(slant="italic"), text_color=Theme.TEXT_MUTED).pack(pady=10)
        else:
            for idx, item in enumerate(self.top_prof_data, 1):
                f = ctk.CTkFrame(self.tp_scroll, fg_color=Theme.BG_WINDOW, border_color=Theme.BORDER_COLOR, border_width=1, corner_radius=3)
                f.pack(fill="x", pady=2)
                
                name_batch = f"{idx}. {item['medicine_name']} (Batch: {item['batch']})"
                ctk.CTkLabel(f, text=name_batch, font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_MAIN, anchor="w").pack(side="left", padx=10, pady=5)
                ctk.CTkLabel(f, text=f"₹{item['total_profit']:.2f}", font=ctk.CTkFont(size=11), text_color=Theme.SUCCESS).pack(side="right", padx=10, pady=5)

    def draw_chart(self):
        self.ax.clear()
        
        if not self.sales_data:
            self.ax.text(0.5, 0.5, 'No transaction data to plot', horizontalalignment='center', verticalalignment='center', transform=self.ax.transAxes, color='gray')
            self.canvas.draw()
            return
            
        # Group sales data by date
        grouped_data = {}
        for bill in self.sales_data:
            # Extract date (YYYY-MM-DD)
            date_str = bill['date'].split()[0]
            if date_str not in grouped_data:
                grouped_data[date_str] = {'revenue': 0.0, 'profit': 0.0}
            grouped_data[date_str]['revenue'] += bill['grand_total']
            grouped_data[date_str]['profit'] += bill['total_profit']
            
        # Sort by date
        sorted_dates = sorted(grouped_data.keys())
        revenues = [grouped_data[d]['revenue'] for d in sorted_dates]
        profits = [grouped_data[d]['profit'] for d in sorted_dates]
        
        # Formatting X-axis dates for better labels readability
        short_dates = []
        for d in sorted_dates:
            try:
                # E.g. converts "2026-06-22" to "22 Jun"
                dt = datetime.strptime(d, "%Y-%m-%d")
                short_dates.append(dt.strftime("%d %b"))
            except ValueError:
                short_dates.append(d)
                
        # Draw plots
        self.ax.plot(short_dates, revenues, marker='o', color=Theme.SECONDARY, label='Revenue', linewidth=2)
        self.ax.plot(short_dates, profits, marker='s', color=Theme.SUCCESS, label='Profit', linewidth=2)
        
        self.ax.set_facecolor(Theme.BG_PANEL)
        self.ax.tick_params(colors='white', labelsize=8)
        
        # Rotate dates if too many
        if len(short_dates) > 5:
            plt.setp(self.ax.get_xticklabels(), rotation=30, horizontalalignment='right')
            
        self.ax.spines['bottom'].set_color(Theme.BORDER_COLOR)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_color(Theme.BORDER_COLOR)
        self.ax.grid(True, linestyle=':', alpha=0.3, color='gray')
        self.ax.legend(facecolor=Theme.BG_PANEL, edgecolor='none', labelcolor='white', fontsize=8)
        
        self.fig.tight_layout()
        self.canvas.draw()
        
    def export_pdf(self):
        if not self.sales_data:
            messagebox.showerror("Export Error", "No transaction data available to export.")
            return
            
        try:
            pdf_path = generate_report_pdf(self.active_filter, self.sales_data, self.top_sold_data, self.top_prof_data)
            self.show_export_success(pdf_path)
        except Exception as ex:
            messagebox.showerror("Export Failed", str(ex))
            
    def export_excel(self):
        if not self.sales_data:
            messagebox.showerror("Export Error", "No transaction data available to export.")
            return
            
        try:
            excel_path = generate_report_excel(self.active_filter, self.sales_data, self.top_sold_data, self.top_prof_data)
            self.show_export_success(excel_path)
        except Exception as ex:
            messagebox.showerror("Export Failed", str(ex))
            
    def show_export_success(self, path):
        confirm = messagebox.askyesno("Export Successful", f"Report successfully saved to:\n{path}\n\nWould you like to open it now?")
        if confirm and os.path.exists(path):
            try:
                if os.name == 'nt':
                    os.startfile(path)
                elif os.name == 'posix':
                    subprocess.run(['open', path])
            except Exception:
                pass
