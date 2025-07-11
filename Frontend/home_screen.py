import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging

logger = logging.getLogger(__name__)

class HomeScreen:
    def __init__(self, parent, app_controller, show_private_mode, show_group_mode):
        self.parent = parent
        self.app_controller = app_controller
        self.show_private_mode = show_private_mode
        self.show_group_mode = show_group_mode
        
        self.setup_ui()
    
    def setup_ui(self):
        # Title
        title_frame = ttk.Frame(self.parent)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(
            title_frame, 
            text=f"Welcome, {self.app_controller.current_user.username}!", 
            font=('Arial', 18, 'bold'),
            foreground="#4a6fa5"
        )
        title_label.pack()
        
        server_info = ttk.Label(
            title_frame,
            text=f"Server running on port {self.app_controller.current_user.port}",
            font=('Arial', 10)
        )
        server_info.pack()
        
        # Main content with cards
        content_frame = ttk.Frame(self.parent)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Create two cards side by side
        private_card = self.create_card(
            content_frame,
            "Private Mode",
            "Chat and share files with individual peers",
            "chat_icon.png",
            self.show_private_mode
        )
        private_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        group_card = self.create_card(
            content_frame,
            "Group Mode",
            "Create and manage groups for collaborative sharing",
            "group_icon.png",
            self.show_group_mode
        )
        group_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Discovery button
        bottom_frame = ttk.Frame(self.parent)
        bottom_frame.pack(fill=tk.X, pady=20)
        
        self.discover_button = ttk.Button(
            bottom_frame,
            text="Discover Peers",
            style="Action.TButton",
            command=self.discover_peers
        )
        self.discover_button.pack(padx=20)
    
    def create_card(self, parent, title, description, icon_path, command):
        """Create a card widget with icon, title, description and button"""
        card = ttk.Frame(parent, padding=20, relief="raised", borderwidth=1)
        
        # Icon (placeholder)
        icon_frame = ttk.Frame(card, width=64, height=64)
        icon_frame.pack(pady=(0, 10))
        
        # Title
        title_label = ttk.Label(
            card, 
            text=title, 
            font=('Arial', 14, 'bold'),
            foreground="#4a6fa5"
        )
        title_label.pack(pady=(0, 10))
        
        # Description
        desc_label = ttk.Label(
            card,
            text=description,
            wraplength=200,
            justify="center"
        )
        desc_label.pack(pady=(0, 20))
        
        # Button
        action_button = ttk.Button(
            card,
            text=f"Enter {title}",
            style="Action.TButton",
            command=command
        )
        action_button.pack()
        
        return card
    
    def discover_peers(self):
        """Handle peer discovery"""
        self.discover_button.config(state=tk.DISABLED, text="Discovering...")
        
        def discovery_thread():
            discovered = self.app_controller.discover_peers()
            
            # Update UI from main thread
            self.parent.after_idle(
                lambda: self.handle_discovery_result(discovered)
            )
        
        threading.Thread(target=discovery_thread, daemon=True).start()
    
    def handle_discovery_result(self, discovered):
        """Handle discovery result"""
        self.discover_button.config(state=tk.NORMAL, text="Discover Peers")
        messagebox.showinfo("Discovery", f"Found {discovered} peers on the network")