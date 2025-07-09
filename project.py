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
        self.groups = {}  # {group_name: [usernames]}
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
        
    def show_group_mode(self):
        self.clear_right_panel()
        self.current_mode = "group"
        
        # Group mode UI
        group_frame = ttk.LabelFrame(self.right_panel, text="Group File Sharing", padding=10)
        group_frame.pack(fill=tk.BOTH, expand=True)
        
        # Group management
        group_mgmt_frame = ttk.LabelFrame(group_frame, text="Group Management", padding=10)
        group_mgmt_frame.pack(fill=tk.X, pady=5)
        
        group_buttons_frame = ttk.Frame(group_mgmt_frame)
        group_buttons_frame.pack(fill=tk.X)
        
        ttk.Button(group_buttons_frame, text="Create Group", 
                  command=self.create_group).pack(side=tk.LEFT, padx=5)
        ttk.Button(group_buttons_frame, text="Join Group", 
                  command=self.join_group).pack(side=tk.LEFT, padx=5)
        
        # Groups list
        ttk.Label(group_frame, text="My Groups:").pack(anchor=tk.W, pady=(10, 0))
        self.groups_listbox = tk.Listbox(group_frame, height=4)
        self.groups_listbox.pack(fill=tk.X, pady=5)
        self.groups_listbox.bind('<<ListboxSelect>>', self.on_group_select)
        
        # Group shared directories
        ttk.Label(group_frame, text="Group Shared Directories:").pack(anchor=tk.W, pady=(10, 0))
        self.group_shared_dirs_listbox = tk.Listbox(group_frame, height=4)
        self.group_shared_dirs_listbox.pack(fill=tk.X, pady=5)
        
        # File operations for groups
        group_file_frame = ttk.Frame(group_frame)
        group_file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(group_file_frame, text="Share to Group", 
                  command=self.share_to_group).pack(side=tk.LEFT, padx=5)
        ttk.Button(group_file_frame, text="Download from Group", 
                  command=self.download_from_group).pack(side=tk.LEFT, padx=5)
        
        self.update_groups_list()
        
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
        # Handle group invitation - placeholder for now
        pass
        
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
            
    def create_group(self):
        group_name = tk.simpledialog.askstring("Create Group", "Enter group name:")
        if group_name:
            self.groups[group_name] = [self.current_user.username]
            self.update_groups_list()
            messagebox.showinfo("Success", f"Group '{group_name}' created")
            
    def join_group(self):
        # Simplified group joining - in real implementation, this would involve
        # network communication to find and join existing groups
        group_name = tk.simpledialog.askstring("Join Group", "Enter group name:")
        if group_name:
            if group_name not in self.groups:
                self.groups[group_name] = []
            if self.current_user.username not in self.groups[group_name]:
                self.groups[group_name].append(self.current_user.username)
                self.update_groups_list()
                messagebox.showinfo("Success", f"Joined group '{group_name}'")
            else:
                messagebox.showinfo("Info", "Already in this group")
                
    def share_to_group(self):
        if not self.selected_group:
            messagebox.showwarning("Warning", "Please select a group first")
            return
            
        directory = filedialog.askdirectory()
        if directory:
            # In a real implementation, this would sync the directory with group members
            messagebox.showinfo("Success", f"Directory shared to group '{self.selected_group}'")
            
    def download_from_group(self):
        if not self.selected_group:
            messagebox.showwarning("Warning", "Please select a group first")
            return
            
        # In a real implementation, this would show files available from group members
        messagebox.showinfo("Info", "Group file download feature - to be implemented")
        
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
        if hasattr(self, 'groups_listbox'):
            self.groups_listbox.delete(0, tk.END)
            for group_name in self.groups:
                self.groups_listbox.insert(tk.END, group_name)
                
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