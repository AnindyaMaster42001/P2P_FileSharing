import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
import logging

logger = logging.getLogger(__name__)

class PrivateMode:
    def __init__(self, parent, app_controller):
        self.parent = parent
        self.app_controller = app_controller
        self.root = parent
        self.setup_ui()
    
    def setup_ui(self):
        # Title
        title_frame = ttk.Frame(self.parent)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(
            title_frame, 
            text="Private Communication", 
            font=('Arial', 16, 'bold'),
            foreground="#b4c1d6"
        )
        title_label.pack(side=tk.LEFT)
        
        back_button = ttk.Button(
            title_frame,
            text="Back to Home",
            command=self.app_controller.main_window.show_home_screen
        )
        back_button.pack(side=tk.RIGHT)
        
        # Main content with two panels
        content_frame = ttk.Frame(self.parent)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Left panel - Peer management
        left_panel = ttk.LabelFrame(content_frame, text="Peers", padding=10)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Discover peers button
        ttk.Button(
            left_panel, 
            text="Discover Peers",
            command=self.discover_peers
        ).pack(fill=tk.X, pady=5)
        
        # Online users list
        ttk.Label(left_panel, text="Available Peers:").pack(anchor=tk.W)
        
        peers_frame = ttk.Frame(left_panel)
        peers_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.users_listbox = tk.Listbox(peers_frame, height=12)
        self.users_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                # Add scrollbar to listbox
        users_scrollbar = ttk.Scrollbar(peers_frame, orient=tk.VERTICAL, command=self.users_listbox.yview)
        users_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.users_listbox.config(yscrollcommand=users_scrollbar.set)
        
        # Bind selection event
        self.users_listbox.bind('<<ListboxSelect>>', self.on_user_select)
        
        # Status label
        self.status_label = ttk.Label(left_panel, text="Select a peer to chat with")
        self.status_label.pack(fill=tk.X, pady=5)
        
        # Right panel - Chat and file transfer
        self.right_panel = ttk.Frame(content_frame)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # File operations section
        file_frame = ttk.LabelFrame(self.right_panel, text="File Operations", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            file_frame, 
            text="Send File",
            command=self.send_file
        ).pack(side=tk.LEFT, padx=5)
        
        self.file_status_label = ttk.Label(file_frame, text="Select a peer to send files")
        self.file_status_label.pack(side=tk.LEFT, padx=10)
        
        # Chat section
        chat_frame = ttk.LabelFrame(self.right_panel, text="Private Chat", padding=10)
        chat_frame.pack(fill=tk.BOTH, expand=True)
        
        # Chat display with scrollbar
        chat_display_frame = ttk.Frame(chat_frame)
        chat_display_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.chat_display = scrolledtext.ScrolledText(chat_display_frame, height=15, state=tk.DISABLED)
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # Input area
        chat_input_frame = ttk.Frame(chat_frame)
        chat_input_frame.pack(fill=tk.X, pady=5)
        
        self.chat_entry = ttk.Entry(chat_input_frame)
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        send_button = ttk.Button(
            chat_input_frame, 
            text="Send",
            command=self.send_chat_message
        )
        send_button.pack(side=tk.RIGHT)
        
        # Bind Enter key to send message
        self.chat_entry.bind('<Return>', lambda e: self.send_chat_message())
        
        # Update UI
        self.update_users_list()
        self.update_chat_display_with_history()
    
    def discover_peers(self):
        """Handle peer discovery"""
        self.status_label.config(text="Discovering peers...")
        
        def discovery_thread():
            discovered = self.app_controller.discover_peers()
            
            # Update UI from main thread
            self.parent.after_idle(
                lambda: self.handle_discovery_result(discovered)
            )
        
        threading.Thread(target=discovery_thread, daemon=True).start()
    
    def handle_discovery_result(self, discovered):
        """Handle discovery result"""
        self.status_label.config(text=f"Found {discovered} peers")
        self.update_users_list()
        self.update_file_status()
    
    def update_users_list(self):
        """Update the list of users"""
        self.users_listbox.delete(0, tk.END)
        for username in self.app_controller.users:
            if username != self.app_controller.current_user.username:
                self.users_listbox.insert(tk.END, username)
    
    def on_user_select(self, event):
        """Handle user selection"""
        selection = self.users_listbox.curselection()
        if selection:
            self.app_controller.selected_peer = self.users_listbox.get(selection[0])
            self.update_file_status()
            self.update_chat_display_with_history()
    
    def update_file_status(self):
        """Update the file status label"""
        if self.app_controller.selected_peer:
            pending_count = len(self.app_controller.file_manager.pending_file_requests)
            if pending_count > 0:
                self.file_status_label.config(
                    text=f"Selected: {self.app_controller.selected_peer} | {pending_count} pending transfer(s)"
                )
            else:
                self.file_status_label.config(
                    text=f"Selected: {self.app_controller.selected_peer} | Ready to send files"
                )
        else:
            self.file_status_label.config(text="Select a peer to send files")
    
    def send_file(self):
        """Send a file to the selected peer"""
        if not self.app_controller.selected_peer:
            messagebox.showwarning("Warning", "Please select a peer first")
            return
        
        file_path = filedialog.askopenfilename(
            title="Select file to send",
            filetypes=[("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        self.status_label.config(text="Sending file request...")
        
        def send_file_thread():
            success, result = self.app_controller.send_file(
                self.app_controller.selected_peer, 
                file_path
            )
            
            # Update UI from main thread
            self.parent.after_idle(
                lambda: self.handle_send_file_result(success, result)
            )
        
        threading.Thread(target=send_file_thread, daemon=True).start()
    
    def handle_send_file_result(self, success, result):
        """Handle file send result"""
        if success:
            self.status_label.config(text="File request sent successfully")
            self.update_file_status()
            # If you want to add a message about the file transfer to the chat
            file_info = os.path.basename(result) if isinstance(result, str) else "file"
            self.update_chat_display(f"You: [Sent file request: {file_info}]")
        else:
            self.status_label.config(text="Failed to send file request")
            messagebox.showerror("Error", f"Failed to send file: {result}")
    
    def send_chat_message(self):
        """Send a chat message to the selected peer with timeout"""
        message = self.chat_entry.get().strip()
        if not message or not self.app_controller.selected_peer:
            if not message:
                messagebox.showwarning("Warning", "Please enter a message")
            else:
                messagebox.showwarning("Warning", "Please select a peer first")
            return
        
        # Clear the input field immediately for better UX
        self.chat_entry.delete(0, tk.END)
        
        # Show sending status
        self.status_label.config(text="Sending message...")
        
        # Create a cancel button
        cancel_button = ttk.Button(
                self.chat_display.master,
                text="Cancel",
                command=self.cancel_message_sending
            )
        cancel_button.pack(side=tk.BOTTOM, pady=5)
            
            # Store reference to cancel button
        self.cancel_button = cancel_button
            
            # Create a thread for sending with timeout control
        self.sending_thread = threading.Thread(
                target=self.send_message_thread,
                args=(message,),
                daemon=True
            )
        self.sending_thread.start()
            
            # Start a timer to check for timeout
        # Change this line in send_chat_message
        self.parent.after(10000, self.check_message_timeout)  # 10 second timeout # 10 second timeout
        
        
    def handle_send_error(self, error_message):
        """Handle errors during message sending"""
        self.status_label.config(text=f"Error: {error_message}", foreground="red")
        messagebox.showerror("Error", f"Failed to send message: {error_message}")
        
        # Remove cancel button
        if hasattr(self, 'cancel_button') and self.cancel_button:
            self.cancel_button.destroy()
            self.cancel_button = None
            

    def send_message_thread(self, message):
            """Thread function for sending message"""
            try:
                self.send_in_progress = True
                success = self.app_controller.send_chat_message(
                    self.app_controller.selected_peer, 
                    message
                )
                
                # Update UI from main thread if still in progress
                if self.send_in_progress:
                    self.parent.after_idle(
                        lambda: self.handle_send_message_result(success, message , message)
                    )
            except Exception as e:
                if self.send_in_progress:
                    self.parent.after_idle(
                        lambda: self.handle_send_error(str(e))
                    )
            finally:
                self.send_in_progress = False

    def check_message_timeout(self):
        """Check if message sending has timed out"""
        if hasattr(self, 'send_in_progress') and self.send_in_progress:
            self.send_in_progress = False
            self.status_label.config(text="Message sending timed out", foreground="red")
            
            # Show error message
            messagebox.showerror(
                "Connection Timeout",
                f"Could not connect to {self.app_controller.selected_peer}.\n"
                "The peer may be offline or behind a firewall."
            )
            
            # Remove cancel button
            if hasattr(self, 'cancel_button') and self.cancel_button:
                self.cancel_button.destroy()
                self.cancel_button = None

    def cancel_message_sending(self):
        """Cancel the message sending operation"""
        if hasattr(self, 'send_in_progress') and self.send_in_progress:
            self.send_in_progress = False
            self.status_label.config(text="Message sending cancelled", foreground="blue")
            
            # Remove cancel button
            if hasattr(self, 'cancel_button') and self.cancel_button:
                self.cancel_button.destroy()
                self.cancel_button = None
    
    def handle_send_message_result(self, success, message):
        """Handle message send result"""
        if success:
            self.chat_entry.delete(0, tk.END)
            self.status_label.config(text="Message sent")
        else:
            self.status_label.config(text="Failed to send message")
            messagebox.showerror("Error", "Failed to send message. Peer may be offline.")
    
    def update_chat_display(self, message):
        """Update the chat display with a new message"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def update_chat_display_with_history(self):
        """Update the chat display with message history"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        
        # Filter messages for current peer if selected
        if self.app_controller.selected_peer:
            peer = self.app_controller.selected_peer
            for message in self.app_controller.temp_messages:
                if f"{peer}: " in message or "You: " in message:
                    self.chat_display.insert(tk.END, message + "\n")
        
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
    def handle_send_message_result(self, success, result, message):
        """Handle message send result with better error reporting"""
        if success:
            self.chat_entry.delete(0, tk.END)
            self.status_label.config(text="Message sent")
        else:
            self.status_label.config(text=f"Failed to send message: {result}")
            
            # Check if it's a connection issue
            if "offline" in result.lower() or "refused" in result.lower() or "connection" in result.lower():
                response = messagebox.askyesno(
                    "Connection Issue",
                    f"Cannot connect to peer {self.app_controller.selected_peer}.\n"
                    "Would you like to see firewall configuration instructions?",
                    icon="warning"
                )
                if response:
                    self.app_controller.show_firewall_instructions()