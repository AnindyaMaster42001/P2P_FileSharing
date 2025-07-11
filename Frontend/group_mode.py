import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
import logging

logger = logging.getLogger(__name__)

class GroupMode:
    def __init__(self, parent, app_controller):
        self.parent = parent
        self.app_controller = app_controller
        
        self.setup_ui()
    
    def setup_ui(self):
        # Title
        title_frame = ttk.Frame(self.parent)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(
            title_frame, 
            text="Group Management", 
            font=('Arial', 16, 'bold'),
            foreground="#4a6fa5"
        )
        title_label.pack(side=tk.LEFT)
        
        back_button = ttk.Button(
            title_frame,
            text="Back to Home",
            command=self.app_controller.main_window.show_home_screen
        )
        back_button.pack(side=tk.RIGHT)
        
        # Main notebook for tabs
        self.group_notebook = ttk.Notebook(self.parent)
        self.group_notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create Group Tab
        self.create_group_frame = ttk.Frame(self.group_notebook, padding=10)
        self.group_notebook.add(self.create_group_frame, text="Create Group")
        
        # My Groups Tab
        self.my_groups_frame = ttk.Frame(self.group_notebook, padding=10)
        self.group_notebook.add(self.my_groups_frame, text="My Groups")
        
        # Setup tabs
        self.setup_create_group_tab()
        self.setup_my_groups_tab()
        
        # Bind tab change event
        self.group_notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
    
    def setup_create_group_tab(self):
        """Setup the Create Group tab"""
        # Group creation section
        create_frame = ttk.LabelFrame(self.create_group_frame, text="Create New Group", padding=10)
        create_frame.pack(fill=tk.X, pady=5)
        
        # Group name input
        name_frame = ttk.Frame(create_frame)
        name_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(name_frame, text="Group Name:", width=15).pack(side=tk.LEFT)
        self.group_name_entry = ttk.Entry(name_frame)
        self.group_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Available peers section
        peers_frame = ttk.LabelFrame(self.create_group_frame, text="Select Members", padding=10)
        peers_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Peers listbox with checkboxes (using multiple selection)
        peers_list_frame = ttk.Frame(peers_frame)
        peers_list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.create_peers_listbox = tk.Listbox(peers_list_frame, selectmode=tk.MULTIPLE, height=10)
        self.create_peers_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        peers_scrollbar = ttk.Scrollbar(peers_list_frame, orient=tk.VERTICAL, command=self.create_peers_listbox.yview)
        peers_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.create_peers_listbox.config(yscrollcommand=peers_scrollbar.set)
        
        # Buttons frame
        buttons_frame = ttk.Frame(self.create_group_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            buttons_frame, 
            text="Refresh Peers",
            command=self.refresh_create_peers
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            buttons_frame, 
            text="Create Group",
            style="Action.TButton",
            command=self.create_group_with_members
        ).pack(side=tk.RIGHT)
        
        # Populate peers
        self.refresh_create_peers()
    
    def setup_my_groups_tab(self):
        """Setup the My Groups tab"""
        # Split the tab into two panels
        panel_frame = ttk.Frame(self.my_groups_frame)
        panel_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Group list
        left_panel = ttk.Frame(panel_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5), expand=True, anchor=tk.N)
        
        # Groups list
        groups_frame = ttk.LabelFrame(left_panel, text="My Groups", padding=10)
        groups_frame.pack(fill=tk.BOTH, expand=True)
        
        groups_list_frame = ttk.Frame(groups_frame)
        groups_list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.my_groups_listbox = tk.Listbox(groups_list_frame, height=15)
        self.my_groups_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        groups_scrollbar = ttk.Scrollbar(groups_list_frame, orient=tk.VERTICAL, command=self.my_groups_listbox.yview)
        groups_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.my_groups_listbox.config(yscrollcommand=groups_scrollbar.set)
        
        # Bind selection event
        self.my_groups_listbox.bind('<<ListboxSelect>>', self.on_my_group_select)
        
        # Refresh button
        ttk.Button(
            groups_frame, 
            text="Refresh Groups",
            command=self.update_my_groups_list
        ).pack(fill=tk.X, pady=(5, 0))
        
        # Right panel - Group details
        right_panel = ttk.Frame(panel_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0), expand=True)
        
        # Group details section
        self.group_details_frame = ttk.LabelFrame(right_panel, text="Group Details", padding=10)
        self.group_details_frame.pack(fill=tk.BOTH, expand=True)
        
        # Initially show placeholder
        self.show_group_placeholder()
        
        # Update groups list
        self.update_my_groups_list()
    
    def show_group_placeholder(self):
        """Show placeholder when no group is selected"""
        # Clear existing widgets
        for widget in self.group_details_frame.winfo_children():
            widget.destroy()
        
        placeholder = ttk.Label(
            self.group_details_frame, 
            text="Select a group to view details",
            font=('Arial', 10, 'italic')
        )
        placeholder.pack(expand=True, pady=50)
    
    def show_group_details(self, group_name):
        """Show details for the selected group"""
        # Clear existing widgets
        for widget in self.group_details_frame.winfo_children():
            widget.destroy()
        
        # Group info
        info_frame = ttk.Frame(self.group_details_frame)
        info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(
            info_frame, 
            text=f"Group: {group_name}",
            font=('Arial', 12, 'bold'),
            foreground="#4a6fa5"
        ).pack(anchor=tk.W)
        
        # Members section
        members_frame = ttk.LabelFrame(self.group_details_frame, text="Members", padding=10)
        members_frame.pack(fill=tk.X, pady=10)
        
        members_list_frame = ttk.Frame(members_frame)
        members_list_frame.pack(fill=tk.X)
        
        # Listbox showing current members
        self.group_members_listbox = tk.Listbox(members_list_frame, height=5)
        self.group_members_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        members_scrollbar = ttk.Scrollbar(members_list_frame, orient=tk.VERTICAL, command=self.group_members_listbox.yview)
        members_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.group_members_listbox.config(yscrollcommand=members_scrollbar.set)
        
        # Members buttons
        buttons_frame = ttk.Frame(members_frame)
        buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            buttons_frame, 
            text="Add Member",
            command=lambda: self.add_member_to_group(group_name)
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            buttons_frame, 
            text="Refresh Members",
            command=lambda: self.update_group_members_list(group_name)
        ).pack(side=tk.RIGHT)
        
        # Populate the list
        self.update_group_members_list(group_name)
        
        # File operations section - Create notebook
        file_notebook = ttk.Notebook(self.group_details_frame)
        file_notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Shared with me tab
        shared_with_me_frame = ttk.Frame(file_notebook, padding=10)
        file_notebook.add(shared_with_me_frame, text="Shared with Me")
        
        # Share directory tab
        share_dir_frame = ttk.Frame(file_notebook, padding=10)
        file_notebook.add(share_dir_frame, text="Share Directory")
        
        # Setup tabs
        self.setup_shared_with_me_tab(shared_with_me_frame, group_name)
        self.setup_share_directory_tab(share_dir_frame, group_name)
    
    def setup_shared_with_me_tab(self, parent, group_name):
        """Setup the Shared with Me tab"""
        # Create treeview for directories and files
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.shared_dirs_tree = ttk.Treeview(
            tree_frame, 
            columns=('Size', 'Sharer'), 
            show='tree headings'
        )
        self.shared_dirs_tree.heading('#0', text='Name')
        self.shared_dirs_tree.heading('Size', text='Size')
        self.shared_dirs_tree.heading('Sharer', text='Shared By')
        self.shared_dirs_tree.column('#0', width=250)
        self.shared_dirs_tree.column('Size', width=80)
        self.shared_dirs_tree.column('Sharer', width=100)
        
        self.shared_dirs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.shared_dirs_tree.yview)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.shared_dirs_tree.config(yscrollcommand=tree_scrollbar.set)
        
        # Download button
        actions_frame = ttk.Frame(parent)
        actions_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            actions_frame, 
            text="Download Selected",
            command=lambda: self.download_from_group(group_name)
        ).pack(side=tk.RIGHT)
        
        ttk.Button(
            actions_frame, 
            text="Refresh Shared Files",
            command=lambda: self.update_shared_directories(group_name)
        ).pack(side=tk.LEFT)
        
        # Populate shared directories
        self.update_shared_directories(group_name)
    
    def setup_share_directory_tab(self, parent, group_name):
        """Setup the Share Directory tab"""
        # Directory selection
        dir_frame = ttk.Frame(parent)
        dir_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(dir_frame, text="Directory to share:").pack(anchor=tk.W)
        
        select_frame = ttk.Frame(dir_frame)
        select_frame.pack(fill=tk.X, pady=5)
        
        self.share_dir_entry = ttk.Entry(select_frame)
        self.share_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(
            select_frame, 
            text="Browse",
            command=self.browse_directory_to_share
        ).pack(side=tk.RIGHT)
        
        # Members to share with
        members_frame = ttk.LabelFrame(parent, text="Share with members:", padding=10)
        members_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        members_list_frame = ttk.Frame(members_frame)
        members_list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.share_members_listbox = tk.Listbox(members_list_frame, selectmode=tk.MULTIPLE)
        self.share_members_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        members_scrollbar = ttk.Scrollbar(members_list_frame, orient=tk.VERTICAL, command=self.share_members_listbox.yview)
        members_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.share_members_listbox.config(yscrollcommand=members_scrollbar.set)
        
        # Share button
        actions_frame = ttk.Frame(parent)
        actions_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            actions_frame, 
            text="Share Directory",
            style="Action.TButton",
            command=lambda: self.share_directory_to_group(group_name)
        ).pack(side=tk.RIGHT)
        
        # Populate members for sharing
        self.update_share_members_list(group_name)
    
    def refresh_create_peers(self):
        """Refresh the list of peers for group creation"""
        self.create_peers_listbox.delete(0, tk.END)
        for username in self.app_controller.users:
            if username != self.app_controller.current_user.username:
                self.create_peers_listbox.insert(tk.END, username)
    
    def create_group_with_members(self):
        """Create a new group with selected members"""
        group_name = self.group_name_entry.get().strip()
        
        # Get selected members
        selected_indices = self.create_peers_listbox.curselection()
        selected_members = [self.create_peers_listbox.get(i) for i in selected_indices]
        
        def create_group_thread():
            success, message = self.app_controller.create_group(group_name, selected_members)
            
            # Update UI from main thread
            self.parent.after_idle(
                lambda: self.handle_create_group_result(success, message, group_name)
            )
        
        threading.Thread(target=create_group_thread, daemon=True).start()
    
    def handle_create_group_result(self, success, message, group_name):
        """Handle group creation result"""
        if success:
            # Clear form
            self.group_name_entry.delete(0, tk.END)
            self.create_peers_listbox.selection_clear(0, tk.END)
            
            # Update my groups list
            self.update_my_groups_list()
            
            # Switch to My Groups tab
            self.group_notebook.select(self.my_groups_frame)
            
            messagebox.showinfo("Success", f"Group '{group_name}' created successfully!")
        else:
            messagebox.showerror("Error", message)
    
    def on_tab_changed(self, event):
        """Handle tab change events"""
        selected_tab = self.group_notebook.select()
        tab_text = self.group_notebook.tab(selected_tab, "text")
        
        if tab_text == "Create Group":
            self.refresh_create_peers()
        elif tab_text == "My Groups":
            self.update_my_groups_list()
    
    def on_my_group_select(self, event):
        """Handle group selection"""
        selection = self.my_groups_listbox.curselection()
        if selection:
            group_name = self.my_groups_listbox.get(selection[0])
            self.app_controller.selected_group = group_name
            self.show_group_details(group_name)
    
    def update_my_groups_list(self):
        """Update the list of user's groups"""
        self.my_groups_listbox.delete(0, tk.END)
        user_groups = self.app_controller.group_manager.list_user_groups()
        
        for group_name in user_groups:
            self.my_groups_listbox.insert(tk.END, group_name)
    
    def update_group_members_list(self, group_name):
        """Update the list of group members"""
        if hasattr(self, 'group_members_listbox') and group_name in self.app_controller.group_manager.groups:
            self.group_members_listbox.delete(0, tk.END)
            members = self.app_controller.group_manager.get_group_members(group_name)
            
            for member in members:
                self.group_members_listbox.insert(tk.END, member)
    
    def add_member_to_group(self, group_name):
        """Show dialog to add a member to a group"""
        # Get available peers (not already in group)
        current_members = self.app_controller.group_manager.get_group_members(group_name)
        available_peers = [user for user in self.app_controller.users 
                         if user not in current_members and 
                         user != self.app_controller.current_user.username]
        
        if not available_peers:
            messagebox.showinfo("Info", "No available peers to add")
            return
        
        # Create selection dialog
        selection_window = tk.Toplevel(self.parent)
        selection_window.title("Add Member to Group")
        selection_window.geometry("300x400")
        selection_window.transient(self.parent)
        selection_window.grab_set()
        
        ttk.Label(selection_window, text="Select member to add:").pack(pady=10)
        
        # Listbox for member selection
        member_listbox = tk.Listbox(selection_window, selectmode=tk.SINGLE)
        member_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for peer in available_peers:
            member_listbox.insert(tk.END, peer)
        
        # Buttons
        button_frame = ttk.Frame(selection_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def add_selected_member():
            selection = member_listbox.curselection()
            if selection:
                selected_member = member_listbox.get(selection[0])
                
                def add_member_thread():
                    # Add to group
                    self.app_controller.group_manager.add_member(group_name, selected_member)
                    # Send invitation
                    self.app_controller.send_group_invitations(group_name, [selected_member])
                    
                    # Update UI from main thread
                    self.parent.after_idle(
                        lambda: self.handle_add_member_result(group_name, selected_member)
                    )
                
                threading.Thread(target=add_member_thread, daemon=True).start()
                selection_window.destroy()
            else:
                messagebox.showwarning("Warning", "Please select a member")
        
        ttk.Button(button_frame, text="Add", command=add_selected_member).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=selection_window.destroy).pack(side=tk.RIGHT)
    
    def handle_add_member_result(self, group_name, member):
        """Handle add member result"""
        # Update displays
        self.update_group_members_list(group_name)
        self.update_share_members_list(group_name)
        messagebox.showinfo("Success", f"Added {member} to group {group_name}")
    
    def update_share_members_list(self, group_name):
        """Update the list of members for sharing"""
        if hasattr(self, 'share_members_listbox') and group_name in self.app_controller.group_manager.groups:
            self.share_members_listbox.delete(0, tk.END)
            members = self.app_controller.group_manager.get_group_members(group_name)
            
            for member in members:
                if member != self.app_controller.current_user.username:
                    self.share_members_listbox.insert(tk.END, member)
    
    def browse_directory_to_share(self):
        """Browse for a directory to share"""
        directory = filedialog.askdirectory()
        if directory:
            self.share_dir_entry.delete(0, tk.END)
            self.share_dir_entry.insert(0, directory)
    
    def share_directory_to_group(self, group_name):
        """Share a directory with group members"""
        directory = self.share_dir_entry.get().strip()
        if not directory or not os.path.exists(directory):
            messagebox.showwarning("Warning", "Please select a valid directory")
            return
        
        # Get selected members
        selected_indices = self.share_members_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select at least one member to share with")
            return
        
        selected_members = [self.share_members_listbox.get(i) for i in selected_indices]
        
        def share_directory_thread():
            success = self.app_controller.share_directory(group_name, directory, selected_members)
            
            # Update UI from main thread
            self.parent.after_idle(
                lambda: self.handle_share_directory_result(success, group_name)
            )
        
        threading.Thread(target=share_directory_thread, daemon=True).start()
    
    def handle_share_directory_result(self, success, group_name):
        """Handle directory share result"""
        if success:
            # Clear form
            self.share_dir_entry.delete(0, tk.END)
            self.share_members_listbox.selection_clear(0, tk.END)
            
            messagebox.showinfo("Success", "Directory shared successfully")
        else:
            messagebox.showerror("Error", "Failed to share directory")
    
    def update_shared_directories(self, group_name):
        """Update the list of shared directories"""
        if hasattr(self, 'shared_dirs_tree') and group_name in self.app_controller.group_manager.groups:
            # Clear existing items
            for item in self.shared_dirs_tree.get_children():
                self.shared_dirs_tree.delete(item)
            
            # Add shared directories
            shared_dirs = self.app_controller.group_manager.get_shared_directories(group_name)
            for sharer, directories in shared_dirs.items():
                for directory in directories:
                    if os.path.exists(directory):
                        # Add directory node
                        dir_node = self.shared_dirs_tree.insert(
                            '', 'end', 
                            text=os.path.basename(directory), 
                            values=('Directory', sharer), 
                            tags=('directory',)
                        )
                        
                        # Add files in directory
                        try:
                            for file_name in os.listdir(directory):
                                file_path = os.path.join(directory, file_name)
                                if os.path.isfile(file_path):
                                    file_size = self.app_controller.file_manager.format_file_size(os.path.getsize(file_path))
                                    self.shared_dirs_tree.insert(
                                        dir_node, 'end', 
                                        text=file_name, 
                                        values=(file_size, sharer), 
                                        tags=('file',)
                                    )
                        except PermissionError:
                            self.shared_dirs_tree.insert(
                                dir_node, 'end', 
                                text="Permission Denied", 
                                values=('', sharer), 
                                tags=('error',)
                            )
    
    def download_from_group(self, group_name):
        """Download a selected file from a group"""
        selection = self.shared_dirs_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file to download")
            return
        
        item = selection[0]
        item_tags = self.shared_dirs_tree.item(item, 'tags')
        
        if 'file' not in item_tags:
            messagebox.showwarning("Warning", "Please select a file (not a directory)")
            return
        
        file_name = self.shared_dirs_tree.item(item, 'text')
        sharer = self.shared_dirs_tree.item(item, 'values')[1]
        
        # Get the directory path
        parent_item = self.shared_dirs_tree.parent(item)
        dir_name = self.shared_dirs_tree.item(parent_item, 'text')
        
        # Find the full path
        shared_dirs = self.app_controller.group_manager.groups[group_name]['shared_dirs']
        if sharer in shared_dirs:
            for directory in shared_dirs[sharer]:
                if os.path.basename(directory) == dir_name:
                    file_path = os.path.join(directory, file_name)
                    if os.path.exists(file_path):
                        self.copy_file_to_downloads(file_path, file_name)
                        return
        
        messagebox.showerror("Error", "File not found or access denied")
    
    def copy_file_to_downloads(self, source_path, file_name):
        """Copy a file to the downloads directory"""
        try:
            # Create downloads directory if it doesn't exist
            from Backend.utils import get_group_download_dir
            downloads_dir = get_group_download_dir()
            os.makedirs(downloads_dir, exist_ok=True)
            
            # Generate unique filename to avoid conflicts
            base_name, ext = os.path.splitext(file_name)
            counter = 1
            dest_path = os.path.join(downloads_dir, file_name)
            
            while os.path.exists(dest_path):
                dest_path = os.path.join(downloads_dir, f"{base_name}_{counter}{ext}")
                counter += 1
            
            # Copy the file
            import shutil
            shutil.copy2(source_path, dest_path)
            
            messagebox.showinfo("Success", f"File downloaded to: {dest_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to download file: {str(e)}")