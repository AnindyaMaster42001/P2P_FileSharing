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
        self.is_signup_mode = False
        
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
        self.auth_frame = ttk.LabelFrame(container, text="User Authentication", padding=20)
        self.auth_frame.pack(padx=20, pady=10, fill=tk.X)
        
        # Email field
        email_frame = ttk.Frame(self.auth_frame)
        email_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(email_frame, text="Email:", width=15).pack(side=tk.LEFT)
        self.email_entry = ttk.Entry(email_frame, width=30)
        self.email_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Password field
        password_frame = ttk.Frame(self.auth_frame)
        password_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(password_frame, text="Password:", width=15).pack(side=tk.LEFT)
        self.password_entry = ttk.Entry(password_frame, width=30, show="*")
        self.password_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Username field (only shown after successful authentication)
        self.username_frame = ttk.Frame(self.auth_frame)
        ttk.Label(self.username_frame, text="Username:", width=15).pack(side=tk.LEFT)
        self.username_entry = ttk.Entry(self.username_frame, width=30)
        self.username_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Auth buttons
        button_frame = ttk.Frame(self.auth_frame)
        button_frame.pack(fill=tk.X, pady=(20, 5))
        
        self.login_button = ttk.Button(
            button_frame, 
            text="Sign In",
            style="Action.TButton",
            command=self.authenticate_user
        )
        self.login_button.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        self.signup_button = ttk.Button(
            button_frame, 
            text="Sign Up",
            command=self.toggle_mode
        )
        self.signup_button.pack(side=tk.RIGHT, padx=5, expand=True, fill=tk.X)
        
        # Status label
        self.status_label = ttk.Label(self.auth_frame, text="", foreground="red")
        self.status_label.pack(fill=tk.X, pady=(10, 0))
        
        # Focus on email field
        self.email_entry.focus_set()
        
        # Update UI based on initial mode
        self.update_ui_for_mode()
        
        # Bind Enter key to login
        self.parent.bind('<Return>', lambda e: self.authenticate_user())
    
    def update_ui_for_mode(self):
        """Update UI based on whether we're in login or signup mode"""
        if self.is_signup_mode:
            self.auth_frame.config(text="Create Account")
            self.login_button.config(text="Create Account")
            self.signup_button.config(text="Back to Login")
        else:
            self.auth_frame.config(text="User Authentication")
            self.login_button.config(text="Sign In")
            self.signup_button.config(text="Sign Up")
            
        # Hide username initially - will show after authentication
        if hasattr(self, 'username_frame'):
            self.username_frame.pack_forget()
    
    def toggle_mode(self):
        """Toggle between login and signup modes"""
        self.is_signup_mode = not self.is_signup_mode
        self.update_ui_for_mode()
        self.status_label.config(text="")
    
    def authenticate_user(self):
        """Handle authentication process"""
        # Clear previous status
        self.status_label.config(text="")
        
        email = self.email_entry.get().strip()
        password = self.password_entry.get()
        
        if not email or not password:
            self.status_label.config(text="Please enter both email and password")
            return
        
        # Disable buttons while processing
        self.login_button.config(state=tk.DISABLED)
        self.signup_button.config(state=tk.DISABLED)
        
        if self.is_signup_mode:
            self.status_label.config(text="Creating account...", foreground="blue")
        else:
            self.status_label.config(text="Signing in...", foreground="blue")
        
        # Use threading to avoid freezing UI
        def auth_thread():
            if self.is_signup_mode:
                success, result = self.app_controller.sign_up_user(email, password)
            else:
                success, result = self.app_controller.sign_in_user(email, password)
            
            # Update UI from main thread
            self.parent.after_idle(
                lambda: self.handle_auth_result(success, result)
            )
        
        threading.Thread(target=auth_thread, daemon=True).start()
    
    def handle_auth_result(self, success, result):
        """Handle authentication result"""
        if success:
            # Authentication successful - now show username field to proceed
            self.status_label.config(text="Authentication successful! Please enter your preferred username for P2P network.", foreground="green")
            
            # Show username field
            self.username_frame.pack(fill=tk.X, pady=5, after=self.password_entry.master)
            self.username_entry.focus_set()
            
            # Change login button to "Connect" to finish setup
            self.login_button.config(text="Connect to Network", state=tk.NORMAL, command=self.connect_to_network)
            self.signup_button.config(state=tk.DISABLED)
            
            # Store auth result
            self.auth_result = result
        else:
            # Authentication failed
            self.status_label.config(text=result, foreground="red")
            self.login_button.config(state=tk.NORMAL)
            self.signup_button.config(state=tk.NORMAL)
    
    def connect_to_network(self):
        """After authentication, connect to the P2P network"""
        # Clear previous status
        self.status_label.config(text="")
        
        username = self.username_entry.get().strip()
        
        if not username:
            self.status_label.config(text="Please enter a username")
            return
        
        # Disable login button while processing
        self.login_button.config(state=tk.DISABLED)
        self.status_label.config(text="Connecting to network...", foreground="blue")
        
        # Use threading to avoid freezing UI
        def login_thread():
            success, result = self.app_controller.login_user(username, self.auth_result)
            
            # Update UI from main thread
            self.parent.after_idle(
                lambda: self.handle_login_result(success, result)
            )
        
        threading.Thread(target=login_thread, daemon=True).start()
    
    def handle_login_result(self, success, result):
        """Handle login result"""
        if success:
            # Login successful - result is the actual port used
            self.on_login_success(result)
        else:
            # Login failed
            self.status_label.config(text=result, foreground="red")
            self.login_button.config(state=tk.NORMAL)