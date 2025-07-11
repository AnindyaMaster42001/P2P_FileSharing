import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import logging
from datetime import datetime   
from Frontend.login_screen import LoginScreen
from Frontend.home_screen import HomeScreen
from Frontend.private_mode import PrivateMode
from Frontend.group_mode import GroupMode

logger = logging.getLogger(__name__)

class MainWindow:
    def __init__(self, app_controller):
        self.app_controller = app_controller
        self.app_controller.main_window = self
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("P2P File Sharing Application")
        self.root.geometry("900x650")
        self.root.minsize(800, 600)
        
        # Apply theme
        self.setup_theme()
        
        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Current UI components
        self.current_screen = None
        self.private_mode = None
        self.group_mode = None
        
        # Show login screen initially (FIXED LINE)
        self.show_login_screen()
        
        # Set up window closing protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_theme(self):
        """Set up the application theme and styling"""
        # Configure ttk style
        style = ttk.Style()
        
        # Try to use a modern theme if available
        try:
            style.theme_use('clam')  # Alternative: 'alt', 'default', 'classic'
        except tk.TclError:
            pass  # Use default theme if 'clam' is not available
        
        # Configure colors
        bg_color = "#f5f5f5"
        accent_color = "#4a6fa5"
        text_color = "#333333"
        
        # Configure ttk styles
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=text_color)
        style.configure('TButton', background=accent_color, foreground='white')
        style.configure('TEntry', fieldbackground='white')
        style.configure('Heading.TLabel', font=('Arial', 16, 'bold'))
        
        # Configure root window colors
        self.root.configure(background=bg_color)
        
        # Custom styles
        style.configure('Action.TButton', background=accent_color, foreground='white', 
                        font=('Arial', 10, 'bold'))
        style.configure('Secondary.TButton', background='#dddddd', foreground=text_color)
        
        # Configure notebook style
        style.configure('TNotebook', background=bg_color)
        style.configure('TNotebook.Tab', background='#dddddd', padding=[10, 5])
        style.map('TNotebook.Tab', 
                 background=[('selected', accent_color)],
                 foreground=[('selected', 'white')])
    
    def clear_main_frame(self):
        """Clear all widgets from the main frame"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()
    
    def show_login_screen(self):
        """Show the login screen"""
        self.clear_main_frame()
        self.current_screen = LoginScreen(self.main_frame, self.app_controller, self.on_login_success)
        self.app_controller.current_mode = "login"
    
    def on_login_success(self, port):
        """Called when login is successful"""
        # Switch to home screen
        self.show_home_screen()
        
        # Show a message if port changed
        if port != int(self.current_screen.port_entry.get()):
            messagebox.showinfo(
                "Port Changed", 
                f"Requested port was unavailable.\n"
                f"Started server on port {port} instead."
            )
    
    def show_home_screen(self):
        """Show the home screen after login"""
        self.clear_main_frame()
        self.current_screen = HomeScreen(
            self.main_frame, 
            self.app_controller, 
            self.show_private_mode,
            self.show_group_mode
        )
        self.app_controller.current_mode = "home"
    
    def show_private_mode(self):
        """Show the private chat and file sharing mode"""
        self.clear_main_frame()
        self.private_mode = PrivateMode(self.main_frame, self.app_controller)
        self.app_controller.current_mode = "private"
    
    def show_group_mode(self):
        """Show the group management mode"""
        self.clear_main_frame()
        self.group_mode = GroupMode(self.main_frame, self.app_controller)
        self.app_controller.current_mode = "group"
    
    def show_file_notification(self, request_id, sender, file_name, file_size):
        """Show a notification for an incoming file transfer request"""
        size_str = self.app_controller.file_manager.format_file_size(file_size)
        
        result = messagebox.askyesno(
            "File Transfer Request",
            f"{sender} wants to send you a file:\n\n"
            f"File: {file_name}\n"
            f"Size: {size_str}\n\n"
            f"Do you want to accept this file?",
            icon='question'
        )
        
        # Send response back to sender
        self.send_file_response(sender, request_id, result)
    
    def send_file_response(self, sender, request_id, accepted):
        """Send response to a file transfer request"""
        try:
            if sender not in self.app_controller.users:
                # Handle the case where sender is not in our users list
                # This would need special handling in a real implementation
                messagebox.showerror("Error", "Could not send response to unknown sender")
                return
            
            peer = self.app_controller.users[sender]
            response = {
                'type': 'file_send_response',
                'request_id': request_id,
                'sender': self.app_controller.current_user.username,
                'accepted': accepted,
                'timestamp': datetime.now().isoformat()
            }
            
            self.app_controller.network.send_message(peer, response)
            
            if accepted:
                self.app_controller.add_temp_message(f"Accepted file transfer from {sender}")
            else:
                self.app_controller.add_temp_message(f"Rejected file transfer from {sender}")
                
        except Exception as e:
            logger.error(f"Error sending file response: {e}")
            messagebox.showerror("Error", f"Failed to send response: {str(e)}")
    
    def show_file_received_notification(self, file_info):
        """Show a notification when a file has been received"""
        messagebox.showinfo(
            "File Received", 
            f"File '{file_info['file_name']}' from {file_info['sender']}\n"
            f"Saved to: {file_info['file_path']}"
        )
    
    def show_group_invitation(self, group_name, inviter):
        """Show a notification for a group invitation"""
        result = messagebox.askyesno(
            "Group Invitation",
            f"{inviter} has invited you to join the group '{group_name}'\n\n"
            f"Do you want to accept this invitation?",
            icon='question'
        )
        
        if not result:
            messagebox.showinfo("Info", f"Group invitation from {inviter} declined")
            return
        
        # Get the invitation details
        invitation_data = getattr(self.app_controller, '_last_group_invitation', None)
        
        # Extract member list from invitation
        members = []
        if invitation_data and 'members' in invitation_data:
            members = invitation_data['members']
        else:
            # Fallback: just include inviter
            members = [inviter]
        
        # Join the group
        if self.app_controller.join_group(group_name, members, inviter):
            messagebox.showinfo("Success", f"You have joined the group '{group_name}'")
            
            # Switch to group mode and refresh if needed
            if self.app_controller.current_mode == "group" and self.group_mode:
                self.group_mode.update_my_groups_list()
            elif self.app_controller.current_mode != "group":
                self.show_group_mode()
        else:
            messagebox.showerror("Error", f"Failed to join group '{group_name}'")
    
    def update_chat_display(self, message):
        """Update the chat display with a new message"""
        if self.app_controller.current_mode == "private" and self.private_mode:
            self.private_mode.update_chat_display(message)
    
    def on_closing(self):
        """Handle window closing event"""
        if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
            self.app_controller.shutdown()
            self.root.destroy()
    
    def run(self):
        """Start the main event loop"""
        self.root.mainloop()