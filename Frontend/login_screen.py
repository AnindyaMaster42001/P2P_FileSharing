import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging

logger = logging.getLogger(__name__)

class LoginScreen:
    def __init__(self, parent, app_controller, on_login_success):
        self.parent = parent
        self.app_controller = app_controller
        self.on_login_success = on_login_success
        
        self.setup_ui()
    
    def setup_ui(self):
        # Main container with some padding and centered
        container = ttk.Frame(self.parent, padding=20)
        container.pack(expand=True)
        
        # App title
        title_frame = ttk.Frame(container)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(
            title_frame, 
            text="P2P File Sharing", 
            font=('Arial', 24, 'bold'),
            foreground="#4a6fa5"
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Connect and share files securely with peers",
            font=('Arial', 12)
        )
        subtitle_label.pack(pady=(5, 0))
        
        # Login frame with border
        login_frame = ttk.LabelFrame(container, text="User Authentication", padding=20)
        login_frame.pack(padx=20, pady=10, fill=tk.X)
        
        # Username field
        username_frame = ttk.Frame(login_frame)
        username_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(username_frame, text="Username:", width=15).pack(side=tk.LEFT)
        self.username_entry = ttk.Entry(username_frame, width=30)
        self.username_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Port field
        port_frame = ttk.Frame(login_frame)
        port_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(port_frame, text="Server Port:", width=15).pack(side=tk.LEFT)
        self.port_entry = ttk.Entry(port_frame, width=30)
        self.port_entry.insert(0, "12345")
        self.port_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Login button
        button_frame = ttk.Frame(login_frame)
        button_frame.pack(fill=tk.X, pady=(20, 5))
        
        self.login_button = ttk.Button(
            button_frame, 
            text="Sign In / Register",
            style="Action.TButton",
            command=self.login_user
        )
        self.login_button.pack(pady=5)
        
        # Status label
        self.status_label = ttk.Label(login_frame, text="", foreground="red")
        self.status_label.pack(fill=tk.X, pady=(10, 0))
        
        # Focus on username field
        self.username_entry.focus_set()
        
        # Bind Enter key to login
        self.parent.bind('<Return>', lambda e: self.login_user())
    
    def login_user(self):
        """Handle login process"""
        # Clear previous status
        self.status_label.config(text="")
        
        username = self.username_entry.get().strip()
        port = self.port_entry.get().strip()
        
        if not username:
            self.status_label.config(text="Please enter a username")
            return
        
        try:
            port = int(port)
        except ValueError:
            self.status_label.config(text="Please enter a valid port number")
            return
        
        # Disable login button while processing
        self.login_button.config(state=tk.DISABLED)
        self.status_label.config(text="Connecting...", foreground="blue")
        
        # Use threading to avoid freezing UI
        def login_thread():
            success, result = self.app_controller.login_user(username, port)
            
            # Update UI from main thread
            self.parent.after_idle(
                lambda: self.handle_login_result(success, result)
            )
        
        threading.Thread(target=login_thread, daemon=True).start()
    
    def handle_login_result(self, success, result):
        """Handle login result"""
        if success:
            # Login successful
            self.on_login_success(result)  # result is the actual port used
        else:
            # Login failed
            self.status_label.config(text=result, foreground="red")
            self.login_button.config(state=tk.NORMAL)