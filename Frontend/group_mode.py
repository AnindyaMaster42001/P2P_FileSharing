import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
import logging
import time
logger = logging.getLogger(__name__)

class GroupMode:
    def __init__(self, parent, app_controller):
        self.parent = parent
        self.app_controller = app_controller
        self.root = parent
        # Create direct reference to app_controller's group_manager
        self.group_manager = self.app_controller.group_manager
        
        # Setup the UI
        self.setup_ui()
    
    def setup_ui(self):
        # Title
        title_frame = ttk.Frame(self.parent)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(
            title_frame, 
            text="Group Management", 
            font=('Arial', 16, 'bold'),
            foreground="#e6ecf6"
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
        
        # Add refresh button
        refresh_button = ttk.Button(
            buttons_frame, 
            text="Refresh Peers",
            command=self.refresh_create_peers
        )
        refresh_button.pack(side=tk.LEFT)
        
        # Add test connectivity button
        test_button = ttk.Button(
            buttons_frame,
            text="Test Connectivity",
            command=self.test_connectivity
        )
        test_button.pack(side=tk.LEFT, padx=5)
        
        # Add debug button
        debug_button = ttk.Button(
            buttons_frame,
            text="Debug Groups",
            command=self.debug_group_info
        )
        debug_button.pack(side=tk.LEFT, padx=5)
        
        # Add create group button
        create_button = ttk.Button(
            buttons_frame, 
            text="Create Group",
            style="Action.TButton",
            command=self.create_group_with_members
        )
        create_button.pack(side=tk.RIGHT)
        
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
        
        # Create the listbox with MULTIPLE selection mode
        self.share_members_listbox = tk.Listbox(members_list_frame, selectmode=tk.MULTIPLE)
        self.share_members_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        members_scrollbar = ttk.Scrollbar(members_list_frame, orient=tk.VERTICAL, command=self.share_members_listbox.yview)
        members_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.share_members_listbox.config(yscrollcommand=members_scrollbar.set)
        
        # Add "Select All" button for convenience
        select_all_button = ttk.Button(
            members_frame,
            text="Select All",
            command=lambda: self.share_members_listbox.select_set(0, tk.END)
        )
        select_all_button.pack(side=tk.LEFT, pady=(5, 0))
        
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
        
        # Print debug info
        print(f"Debug - Initialized share_members_listbox with {self.share_members_listbox.size()} items")
    
    # Core functionality methods
    def refresh_create_peers(self):
        """Refresh the list of peers for group creation"""
        self.create_peers_listbox.delete(0, tk.END)
        
        # Try to discover peers first
        try:
            # Force a network discovery
            self.app_controller.discover_peers()
            logger.info("Discovering peers during refresh")
        except Exception as e:
            logger.error(f"Error discovering peers: {str(e)}")
        
        # Add all known users to the list
        peers_count = 0
        for username in self.app_controller.users:
            if username != self.app_controller.current_user.username:
                self.create_peers_listbox.insert(tk.END, username)
                peers_count += 1
        
        logger.info(f"Refreshed peers list with {peers_count} users")
    
    def create_group_with_members(self):
        """Create a new group with selected members"""
        group_name = self.group_name_entry.get().strip()
        
        if not group_name:
            messagebox.showwarning("Warning", "Please enter a group name")
            return
        
        # Get selected members
        selected_indices = self.create_peers_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select at least one member")
            return
            
        selected_members = [self.create_peers_listbox.get(i) for i in selected_indices]
        
        def create_group_thread():
            try:
                # First create the group with just the creator
                success, message = self.app_controller.create_group(group_name, [])
                
                if success:
                    logger.info(f"Group '{group_name}' created, sending invitations to {selected_members}")
                    
                    # Then send invitations to selected members
                    self.app_controller.send_group_invitation(group_name, selected_members)
                    
                # Update UI from main thread
                self.parent.after_idle(
                    lambda: self.handle_create_group_result(success, message, group_name)
                )
            except Exception as e:
                logger.exception(f"Error creating group: {str(e)}")
                self.parent.after_idle(
                    lambda: messagebox.showerror("Error", f"Failed to create group: {str(e)}")
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
        user_groups = self.group_manager.list_user_groups()
        
        for group_name in user_groups:
            self.my_groups_listbox.insert(tk.END, group_name)
    
    def update_share_members_list(self, group_name):
        """Update the list of members for sharing"""
        if hasattr(self, 'share_members_listbox') and group_name in self.app_controller.group_manager.groups:
            # Clear the listbox
            self.share_members_listbox.delete(0, tk.END)
            
            # Get all members of the group
            members = self.app_controller.group_manager.get_group_members(group_name)
            
            # Debug information
            print(f"Debug - Group members for {group_name}: {members}")
            
            # Add members to the listbox (except current user)
            count = 0
            for member in members:
                if member != self.app_controller.current_user.username:
                    self.share_members_listbox.insert(tk.END, member)
                    count += 1
            
            # More debug info
            print(f"Debug - Added {count} members to share_members_listbox")
            
            # Select all by default for convenience
            if count > 0:
                self.share_members_listbox.select_set(0, tk.END)
    
    def add_member_to_group(self, group_name):
        """Show dialog to add a member to a group"""
        # Get available peers (not already in group)
        current_members = self.group_manager.get_group_members(group_name)
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
                    self.group_manager.add_member(group_name, selected_member)
                    # Send invitation
                    self.app_controller.send_group_invitation(group_name, [selected_member])
                    
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
        if hasattr(self, 'share_members_listbox') and group_name in self.group_manager.groups:
            self.share_members_listbox.delete(0, tk.END)
            members = self.group_manager.get_group_members(group_name)
            
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
        
        # Get selected members - add debug output
        selected_indices = self.share_members_listbox.curselection()
        print(f"Debug - Selected indices: {selected_indices}")
        
        if not selected_indices:
            # Try to check if the listbox has items
            list_size = self.share_members_listbox.size()
            print(f"Debug - Listbox size: {list_size}")
            
            if list_size == 0:
                messagebox.showwarning("Warning", "No members available to share with")
            else:
                messagebox.showwarning("Warning", "Please select at least one member to share with")
            return
        
        selected_members = [self.share_members_listbox.get(i) for i in selected_indices]
        print(f"Debug - Selected members: {selected_members}")
        
        def share_directory_thread():
            success = self.app_controller.share_directory(group_name, directory, selected_members)
            
            # Update UI from main thread - fix the after_idle issue
            if hasattr(self.parent, 'winfo_toplevel'):
                root_window = self.parent.winfo_toplevel()
                root_window.after(
                    100,
                    lambda: self.handle_share_directory_result(success, group_name)
                )
            else:
                # Fallback if we can't get the root window
                self.handle_share_directory_result(success, group_name)
        
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
            shared_dirs = self.app_controller.group_manager.groups[group_name]['shared_dirs']
            
            for sharer, directories in shared_dirs.items():
                for directory in directories:
                    # Add the root shared directory
                    dir_node = self.shared_dirs_tree.insert(
                        '', 'end', 
                        text=os.path.basename(directory), 
                        values=('Directory', sharer), 
                        tags=('directory',)
                    )
                    
                    # Add contents of the directory
                    if os.path.exists(directory) and os.path.isdir(directory):
                        self._add_directory_contents(dir_node, directory, sharer)
                    else:
                        self.shared_dirs_tree.insert(
                            dir_node, 'end', 
                            text="Directory not accessible", 
                            values=('', sharer), 
                            tags=('error',)
                        )
    
    def _add_directory_contents(self, parent_node, directory_path, sharer):
        """Recursively add directory contents to the tree view"""
        try:
            # List items in the directory
            for item_name in os.listdir(directory_path):
                item_path = os.path.join(directory_path, item_name)
                
                if os.path.isdir(item_path):
                    # It's a subdirectory - add it as a node
                    subdir_node = self.shared_dirs_tree.insert(
                        parent_node, 'end', 
                        text=item_name, 
                        values=('Directory', sharer), 
                        tags=('directory',)
                    )
                    
                    # Recursively add its contents
                    self._add_directory_contents(subdir_node, item_path, sharer)
                    
                elif os.path.isfile(item_path):
                    # It's a file - add it as a leaf
                    file_size = self.app_controller.file_manager.format_file_size(os.path.getsize(item_path))
                    self.shared_dirs_tree.insert(
                        parent_node, 'end', 
                        text=item_name, 
                        values=(file_size, sharer), 
                        tags=('file',)
                    )
        except PermissionError:
            self.shared_dirs_tree.insert(
                parent_node, 'end', 
                text="Permission Denied", 
                values=('', sharer), 
                tags=('error',)
            )
        except Exception as e:
            self.shared_dirs_tree.insert(
                parent_node, 'end', 
                text=f"Error: {str(e)}", 
                values=('', sharer), 
                tags=('error',)
            )
    
    def download_from_group(self, group_name):
        """Download a selected file or directory from a group"""
        selection = self.shared_dirs_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file or directory to download")
            return
        
        item = selection[0]
        item_tags = self.shared_dirs_tree.item(item, 'tags')
        item_name = self.shared_dirs_tree.item(item, 'text')
        sharer = self.shared_dirs_tree.item(item, 'values')[1]
        
        # Build the full path by traversing up the tree
        path_parts = [item_name]
        parent = self.shared_dirs_tree.parent(item)
        
        while parent and parent != '':
            parent_name = self.shared_dirs_tree.item(parent, 'text')
            path_parts.insert(0, parent_name)
            parent = self.shared_dirs_tree.parent(parent)
        
        # Find the root shared directory
        root_dir_name = path_parts[0]
        shared_dirs = self.app_controller.group_manager.groups[group_name]['shared_dirs']
        
        if sharer in shared_dirs:
            # Find the matching shared directory
            for shared_dir in shared_dirs[sharer]:
                if os.path.basename(shared_dir) == root_dir_name:
                    # Build the complete path
                    source_path = shared_dir
                    for part in path_parts[1:]:
                        source_path = os.path.join(source_path, part)
                    
                    if 'file' in item_tags and os.path.isfile(source_path):
                        # Download a single file
                        self.copy_file_to_downloads(source_path, item_name)
                        return
                    elif 'directory' in item_tags and os.path.isdir(source_path):
                        # Download an entire directory
                        self.copy_directory_to_downloads(source_path, item_name)
                        return
        
        messagebox.showerror("Error", "Item not found or access denied")
    
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

    def copy_directory_to_downloads(self, source_dir, dir_name):
        """Copy an entire directory to the downloads directory"""
        try:
            # Create downloads directory if it doesn't exist
            from Backend.utils import get_group_download_dir
            downloads_dir = get_group_download_dir()
            os.makedirs(downloads_dir, exist_ok=True)
            
            # Generate unique directory name to avoid conflicts
            dest_dir = os.path.join(downloads_dir, dir_name)
            counter = 1
            
            while os.path.exists(dest_dir):
                dest_dir = os.path.join(downloads_dir, f"{dir_name}_{counter}")
                counter += 1
            
            # Create the destination directory
            os.makedirs(dest_dir, exist_ok=True)
            
            # Copy the directory contents
            import shutil
            
            # Count files to show progress
            file_count = sum([len(files) for _, _, files in os.walk(source_dir)])
            
            if file_count > 20:
                # For larger directories, show a progress dialog
                progress_window = tk.Toplevel(self.parent)
                progress_window.title("Downloading Directory")
                progress_window.geometry("400x150")
                progress_window.transient(self.parent)
                
                ttk.Label(progress_window, text=f"Downloading {dir_name}...").pack(pady=10)
                
                progress_var = tk.DoubleVar()
                progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=100)
                progress_bar.pack(fill=tk.X, padx=20, pady=10)
                
                status_label = ttk.Label(progress_window, text="Starting...")
                status_label.pack(pady=5)
                
                # Start copy in a separate thread
                copied_files = 0
                
                def copy_with_progress():
                    nonlocal copied_files
                    
                    for root, dirs, files in os.walk(source_dir):
                        # Get the relative path
                        rel_path = os.path.relpath(root, source_dir)
                        if rel_path == '.':
                            rel_path = ''
                        
                        # Create destination directory
                        dest_path = os.path.join(dest_dir, rel_path)
                        os.makedirs(dest_path, exist_ok=True)
                        
                        # Copy files
                        for file in files:
                            src_file = os.path.join(root, file)
                            dst_file = os.path.join(dest_path, file)
                            shutil.copy2(src_file, dst_file)
                            
                            copied_files += 1
                            progress = (copied_files / file_count) * 100
                            
                            # Update UI from main thread
                            self.parent.after_idle(lambda p=progress, f=file: self._update_progress(progress_var, status_label, p, f))
                    
                    # Close progress window when done
                    self.parent.after_idle(lambda: self._finish_progress(progress_window, dest_dir))
                
                threading.Thread(target=copy_with_progress, daemon=True).start()
            else:
                # For smaller directories, just copy directly
                shutil.copytree(source_dir, dest_dir)
                messagebox.showinfo("Success", f"Directory downloaded to: {dest_dir}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to download directory: {str(e)}")

    def _update_progress(self, progress_var, status_label, progress, current_file):
        """Update progress bar during directory download"""
        progress_var.set(progress)
        status_label.config(text=f"Copying: {current_file}")

    def _finish_progress(self, progress_window, dest_dir):
        """Close progress window and show success message"""
        progress_window.destroy()
        messagebox.showinfo("Success", f"Directory downloaded to: {dest_dir}")
    
    def accept_invitation(self, group_name, from_user):
        """Accept a group invitation"""
        # Find the invitation
        invitation = None
        for inv in self.group_manager.received_invitations[:]:
            if inv.get('group') == group_name and inv.get('from') == from_user:
                invitation = inv
                self.group_manager.received_invitations.remove(inv)
                break
        
        if not invitation:
            return False
        
        # Create the group locally if it doesn't exist
        if group_name not in self.group_manager.groups:
            self.group_manager.groups[group_name] = {
                'members': [self.app_controller.current_user.username, from_user],
                'shared_dirs': {}
            }
        else:
            # Add self to the group
            if self.app_controller.current_user.username not in self.group_manager.groups[group_name]['members']:
                self.group_manager.groups[group_name]['members'].append(self.app_controller.current_user.username)
        
        # Send acceptance response
        response = {
            'type': 'group_invitation_response',
            'group': group_name,
            'response': 'accept',
            'from': self.app_controller.current_user.username
        }
        
        if hasattr(self.app_controller, 'message_handler'):
            self.app_controller.message_handler.send_message(from_user, response)
        
        # Update UI
        self.update_my_groups_list()
        
        return True
    
    def decline_invitation(self, group_name, from_user):
        """Decline a group invitation"""
        # Find the invitation
        invitation = None
        for inv in self.group_manager.received_invitations[:]:
            if inv.get('group') == group_name and inv.get('from') == from_user:
                invitation = inv
                self.group_manager.received_invitations.remove(inv)
                break
        
        if not invitation:
            return False
        
        # Send decline response
        response = {
            'type': 'group_invitation_response',
            'group': group_name,
            'response': 'decline',
            'from': self.app_controller.current_user.username
        }
        
        if hasattr(self.app_controller, 'message_handler'):
            self.app_controller.message_handler.send_message(from_user, response)
        
        return True
        
    def test_connectivity(self):
        """Test connectivity to peers in the list"""
        if not self.create_peers_listbox.size():
            messagebox.showinfo("No Peers", "No peers available to test. Try refreshing first.")
            return
        
        results = {}
        for i in range(self.create_peers_listbox.size()):
            username = self.create_peers_listbox.get(i)
            
            # Try to send a ping message
            ping_message = {
                'type': 'ping',
                'timestamp': time.time()
            }
            
            success = False
            try:
                if hasattr(self.app_controller, 'message_handler'):
                    success = self.app_controller.message_handler.send_message(username, ping_message)
                else:
                    # Try direct network communication
                    if username in self.app_controller.users:
                        peer = self.app_controller.users[username]
                        response = self.app_controller.network.send_message(peer, ping_message)
                        success = response is not None
            except Exception as e:
                logger.exception(f"Error testing connectivity to {username}: {e}")
                success = False
            
            results[username] = "Connected" if success else "Not connected"
        
        # Show results
        result_text = "\n".join([f"{user}: {status}" for user, status in results.items()])
        messagebox.showinfo("Connectivity Test Results", result_text)
        
        # Log the results
        logger.info(f"Connectivity test results: {results}")
    
    def debug_group_info(self):
        """Show debug information about groups"""
        # Create a new window
        debug_window = tk.Toplevel(self.parent)
        debug_window.title("Group Debug Information")
        debug_window.geometry("600x400")
        
        # Create text area
        text_area = scrolledtext.ScrolledText(debug_window, width=80, height=24)
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Collect debug info
        info = []
        info.append(f"Current user: {self.app_controller.current_user.username}")
        info.append(f"Known users: {list(self.app_controller.users.keys())}")
        
        # Groups info
        if hasattr(self.group_manager, 'groups'):
            groups = self.group_manager.groups
            info.append(f"\nGroups ({len(groups)}):")
            for group_name, group_data in groups.items():
                info.append(f"  - {group_name}:")
                info.append(f"    Members: {group_data['members']}")
                info.append(f"    Shared Dirs: {list(group_data['shared_dirs'].keys())}")
        else:
            info.append("\nNo groups defined")
        
        # Pending invitations
        if hasattr(self.group_manager, 'pending_invitations'):
            pending = self.group_manager.pending_invitations
            info.append(f"\nPending Invitations:")
            for group, members in pending.items():
                info.append(f"  - {group}: {members}")
        else:
            info.append("\nNo pending invitations defined")
        
        # Received invitations
        if hasattr(self.group_manager, 'received_invitations'):
            received = self.group_manager.received_invitations
            info.append(f"\nReceived Invitations ({len(received)}):")
            for inv in received:
                info.append(f"  - From: {inv.get('from')}, Group: {inv.get('group')}")
        else:
            info.append("\nNo received invitations defined")
        
        # Network info
        info.append(f"\nNetwork Info:")
        info.append(f"  - Local IP: {self.app_controller.network.local_ip}")
        info.append(f"  - Port: {self.app_controller.current_user.port}")
        
        # Insert into text area
        text_area.insert(tk.END, "\n".join(info))
        
        # Add refresh button
        ttk.Button(
            debug_window,
            text="Refresh",
            command=lambda: debug_window.destroy() or self.debug_group_info()
        ).pack(pady=10)
        
    def update_group_members_list(self, group_name):
        """Update the list of group members in the UI"""
        if hasattr(self, 'group_members_listbox') and group_name in self.app_controller.group_manager.groups:
            # Clear the listbox
            self.group_members_listbox.delete(0, tk.END)
            
            # Get members from the group manager
            members = self.app_controller.group_manager.get_group_members(group_name)
            
            # Add each member to the listbox
            for member in members:
                self.group_members_listbox.insert(tk.END, member)
                
            # Highlight the current user
            for i in range(self.group_members_listbox.size()):
                if self.group_members_listbox.get(i) == self.app_controller.current_user.username:
                    self.group_members_listbox.itemconfig(i, {'bg': '#e6f0ff'})  # Light blue background
                    break
                
    # Add this method to your GroupMode class
    def debug_shared_directories(self, group_name):
        """Print debug information about shared directories"""
        if not hasattr(self.app_controller, 'group_manager') or not hasattr(self.app_controller.group_manager, 'groups'):
            print(f"Debug - No group manager or groups attribute")
            return
            
        if group_name not in self.app_controller.group_manager.groups:
            print(f"Debug - Group {group_name} not found in group manager")
            return
            
        group_data = self.app_controller.group_manager.groups[group_name]
        print(f"Debug - Group {group_name} data: {group_data}")
        
        if 'shared_dirs' not in group_data:
            print(f"Debug - No shared_dirs key in group {group_name}")
            return
            
        shared_dirs = group_data['shared_dirs']
        print(f"Debug - Shared directories for group {group_name}: {shared_dirs}")
        
        for sharer, directories in shared_dirs.items():
            print(f"Debug - Directories shared by {sharer}: {directories}")