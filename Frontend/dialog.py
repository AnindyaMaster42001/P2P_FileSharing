import tkinter as tk
from tkinter import ttk
import logging
from Backend.file_manager import FileManager


logger = logging.getLogger(__name__)

class FileProgressDialog:
    """Dialog showing file transfer progress"""
    def __init__(self, parent, title, file_info):
        self.parent = parent
        self.file_info = file_info
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Prevent closing with the X button
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
        self.setup_ui()
    
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # File info
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(
            info_frame, 
            text=f"File: {self.file_info['file_name']}",
            font=('Arial', 10, 'bold')
        ).pack(anchor=tk.W)
        
       
        size_str = FileManager.format_file_size(self.file_info['file_size'])
        ttk.Label(
            info_frame,
            text=f"Size: {size_str}"
        ).pack(anchor=tk.W)
        
        # Progress bar
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            orient=tk.HORIZONTAL, 
            length=350, 
            mode='determinate',
            variable=self.progress_var
        )
        self.progress_bar.pack(fill=tk.X)
        
        # Status label
        self.status_label = ttk.Label(
            progress_frame,
            text="Starting transfer..."
        )
        self.status_label.pack(anchor=tk.W, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.on_cancel
        )
        self.cancel_button.pack(side=tk.RIGHT)
    
    def update_progress(self, bytes_transferred):
        """Update the progress bar"""
        progress = min(100, (bytes_transferred / self.file_info['file_size']) * 100)
        self.progress_var.set(progress)
        
        transferred_str = FileManager.format_file_size(bytes_transferred)
        total_str = FileManager.format_file_size(self.file_info['file_size'])
        self.status_label.config(text=f"Transferred: {transferred_str} / {total_str} ({progress:.1f}%)")
    
    def complete(self):
        """Mark the transfer as complete"""
        self.progress_var.set(100)
        self.status_label.config(text="Transfer complete")
        self.cancel_button.config(text="Close")
    
    def on_cancel(self):
        """Handle cancel button click"""
        self.dialog.destroy()