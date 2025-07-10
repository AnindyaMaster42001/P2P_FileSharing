import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import tkinter.simpledialog
import socket
import threading
import json
import os
import hashlib
import base64
from datetime import datetime
import time
import shutil


class User:
    def __init__(self, username, ip, port):
        self.username = username
        self.ip = ip
        self.port = port
        self.is_online = True
        self.last_seen = datetime.now()

class P2PFileSharing:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("P2P File Sharing Application")
        self.root.geometry("800x600")
        
        # User data
        self.current_user = None
        self.users = {}  # {username: User object}
        self.groups = {}  # {group_name: {'members': [usernames], 'shared_dirs': {username: [dir_paths]}}}
        self.group_invites = {}  # {group_name: [pending_invitations]}
        self.temp_messages = []  # Temporary chat messages
        self.all_ports=[x for x in range(12345,12370)]

        # Network settings
        self.server_socket = None
        self.server_port = 12345
        self.is_server_running = False
        
        # UI State
        self.current_mode = "login"
        self.selected_peer = None
        self.selected_group = None
        
        # File transfer notifications
        self.pending_file_requests = {}  # {request_id: file_info}
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Show login screen initially
        self.show_login_screen()
    
    def check_port_availability(self, port):
        """Check if a port is available by trying to bind to it"""
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_socket.bind(('127.0.0.1', port))
            test_socket.close()
            return True
        except:
            return False

    def discover_used_ports(self):
        """Discover which ports are already in use by other P2P users using threading"""
        used_ports = set()
        
        def check_port(port):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.2)  # Reduced timeout to 200ms
                result = sock.connect_ex(('127.0.0.1', port))
                if result == 0:
                    used_ports.add(port)
                sock.close()
            except:
                pass
        
        # Use threading to check ports concurrently
        threads = []
        for port in self.all_ports:
            thread = threading.Thread(target=check_port, args=(port,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete with a reasonable timeout
        for thread in threads:
            thread.join(timeout=0.5)  # 500ms max wait per thread
        
        return used_ports


    def show_login_screen(self):
        self.clear_main_frame()
        
        # Login frame
        login_frame = ttk.LabelFrame(self.main_frame, text="User Authentication", padding=20)
        login_frame.pack(expand=True)
        
        ttk.Label(login_frame, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.username_entry = ttk.Entry(login_frame, width=30)
        self.username_entry.grid(row=0, column=1, pady=5, padx=10)
        
        ttk.Label(login_frame, text="Server Port:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.port_entry = ttk.Entry(login_frame, width=30)
        self.port_entry.insert(0, str(self.server_port))
        self.port_entry.grid(row=1, column=1, pady=5, padx=10)
        
        ttk.Button(login_frame, text="Sign Up / Login", 
                  command=self.login_user).grid(row=2, column=0, columnspan=2, pady=20)
        
        # Bind Enter key to login
        self.root.bind('<Return>', lambda e: self.login_user())
        
    def login_user(self):
        username = self.username_entry.get().strip()
        try:
            requested_port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid port number")
            return
            
        if not username:
            messagebox.showerror("Error", "Please enter a username")
            return
            
        # Check if requested port is already in use by another P2P user
        used_ports = self.discover_used_ports()
        if requested_port in used_ports:
            response = messagebox.askyesno(
                "Port In Use", 
                f"Port {requested_port} is already in use by another P2P user.\n\n"
                f"Would you like to automatically find an available port?",
                icon='warning'
            )
            if not response:
                return
        
        # Start server
        if self.start_server(requested_port):
            # Use the actual port that the server is running on
            self.current_user = User(username, "127.0.0.1", self.server_port)
            self.users[username] = self.current_user
            self.show_home_screen()
            
            # Show a message if we had to use a different port
            if self.server_port != requested_port:
                messagebox.showinfo(
                    "Port Changed", 
                    f"Requested port {requested_port} was unavailable.\n"
                    f"Started server on port {self.server_port} instead."
                )
        else:
            messagebox.showerror("Error", f"Could not start server on any available port starting from {requested_port}")
            
    def start_server(self, port):
        max_attempts = 10
        current_port = port
        
        # Get used ports concurrently (now much faster)
        used_ports = self.discover_used_ports()
        
        for attempt in range(max_attempts):
            # Skip ports that are already in use by other P2P users
            if current_port in used_ports:
                current_port += 1
                continue
                
            try:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.bind(('127.0.0.1', current_port))
                self.server_socket.listen(5)
                self.is_server_running = True
                
                # Update the current user's port to the actual port we're using
                self.server_port = current_port
                
                # Start server thread
                server_thread = threading.Thread(target=self.server_listener, daemon=True)
                server_thread.start()
                
                print(f"Server started on port {current_port}")
                return True
                
            except Exception as e:
                print(f"Server start error on port {current_port}: {e}")
                if self.server_socket:
                    self.server_socket.close()
                current_port += 1
                
        return False
            
    def handle_group_member_joined(self, message):
        """Handle notification that a new member joined a group"""
        group_name = message['group_name']
        new_member = message['new_member']
        updated_members = message['updated_members']
        
        # Update local group member list
        if group_name in self.groups:
            self.groups[group_name]['members'] = updated_members
            
            # Refresh UI if currently viewing this group
            self.root.after_idle(lambda: self.add_temp_message(
                f"{new_member} joined group {group_name}"
            ))
            
            # If currently viewing group details, refresh the member list
            if hasattr(self, 'group_members_listbox'):
                self.root.after_idle(lambda: self.update_group_members_list(group_name))


    def server_listener(self):
        while self.is_server_running:
            try:
                client_socket, address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
            except Exception as e:
                if self.is_server_running:
                    print(f"Server error: {e}")


    def receive_file_chunks(self, client_socket):
        """Receive file data in chunks"""
        try:
            file_info = self.current_file_transfer
            
            with open(file_info['file_path'], 'wb') as f:
                while True:
                    # Read chunk size
                    chunk_size_data = client_socket.recv(4)
                    if not chunk_size_data:
                        break
                        
                    chunk_size = int.from_bytes(chunk_size_data, byteorder='big')
                    
                    # If chunk size is 0, we're done
                    if chunk_size == 0:
                        break
                    
                    # Read chunk data
                    chunk_data = b''
                    while len(chunk_data) < chunk_size:
                        remaining = chunk_size - len(chunk_data)
                        data = client_socket.recv(remaining)
                        if not data:
                            raise Exception("Connection lost during file transfer")
                        chunk_data += data
                    
                    # Write chunk to file
                    f.write(chunk_data)
                    file_info['bytes_received'] += len(chunk_data)
            
            # Send final confirmation
            response = {'status': 'received', 'message': 'File received successfully'}
            client_socket.send(json.dumps(response).encode())
            
            # Show success message
            self.root.after_idle(
                lambda: self.add_temp_message(f"File '{file_info['file_name']}' received from {file_info['sender']} and saved to {file_info['file_path']}")
            )
            
            self.root.after_idle(
                lambda: messagebox.showinfo(
                    "File Received", 
                    f"File '{file_info['file_name']}' from {file_info['sender']}\nSaved to: {file_info['file_path']}"
                )
            )
            
        except Exception as e:
            error_response = {'status': 'error', 'message': str(e)}
            try:
                client_socket.send(json.dumps(error_response).encode())
            except:
                pass
            self.root.after_idle(
                lambda: self.add_temp_message(f"Error receiving file: {str(e)}")
            )
        finally:
            # Clean up
            if hasattr(self, 'current_file_transfer'):
                del self.current_file_transfer

    def handle_client(self, client_socket, address):
        try:
            # Set a timeout for the socket
            client_socket.settimeout(30)
            
            # Read initial data
            data = client_socket.recv(8192)
            if not data:
                return
            
            try:
                # Try to parse as regular JSON message first
                message = json.loads(data.decode())
                
                # Handle file transfer start separately
                if message.get('type') == 'file_transfer_start':
                    response = self.handle_file_transfer_start(message)
                    client_socket.send(json.dumps(response).encode())
                    
                    if response.get('status') == 'ready':
                        # Receive file chunks using the new protocol
                        self.receive_file_chunks(client_socket)
                else:
                    # Handle other message types (discovery, chat, etc.)
                    response = self.process_message(message)
                    if response:
                        client_socket.send(json.dumps(response).encode())
                        
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
            except Exception as e:
                print(f"Message processing error: {e}")
                
        except socket.timeout:
            print("Client socket timeout")
        except Exception as e:
            print(f"Client handling error: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
            
    def process_message(self, message):
        msg_type = message.get('type')
        
        if msg_type == 'discover':
            
            return {
                'type': 'discover_response',
                'username': self.current_user.username,
                'port': self.current_user.port
            }
            
        elif msg_type == 'file_send_request':
            # Handle file send notification
            return self.handle_file_send_request(message)
        
        elif msg_type == 'directory_share':
            # Handle directory share notification
            self.handle_directory_share(message)
            return {'type': 'directory_ack', 'status': 'received'}

        elif msg_type == 'group_member_joined':
            # Handle new member notification
            self.handle_group_member_joined(message)
            return {'type': 'group_ack', 'status': 'received'}
            
        elif msg_type == 'file_send_response':
            # Handle file send response (accepted/rejected)
            self.handle_file_send_response(message)
            return {'type': 'ack', 'status': 'received'}
            
        elif msg_type == 'chat_message':
            # Handle chat message
            self.handle_chat_message(message)
            return {'type': 'chat_ack', 'status': 'received'}
            
        elif msg_type == 'group_invite':
            # Handle group invitation
            self.handle_group_invite(message)
            return {'type': 'group_ack', 'status': 'received'}
            
        return None
            
    def show_home_screen(self):
        self.clear_main_frame()
        
        # Title
        title_label = ttk.Label(self.main_frame, text=f"Welcome, {self.current_user.username}!", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)
        
        # Main content frame
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - User/Group management
        left_panel = ttk.LabelFrame(content_frame, text="Network & Users", padding=10)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Discover peers button
        ttk.Button(left_panel, text="Discover Peers", 
                  command=self.discover_peers).pack(fill=tk.X, pady=5)
        
        # Online users list
        ttk.Label(left_panel, text="Online Users:").pack(anchor=tk.W)
        self.users_listbox = tk.Listbox(left_panel, height=8)
        self.users_listbox.pack(fill=tk.X, pady=5)
        self.users_listbox.bind('<<ListboxSelect>>', self.on_user_select)
        
        # Mode buttons
        mode_frame = ttk.Frame(left_panel)
        mode_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(mode_frame, text="Private Mode", 
                  command=self.show_private_mode).pack(side=tk.LEFT, padx=2)
        ttk.Button(mode_frame, text="Group Mode", 
                  command=self.show_group_mode).pack(side=tk.LEFT, padx=2)
        
        # Right panel - Main functionality
        self.right_panel = ttk.Frame(content_frame)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Show private mode by default
        self.show_private_mode()
        
        # Update user list
        self.update_users_list()
        
    def show_private_mode(self):
        self.clear_right_panel()
        self.current_mode = "private"
        
        # Private mode UI
        private_frame = ttk.LabelFrame(self.right_panel, text="Private Communication", padding=10)
        private_frame.pack(fill=tk.BOTH, expand=True)
        
        # File sending section
        file_frame = ttk.LabelFrame(private_frame, text="File Operations", padding=10)
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(file_frame, text="Send File", 
                  command=self.send_file).pack(side=tk.LEFT, padx=5)
        
        # Status label for file operations
        self.file_status_label = ttk.Label(file_frame, text="Select a peer to send files")
        self.file_status_label.pack(side=tk.LEFT, padx=10)
        
        # Chat section
        chat_frame = ttk.LabelFrame(private_frame, text="Private Chat", padding=10)
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.chat_display = scrolledtext.ScrolledText(chat_frame, height=15, state=tk.DISABLED)
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=5)
        
        chat_input_frame = ttk.Frame(chat_frame)
        chat_input_frame.pack(fill=tk.X, pady=5)
        
        self.chat_entry = ttk.Entry(chat_input_frame)
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(chat_input_frame, text="Send", 
                  command=self.send_chat_message).pack(side=tk.RIGHT)
        
        # Bind Enter key to send message
        self.chat_entry.bind('<Return>', lambda e: self.send_chat_message())
        
        self.update_file_status()



    def setup_create_group_tab(self):
    # Group creation section
        create_frame = ttk.LabelFrame(self.create_group_frame, text="Create New Group", padding=10)
        create_frame.pack(fill=tk.X, pady=5)
        
        # Group name input
        ttk.Label(create_frame, text="Group Name:").pack(anchor=tk.W)
        self.group_name_entry = ttk.Entry(create_frame, width=30)
        self.group_name_entry.pack(fill=tk.X, pady=5)
        
        # Available peers section
        peers_frame = ttk.LabelFrame(self.create_group_frame, text="Select Members", padding=10)
        peers_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(peers_frame, text="Available Peers:").pack(anchor=tk.W)
        
        # Peers listbox with checkboxes (using multiple selection)
        self.create_peers_listbox = tk.Listbox(peers_frame, selectmode=tk.MULTIPLE, height=8)
        self.create_peers_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Buttons frame
        buttons_frame = ttk.Frame(self.create_group_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(buttons_frame, text="Refresh Peers", 
                command=self.refresh_create_peers).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Create Group", 
                command=self.create_group_with_members).pack(side=tk.RIGHT, padx=5)
        
        # Populate peers
        self.refresh_create_peers()

    def setup_my_groups_tab(self):
        # Groups list section
        groups_list_frame = ttk.LabelFrame(self.my_groups_frame, text="My Groups", padding=10)
        groups_list_frame.pack(fill=tk.X, pady=5)
        
        self.my_groups_listbox = tk.Listbox(groups_list_frame, height=6)
        self.my_groups_listbox.pack(fill=tk.X, pady=5)
        self.my_groups_listbox.bind('<<ListboxSelect>>', self.on_my_group_select)
        
        # Group details section
        self.group_details_frame = ttk.LabelFrame(self.my_groups_frame, text="Group Details", padding=10)
        self.group_details_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Initially show placeholder
        self.show_group_placeholder()
        
        # Update groups list
        self.update_my_groups_list()

    def show_group_placeholder(self):
        # Clear existing widgets
        for widget in self.group_details_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(self.group_details_frame, text="Select a group to view details", 
                font=('Arial', 10, 'italic')).pack(expand=True)

    def show_group_details(self, group_name):
        # Clear existing widgets
        for widget in self.group_details_frame.winfo_children():
            widget.destroy()
        
        # Group info
        info_frame = ttk.Frame(self.group_details_frame)
        info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(info_frame, text=f"Group: {group_name}", 
                font=('Arial', 12, 'bold')).pack(anchor=tk.W)
        
        # Members section
        members_frame = ttk.LabelFrame(self.group_details_frame, text="Members", padding=10)
        members_frame.pack(fill=tk.X, pady=5)

        members_list_frame = ttk.Frame(members_frame)
        members_list_frame.pack(fill=tk.X)

        # the Listbox showing current members
        self.group_members_listbox = tk.Listbox(members_list_frame, height=4)
        self.group_members_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # frame for both Add and Refresh buttons
        buttons_frame = ttk.Frame(members_list_frame)
        buttons_frame.pack(side=tk.RIGHT, padx=5)

        # "Add Member" stays as before
        ttk.Button(buttons_frame, text="Add Member",
                   command=lambda: self.add_member_to_group(group_name)).pack(fill=tk.X, pady=2)

        # new "Refresh Members" button
        ttk.Button(buttons_frame, text="Refresh Members",
                   command=lambda: self.update_group_members_list(group_name)).pack(fill=tk.X, pady=2)

        # populate the list initially (so new joiners show up on first view)
        self.update_group_members_list(group_name)
        
        # File operations section
        files_frame = ttk.LabelFrame(self.group_details_frame, text="File Operations", padding=10)
        files_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create notebook for file operations
        files_notebook = ttk.Notebook(files_frame)
        files_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Shared with me tab
        shared_with_me_frame = ttk.Frame(files_notebook)
        files_notebook.add(shared_with_me_frame, text="Shared with Me")
        
        # Share directory tab
        share_dir_frame = ttk.Frame(files_notebook)
        files_notebook.add(share_dir_frame, text="Share Directory")
        
        # Setup shared with me tab
        self.setup_shared_with_me_tab(shared_with_me_frame, group_name)
        
        # Setup share directory tab
        self.setup_share_directory_tab(share_dir_frame, group_name)

    def setup_shared_with_me_tab(self, parent, group_name):
        # Shared directories list
        ttk.Label(parent, text="Directories shared with you:").pack(anchor=tk.W, pady=5)
        
        # Create treeview for directories and files
        self.shared_dirs_tree = ttk.Treeview(parent, columns=('Size', 'Sharer'), show='tree headings')
        self.shared_dirs_tree.heading('#0', text='Name')
        self.shared_dirs_tree.heading('Size', text='Size')
        self.shared_dirs_tree.heading('Sharer', text='Shared By')
        self.shared_dirs_tree.column('#0', width=200)
        self.shared_dirs_tree.column('Size', width=80)
        self.shared_dirs_tree.column('Sharer', width=100)
        
        self.shared_dirs_tree.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Download button
        download_frame = ttk.Frame(parent)
        download_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(download_frame, text="Download Selected", 
                command=lambda: self.download_from_group_new(group_name)).pack(side=tk.RIGHT)
        
        # Populate shared directories
        self.update_shared_directories(group_name)

    def setup_share_directory_tab(self, parent, group_name):
        # Directory selection
        dir_frame = ttk.Frame(parent)
        dir_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(dir_frame, text="Select directory to share:").pack(anchor=tk.W)
        
        self.share_dir_entry = ttk.Entry(dir_frame)
        self.share_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(dir_frame, text="Browse", 
                command=self.browse_directory_to_share).pack(side=tk.RIGHT)
        
        # Members to share with
        members_frame = ttk.LabelFrame(parent, text="Share with members:", padding=10)
        members_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.share_members_listbox = tk.Listbox(members_frame, selectmode=tk.MULTIPLE)
        self.share_members_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Share button
        share_frame = ttk.Frame(parent)
        share_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(share_frame, text="Share Directory", 
                command=lambda: self.share_directory_to_group(group_name)).pack(side=tk.RIGHT)
        
        # Populate members for sharing
        self.update_share_members_list(group_name)

    def refresh_create_peers(self):
        self.create_peers_listbox.delete(0, tk.END)
        for username in self.users:
            if username != self.current_user.username:
                self.create_peers_listbox.insert(tk.END, username)

    def create_group_with_members(self):
        group_name = self.group_name_entry.get().strip()
        if not group_name:
            messagebox.showwarning("Warning", "Please enter a group name")
            return
        
        # Check if group name already exists
        if group_name in self.groups:
            messagebox.showerror("Error", "Group name already exists. Please choose a different name.")
            return
        
        # Get selected members
        selected_indices = self.create_peers_listbox.curselection()
        selected_members = [self.create_peers_listbox.get(i) for i in selected_indices]
        
        if not selected_members:
            messagebox.showwarning("Warning", "Please select at least one member")
            return
        
        # Create group
        self.groups[group_name] = {
            'members': [self.current_user.username] + selected_members,
            'shared_dirs': {}
        }
        
        # Send group invitations to selected members
        self.send_group_invitations(group_name, selected_members)
        
        # Clear form
        self.group_name_entry.delete(0, tk.END)
        self.create_peers_listbox.selection_clear(0, tk.END)
        
        # Update my groups list
        self.update_my_groups_list()
        
        # Switch to My Groups tab
        self.group_notebook.select(self.my_groups_frame)
        
        messagebox.showinfo("Success", f"Group '{group_name}' created successfully!")

    def send_group_invitations(self, group_name, members):
        """Send group invitations to selected members"""
        # Get current member list to include in invitation
        current_members = self.groups[group_name]['members'].copy()
        
        for member in members:
            if member in self.users:
                try:
                    peer = self.users[member]
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10)
                    sock.connect((peer.ip, peer.port))
                    
                    invitation = {
                        'type': 'group_invite',
                        'group_name': group_name,
                        'inviter': self.current_user.username,
                        'members': current_members,  # Include full member list
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    sock.send(json.dumps(invitation).encode())
                    sock.close()
                    
                except Exception as e:
                    print(f"Error sending invitation to {member}: {e}")


    def on_group_tab_changed(self, event):
        """Handle tab change events"""
        selected_tab = self.group_notebook.select()
        tab_text = self.group_notebook.tab(selected_tab, "text")
        
        if tab_text == "My Groups":
            self.update_my_groups_list()

    def on_my_group_select(self, event):
        selection = self.my_groups_listbox.curselection()
        if selection:
            group_name = self.my_groups_listbox.get(selection[0])
            self.show_group_details(group_name)

    def update_my_groups_list(self):
        if hasattr(self, 'my_groups_listbox'):
            self.my_groups_listbox.delete(0, tk.END)
            for group_name in self.groups:
                # Only show groups where current user is a member
                if self.current_user.username in self.groups[group_name]['members']:
                    self.my_groups_listbox.insert(tk.END, group_name)

    def update_group_members_list(self, group_name):
        if hasattr(self, 'group_members_listbox') and group_name in self.groups:
            self.group_members_listbox.delete(0, tk.END)
            for member in self.groups[group_name]['members']:
                self.group_members_listbox.insert(tk.END, member)

    def add_member_to_group(self, group_name):
        # Get available peers (not already in group)
        current_members = self.groups[group_name]['members']
        available_peers = [user for user in self.users if user not in current_members and user != self.current_user.username]
        
        if not available_peers:
            messagebox.showinfo("Info", "No available peers to add")
            return
        
        # Create selection dialog
        selection_window = tk.Toplevel(self.root)
        selection_window.title("Add Member to Group")
        selection_window.geometry("300x400")
        selection_window.transient(self.root)
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
                # Add to group
                self.groups[group_name]['members'].append(selected_member)
                # Send invitation
                self.send_group_invitations(group_name, [selected_member])
                # Update display
                self.update_group_members_list(group_name)
                self.update_share_members_list(group_name)
                selection_window.destroy()
                messagebox.showinfo("Success", f"Added {selected_member} to group {group_name}")
            else:
                messagebox.showwarning("Warning", "Please select a member")
        
        ttk.Button(button_frame, text="Add", command=add_selected_member).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=selection_window.destroy).pack(side=tk.RIGHT)

    def update_share_members_list(self, group_name):
        if hasattr(self, 'share_members_listbox') and group_name in self.groups:
            self.share_members_listbox.delete(0, tk.END)
            for member in self.groups[group_name]['members']:
                if member != self.current_user.username:
                    self.share_members_listbox.insert(tk.END, member)

    def browse_directory_to_share(self):
        directory = filedialog.askdirectory()
        if directory:
            self.share_dir_entry.delete(0, tk.END)
            self.share_dir_entry.insert(0, directory)

    def share_directory_to_group(self, group_name):
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
        
        # Add to group's shared directories
        if self.current_user.username not in self.groups[group_name]['shared_dirs']:
            self.groups[group_name]['shared_dirs'][self.current_user.username] = []
        
        # Check if directory already shared
        if directory not in self.groups[group_name]['shared_dirs'][self.current_user.username]:
            self.groups[group_name]['shared_dirs'][self.current_user.username].append(directory)
        
        # Send share notifications to selected members
        self.send_directory_share_notifications(group_name, directory, selected_members)
        
        # Clear form
        self.share_dir_entry.delete(0, tk.END)
        self.share_members_listbox.selection_clear(0, tk.END)
        
        messagebox.showinfo("Success", f"Directory shared with selected members of {group_name}")

    def send_directory_share_notifications(self, group_name, directory, members):
        """Send directory share notifications to group members"""
        for member in members:
            if member in self.users:
                try:
                    peer = self.users[member]
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10)
                    sock.connect((peer.ip, peer.port))
                    
                    notification = {
                        'type': 'directory_share',
                        'group_name': group_name,
                        'directory': directory,
                        'sharer': self.current_user.username,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    sock.send(json.dumps(notification).encode())
                    sock.close()
                    
                except Exception as e:
                    print(f"Error sending directory share notification to {member}: {e}")

    def update_shared_directories(self, group_name):
        if hasattr(self, 'shared_dirs_tree') and group_name in self.groups:
            # Clear existing items
            for item in self.shared_dirs_tree.get_children():
                self.shared_dirs_tree.delete(item)
            
            # Add shared directories
            shared_dirs = self.groups[group_name]['shared_dirs']
            for sharer, directories in shared_dirs.items():
                if sharer != self.current_user.username:  # Don't show own shared directories
                    for directory in directories:
                        if os.path.exists(directory):
                            # Add directory node
                            dir_node = self.shared_dirs_tree.insert('', 'end', text=os.path.basename(directory), 
                                                                values=('Directory', sharer), tags=('directory',))
                            
                            # Add files in directory
                            try:
                                for file_name in os.listdir(directory):
                                    file_path = os.path.join(directory, file_name)
                                    if os.path.isfile(file_path):
                                        file_size = self.format_file_size(os.path.getsize(file_path))
                                        self.shared_dirs_tree.insert(dir_node, 'end', text=file_name, 
                                                                    values=(file_size, sharer), tags=('file',))
                            except PermissionError:
                                self.shared_dirs_tree.insert(dir_node, 'end', text="Permission Denied", 
                                                            values=('', sharer), tags=('error',))

    def download_from_group_new(self, group_name):
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
        shared_dirs = self.groups[group_name]['shared_dirs']
        if sharer in shared_dirs:
            for directory in shared_dirs[sharer]:
                if os.path.basename(directory) == dir_name:
                    file_path = os.path.join(directory, file_name)
                    if os.path.exists(file_path):
                        # Copy file to downloads
                        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads", "P2P_Group_Files")
                        os.makedirs(downloads_dir, exist_ok=True)
                        
                        import shutil
                        dest_path = os.path.join(downloads_dir, file_name)
                        
                        # Handle filename conflicts
                        counter = 1
                        base_name, ext = os.path.splitext(file_name)
                        while os.path.exists(dest_path):
                            dest_path = os.path.join(downloads_dir, f"{base_name}_{counter}{ext}")
                            counter += 1
                        
                        try:
                            shutil.copy2(file_path, dest_path)
                            messagebox.showinfo("Success", f"File downloaded to: {dest_path}")
                        except Exception as e:
                            messagebox.showerror("Error", f"Failed to download file: {str(e)}")
                        return
        
        messagebox.showerror("Error", "File not found or access denied")




    def show_group_mode(self):
        self.clear_right_panel()
        self.current_mode = "group"
        
        # Main group container
        main_group_frame = ttk.Frame(self.right_panel)
        main_group_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create notebook for tabs
        self.group_notebook = ttk.Notebook(main_group_frame)
        self.group_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create Group Tab
        self.create_group_frame = ttk.Frame(self.group_notebook)
        self.group_notebook.add(self.create_group_frame, text="Create Group")
        
        # My Groups Tab
        self.my_groups_frame = ttk.Frame(self.group_notebook)
        self.group_notebook.add(self.my_groups_frame, text="My Groups")
        
        # Setup Create Group tab
        self.setup_create_group_tab()
        
        # Setup My Groups tab
        self.setup_my_groups_tab()
        
        # Bind tab change event
        self.group_notebook.bind("<<NotebookTabChanged>>", self.on_group_tab_changed)
        
    def send_file(self):
        if not self.selected_peer:
            messagebox.showwarning("Warning", "Please select a peer first")
            return
            
        # Select file to send
        file_path = filedialog.askopenfilename(
            title="Select file to send",
            filetypes=[("All files", "*.*")]
        )
        
        if not file_path:
            return
            
        # Get file info
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        # Generate unique request ID
        request_id = hashlib.md5(f"{self.current_user.username}_{file_name}_{datetime.now().isoformat()}".encode()).hexdigest()
        
        # Send file send request to peer
        try:
            peer = self.users[self.selected_peer]
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((peer.ip, peer.port))
            
            request = {
                'type': 'file_send_request',
                'request_id': request_id,
                'sender': self.current_user.username,
                'file_name': file_name,
                'file_size': file_size,
                'timestamp': datetime.now().isoformat()
            }
            
            sock.send(json.dumps(request).encode())
            
            # Wait for response
            response = sock.recv(1024)
            if response:
                response_data = json.loads(response.decode())
                if response_data.get('status') == 'notification_sent':
                    # Store file info for later transfer
                    self.pending_file_requests[request_id] = {
                        'file_path': file_path,
                        'file_name': file_name,
                        'file_size': file_size,
                        'peer': self.selected_peer
                    }
                    self.add_temp_message(f"File send request sent to {self.selected_peer}")
                    self.update_file_status()
                    
            sock.close()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send file request: {str(e)}")
            
    def handle_file_send_request(self, message):
        request_id = message['request_id']
        sender = message['sender']
        file_name = message['file_name']
        file_size = message['file_size']
        
        # Store the request with sender info for later use
        self.pending_file_requests[request_id] = {
            'sender': sender,
            'file_name': file_name,
            'file_size': file_size,
            'type': 'incoming_request'
        }
        
        # Show notification dialog to user
        self.root.after_idle(self.show_file_notification, request_id, sender, file_name, file_size)
        
        return {'status': 'notification_sent'}
        
    def show_file_notification(self, request_id, sender, file_name, file_size):
        # Format file size
        size_str = self.format_file_size(file_size)
        
        # Create notification dialog
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
        try:
            # If sender is not in our users list, we need to extract their info from the request
            if sender not in self.users:
                # We need to get the sender's connection info from the original request
                # For now, we'll try to connect back using the same IP and scan for their port
                sender_ip = "127.0.0.1"  # In a real P2P network, this would come from the request
                sender_port = None
                
                # Try to find the sender's port by scanning common ports
                for port in self.all_ports:
                    try:
                        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        test_sock.settimeout(2)
                        test_sock.connect((sender_ip, port))
                        
                        # Send discovery message to verify this is the sender
                        discover_msg = {'type': 'discover', 'username': self.current_user.username}
                        test_sock.send(json.dumps(discover_msg).encode())
                        
                        response = test_sock.recv(1024)
                        if response:
                            peer_info = json.loads(response.decode())
                            if peer_info.get('username') == sender:
                                sender_port = port
                                # Add sender to our users list
                                self.users[sender] = User(sender, sender_ip, sender_port)
                                test_sock.close()
                                break
                        test_sock.close()
                    except:
                        continue
                
                if sender_port is None:
                    print(f"Could not find sender {sender} to send response")
                    return
            
            peer = self.users[sender]
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((peer.ip, peer.port))
            
            response = {
                'type': 'file_send_response',
                'request_id': request_id,
                'sender': self.current_user.username,
                'accepted': accepted,
                'timestamp': datetime.now().isoformat()
            }
            
            sock.send(json.dumps(response).encode())
            sock.close()
            
            if accepted:
                self.add_temp_message(f"Accepted file transfer from {sender}")
            else:
                self.add_temp_message(f"Rejected file transfer from {sender}")
                
        except Exception as e:
            print(f"Error sending file response: {e}")
            
    def handle_file_send_response(self, message):
        request_id = message['request_id']
        sender = message['sender']
        accepted = message['accepted']
        
        if request_id in self.pending_file_requests:
            file_info = self.pending_file_requests[request_id]
            
            if accepted:
                # Add a small delay to ensure the receiver is ready
                self.root.after(1000, self.start_file_transfer, request_id, sender, file_info)
            else:
                # Remove from pending requests
                del self.pending_file_requests[request_id]
                self.add_temp_message(f"{sender} rejected the file transfer")
                self.update_file_status()

    def handle_file_transfer_start(self, message):
        """Handle the start of a chunked file transfer"""
        sender = message['sender']
        file_name = message['file_name']
        file_size = message['file_size']
        
        try:
            # Create downloads directory if it doesn't exist
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads", "P2P_Files")
            os.makedirs(downloads_dir, exist_ok=True)
            
            # Generate unique filename to avoid conflicts
            base_name, ext = os.path.splitext(file_name)
            counter = 1
            save_path = os.path.join(downloads_dir, file_name)
            
            while os.path.exists(save_path):
                save_path = os.path.join(downloads_dir, f"{base_name}_{counter}{ext}")
                counter += 1
            
            # Store file info for chunked receiving
            self.current_file_transfer = {
                'file_path': save_path,
                'file_name': file_name,
                'file_size': file_size,
                'sender': sender,
                'bytes_received': 0
            }
            
            return {'status': 'ready', 'message': 'Ready to receive file'}
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def start_file_transfer(self, request_id, receiver, file_info):
        def transfer_file():
            try:
                # Send file header first
                peer = self.users[receiver]
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(30)
                sock.connect((peer.ip, peer.port))
                
                # Send file transfer header as regular JSON
                header = {
                    'type': 'file_transfer_start',
                    'request_id': request_id,
                    'sender': self.current_user.username,
                    'file_name': file_info['file_name'],
                    'file_size': file_info['file_size'],
                    'timestamp': datetime.now().isoformat()
                }
                
                sock.send(json.dumps(header).encode())
                
                # Wait for ready signal
                response = sock.recv(1024)
                if response:
                    response_data = json.loads(response.decode())
                    if response_data.get('status') != 'ready':
                        raise Exception(f"Receiver not ready: {response_data.get('message', 'Unknown error')}")
                
                # Send file data in chunks
                chunk_size = 8192
                with open(file_info['file_path'], 'rb') as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        
                        # Send chunk size first, then chunk data
                        sock.send(len(chunk).to_bytes(4, byteorder='big'))
                        sock.send(chunk)
                    
                    # Send end signal (0 bytes)
                    sock.send((0).to_bytes(4, byteorder='big'))
                
                # Wait for final confirmation
                response = sock.recv(1024)
                if response:
                    response_data = json.loads(response.decode())
                    if response_data.get('status') == 'received':
                        self.root.after_idle(
                            lambda: self.add_temp_message(f"File '{file_info['file_name']}' sent successfully to {receiver}")
                        )
                    else:
                        self.root.after_idle(
                            lambda: self.add_temp_message(f"File transfer failed: {response_data.get('message', 'Unknown error')}")
                        )
                
                sock.close()
                    
            except Exception as e:
                self.root.after_idle(
                    lambda: self.add_temp_message(f"Error sending file: {str(e)}")
                )
                
            # Remove from pending requests
            if request_id in self.pending_file_requests:
                del self.pending_file_requests[request_id]
            self.root.after_idle(self.update_file_status)
        
        # Run file transfer in separate thread
        transfer_thread = threading.Thread(target=transfer_file, daemon=True)
        transfer_thread.start()
            
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f} {size_names[i]}"
        
    def update_file_status(self):
        if hasattr(self, 'file_status_label'):
            if self.selected_peer:
                pending_count = len(self.pending_file_requests)
                if pending_count > 0:
                    self.file_status_label.config(text=f"Selected: {self.selected_peer} | {pending_count} pending transfer(s)")
                else:
                    self.file_status_label.config(text=f"Selected: {self.selected_peer} | Ready to send files")
            else:
                self.file_status_label.config(text="Select a peer to send files")
        
    def discover_peers(self):
    # Simple peer discovery - try common ports on local network
        discovered_peers = []
        
        def scan_port(ip, port):
            # Skip our own port to avoid connecting to ourselves
            if port == self.current_user.port:
                return
                
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((ip, port))
                if result == 0:
                    # Send discovery message with our port and IP info
                    message = {
                        'type': 'discover', 
                        'username': self.current_user.username,
                        'port': self.current_user.port,
                        'ip': self.current_user.ip
                    }
                    sock.send(json.dumps(message).encode())
                    
                    # Wait for response
                    sock.settimeout(5)
                    response = sock.recv(1024)
                    if response:
                        peer_info = json.loads(response.decode())
                        if peer_info.get('username') != self.current_user.username:
                            discovered_peers.append(peer_info)
                        
                sock.close()
            except Exception as e:
                print(f"Discovery error for port {port}: {e}")
                
        # Scan local network (simplified)
        base_ip = "127.0.0.1"
        
        threads = []
        for port in self.all_ports:
            t = threading.Thread(target=scan_port, args=(base_ip, port))
            threads.append(t)
            t.start()
                
        # Wait for all threads to complete
        for t in threads:
            t.join()
            
        # Add discovered peers to existing users (don't replace current user)
        for peer in discovered_peers:
            if peer['username'] not in self.users:
                self.users[peer['username']] = User(
                    peer['username'], 
                    "127.0.0.1", 
                    peer['port']
                )
            
        # Clear selected peer if it's no longer available
        if self.selected_peer and self.selected_peer not in self.users:
            self.selected_peer = None
            
        self.update_users_list()
        self.update_file_status()  # Update file status to reflect peer selection changes
        messagebox.showinfo("Discovery", f"Found {len(discovered_peers)} peers")
            
    def send_chat_message(self):
        message = self.chat_entry.get().strip()
        if not message or not self.selected_peer:
            if not message:
                messagebox.showwarning("Warning", "Please enter a message")
            else:
                messagebox.showwarning("Warning", "Please select a peer first")
            return
            
        try:
            peer = self.users[self.selected_peer]
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((peer.ip, peer.port))
            
            chat_message = {
                'type': 'chat_message',
                'sender': self.current_user.username,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
            
            sock.send(json.dumps(chat_message).encode())
            
            # Wait for acknowledgment
            ack = sock.recv(1024)
            if ack:
                ack_data = json.loads(ack.decode())
                if ack_data.get('status') == 'received':
                    # Add to local chat display
                    self.add_temp_message(f"You: {message}")
                    self.chat_entry.delete(0, tk.END)
                    
            sock.close()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send message: {str(e)}")
            
    def handle_chat_message(self, message):
        sender = message['sender']
        msg_text = message['message']
        timestamp = message['timestamp']
        
        # Add to temporary messages
        self.add_temp_message(f"{sender}: {msg_text}")
        
    def handle_group_invite(self, message):
        group_name = message['group_name']
        inviter = message['inviter']

        # Store the invitation data for later use
        self._last_group_invitation = message

        # Show invitation dialog
        self.root.after_idle(self.show_group_invitation, group_name, inviter)


    def notify_group_members_new_joiner(self, group_name, inviter):
        """Notify existing group members that someone new has joined"""
        if group_name not in self.groups:
            return
        
        # Send notification to all members except the inviter and yourself
        for member in self.groups[group_name]['members']:
            if member != self.current_user.username and member != inviter and member in self.users:
                try:
                    peer = self.users[member]
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10)
                    sock.connect((peer.ip, peer.port))
                    
                    notification = {
                        'type': 'group_member_joined',
                        'group_name': group_name,
                        'new_member': self.current_user.username,
                        'updated_members': self.groups[group_name]['members'],
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    sock.send(json.dumps(notification).encode())
                    sock.close()
                    
                except Exception as e:
                    print(f"Error notifying {member} about new group member: {e}")


    def show_group_invitation(self, group_name, inviter):
        result = messagebox.askyesno(
            "Group Invitation",
            f"{inviter} has invited you to join the group '{group_name}'\n\n"
            f"Do you want to accept this invitation?",
            icon='question'
        )
        if not result:
            messagebox.showinfo("Info", f"Group invitation from {inviter} declined")
            return

        # Get the invitation details from the most recent invite
        invitation_data = None
        if hasattr(self, '_last_group_invitation'):
            invitation_data = self._last_group_invitation
        
        # Create or update the group with full member list
        if group_name not in self.groups:
            self.groups[group_name] = {'members': [], 'shared_dirs': {}}
        
        # If we have invitation data with member list, use it
        if invitation_data and 'members' in invitation_data:
            # Use the complete member list from invitation
            self.groups[group_name]['members'] = invitation_data['members'].copy()
            # Add yourself if not already in the list
            if self.current_user.username not in self.groups[group_name]['members']:
                self.groups[group_name]['members'].append(self.current_user.username)
        else:
            # Fallback: just add inviter and yourself
            members = self.groups[group_name]['members']
            if inviter not in members:
                members.append(inviter)
            if self.current_user.username not in members:
                members.append(self.current_user.username)
        
        # Notify existing group members about the new joiner
        self.notify_group_members_new_joiner(group_name, inviter)
        
        # Refresh UI
        self.update_my_groups_list()
        messagebox.showinfo("Success", f"You have joined the group '{group_name}'")


        

    def handle_directory_share(self, message):
        group_name = message['group_name']
        directory = message['directory']
        sharer = message['sharer']
        
        # Update group's shared directories
        if group_name in self.groups:
            if sharer not in self.groups[group_name]['shared_dirs']:
                self.groups[group_name]['shared_dirs'][sharer] = []
            
            if directory not in self.groups[group_name]['shared_dirs'][sharer]:
                self.groups[group_name]['shared_dirs'][sharer].append(directory)
        
         # Show notification and refresh the Shared-with-Me view
        self.root.after_idle(lambda: self.add_temp_message(
            f"{sharer} shared a directory with group {group_name}"
        ))
        self.root.after_idle(lambda: self.update_shared_directories(group_name))


    def add_temp_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        self.temp_messages.append(full_message)
        
        # Update chat display if in private mode
        if self.current_mode == "private" and hasattr(self, 'chat_display'):
            # Use after_idle to ensure thread-safe GUI updates
            self.root.after_idle(self.update_chat_display, full_message)
            
    def update_chat_display(self, message):
        if hasattr(self, 'chat_display'):
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, message + "\n")
            self.chat_display.config(state=tk.DISABLED)
            self.chat_display.see(tk.END)
            
    # def create_group(self):
    #     group_name = tk.simpledialog.askstring("Create Group", "Enter group name:")
    #     if group_name:
    #         self.groups[group_name] = [self.current_user.username]
    #         self.update_groups_list()
    #         messagebox.showinfo("Success", f"Group '{group_name}' created")
            
    # def join_group(self):
    #     # Simplified group joining - in real implementation, this would involve
    #     # network communication to find and join existing groups
    #     group_name = tk.simpledialog.askstring("Join Group", "Enter group name:")
    #     if group_name:
    #         if group_name not in self.groups:
    #             self.groups[group_name] = []
    #         if self.current_user.username not in self.groups[group_name]:
    #             self.groups[group_name].append(self.current_user.username)
    #             self.update_groups_list()
    #             messagebox.showinfo("Success", f"Joined group '{group_name}'")
    #         else:
    #             messagebox.showinfo("Info", "Already in this group")
                
    # def share_to_group(self):
    #     if not self.selected_group:
    #         messagebox.showwarning("Warning", "Please select a group first")
    #         return
            
    #     directory = filedialog.askdirectory()
    #     if directory:
    #         # In a real implementation, this would sync the directory with group members
    #         messagebox.showinfo("Success", f"Directory shared to group '{self.selected_group}'")
            
    # def download_from_group(self):
    #     if not self.selected_group:
    #         messagebox.showwarning("Warning", "Please select a group first")
    #         return
            
    #     # In a real implementation, this would show files available from group members
    #     messagebox.showinfo("Info", "Group file download feature - to be implemented")
        
    def on_user_select(self, event):
        selection = self.users_listbox.curselection()
        if selection:
            self.selected_peer = self.users_listbox.get(selection[0])
            self.update_file_status()
            
    def on_group_select(self, event):
        selection = self.groups_listbox.curselection()
        if selection:
            self.selected_group = self.groups_listbox.get(selection[0])
            
    def update_users_list(self):
        if hasattr(self, 'users_listbox'):
            self.users_listbox.delete(0, tk.END)
            for username in self.users:
                if username != self.current_user.username:
                    self.users_listbox.insert(tk.END, username)
                    
    def update_groups_list(self):
        # This method is now handled by update_my_groups_list
        pass
                
    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
            
    def clear_right_panel(self):
        for widget in self.right_panel.winfo_children():
            widget.destroy()
            
    def on_closing(self):
        self.is_server_running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        self.root.destroy()
        
    def run(self):
        """Main application loop"""
        # Set up window closing protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start the GUI event loop
        self.root.mainloop()

def main():
    """Main entry point for the application"""
    app = P2PFileSharing()
    app.run()

if __name__ == "__main__":
    main()