import logging
import socket
import threading
import json
from datetime import datetime
from tkinter import ttk, messagebox
from Backend.user import User
from Backend.network import NetworkManager
from Backend.file_manager import FileManager
from Backend.group import GroupManager
from Backend.supabase import SupabaseAuth
from Backend.utils import setup_logger, get_app_version
from tkinter import ttk, messagebox
from Backend.Message_Handler import MessageHandler
import time
logger = logging.getLogger(__name__)

class AppController:
    def __init__(self):
        # Initialize logger
        setup_logger()
        logger.info(f"Starting P2P File Sharing App v{get_app_version()}")
        
        # Backend components
        self.network = NetworkManager(self)
        self.file_manager = FileManager(self)
        self.group_manager = GroupManager(self)
        self.auth = SupabaseAuth()  # Initialize Supabase auth
        self.message_handler = MessageHandler(self)  # Add this line
        
        # State
          # State
        self.current_user = None
        self.users = {}  # {username: User object}
        self.temp_messages = []  # Temporary chat messages
        self.auth_user = None  # Store authenticated user from Supabase
        
        # UI references (will be set by UI components)
        self.main_window = None
        
        # Initialize mode and selections
        self.current_mode = "login"
        self.selected_peer = None
        self.selected_group = None
        
    def sign_up_user(self, email, password):
        """Sign up a new user with Supabase"""
        try:
            success, user = self.auth.sign_up(email, password)
            if success:
                self.auth_user = user
                logger.info(f"User signed up: {email}")
            return success, user
        except Exception as e:
            logger.error(f"Sign up error: {e}")
            return False, str(e)
    def sign_in_user(self, email, password):
        """Sign in existing user with Supabase"""
        try:
            success, user = self.auth.sign_in(email, password)
            if success:
                self.auth_user = user
                logger.info(f"User signed in: {email}")
            return success, user
        except Exception as e:
            logger.error(f"Sign in error: {e}")
            return False, str(e)
    
    def login_user(self, username, auth_user=None):
        """Log in a user and start the server with automatic port assignment"""
        if not username:
            return False, "Please enter a username"
        
        if auth_user is None and self.auth_user is None:
            return False, "Authentication required"
        
        # Use auth_user if provided, or use the stored one
        if auth_user:
            self.auth_user = auth_user
        
        # Check if username is already taken in the current session
        for user_id, user in self.users.items():
            if user_id != username and user.username.lower() == username.lower():
                return False, "Username is already taken by another user. Please choose a different username."

        # Get saved port from user profile or use default port range
        user_profile = self.get_user_profile()
        start_port = user_profile.get('last_port', 12345) if user_profile else 12345
        
        # Try to start server with automatic port assignment
        try:
            server_port = self.network.start_server(start_port)
            if not server_port:
                return False, "Could not start server. Network may be unavailable."
            
            # Get local IP (with fallback to localhost if there's an error)
            local_ip = getattr(self.network, 'local_ip', '127.0.0.1')
            
            # Create user with network IP address
            self.current_user = User(username, local_ip, server_port)
            self.users[username] = self.current_user
            
            # Update user profile with the newly assigned port
            self.update_user_profile(username, server_port)
            
            logger.info(f"User {username} logged in on {local_ip}:{server_port}")
            
            return True, server_port
        except Exception as e:
            logger.error(f"Error logging in user: {e}")
            return False, f"Login error: {str(e)}"   
    
    def get_user_profile(self):
        """Get user profile from Supabase"""
        if not self.auth_user:
            return None
            
        try:
            # Query the profiles table for this user
            user_id = self.auth_user.id
            profile = self.auth.get_profile(user_id)
            
            if profile:
                return profile
            else:
                # Profile should be created automatically by the database trigger
                # But if it's not there, we'll return a default
                return {
                    'id': user_id,
                    'username': '',
                    'last_port': 12345,
                    'created_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None 
    
    
    def update_user_profile(self, username, port):
        """Update user profile in Supabase"""
        if not self.auth_user:
            return False
            
        try:
            user_id = self.auth_user.id
            updates = {
                'username': username,
                'last_port': port,
                'last_login': datetime.now().isoformat()
            }
            
            self.auth.update_profile(user_id, updates)
            return True
            
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            return False
    
    def discover_peers(self):
        """Discover peers on the network"""
        discovered_peers = self.network.discover_peers(self.current_user)
        
        # Add discovered peers to existing users
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
            
        return len(discovered_peers)
    
    def process_message(self, message):
        """Process incoming messages"""
        msg_type = message.get('type')
        sender = message.get('sender', 'unknown')
        
        # Debug log
        logger.debug(f"Processing message type: {msg_type} from {sender}")
        
        # First have the message handler process it (you can keep this if needed)
        if hasattr(self, 'message_handler'):
            self.message_handler.process_message(message, sender)
        
        # Then handle the basic network-level messages
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
            # Handle group invitation (legacy method - keep for compatibility)
            self.handle_group_invite(message)
            return {'type': 'group_ack', 'status': 'received'}
        
        elif msg_type == 'group_invitation':
            # Handle group invitation
            group_name = message.get('group')
            from_user = message.get('from', sender)
            
            logger.info(f"Received group invitation from {from_user} for group '{group_name}'")
            
            # Store the invitation
            if not hasattr(self.group_manager, 'received_invitations'):
                self.group_manager.received_invitations = []
            
            # Check if invitation already exists
            invitation_exists = False
            for inv in self.group_manager.received_invitations:
                if inv.get('group') == group_name and inv.get('from') == from_user:
                    invitation_exists = True
                    break
            
            if not invitation_exists:
                # Add to received invitations
                self.group_manager.received_invitations.append({
                    'group': group_name,
                    'from': from_user,
                    'timestamp': message.get('timestamp', time.time())
                })
                
                # Show invitation dialog
                if self.main_window:
                    self.main_window.after_idle(
                        lambda: self.show_group_invitation_dialog(group_name, from_user)
                    )
            
            # Return acknowledgment
            return {'type': 'ack', 'status': 'received'}
            
        elif msg_type == 'group_invitation_response':
            # Handle invitation response
            group_name = message.get('group')
            response_type = message.get('response')
            from_user = message.get('from', sender)
            
            # Log the response
            logger.info(f"Received {response_type} response from {from_user} for group '{group_name}'")
            
            # Handle acceptance
            if response_type == 'accept':
                # Add user to group members
                if group_name in self.group_manager.groups:
                    members = self.group_manager.groups[group_name]['members']
                    if from_user not in members:
                        members.append(from_user)
                        logger.info(f"Added {from_user} to group '{group_name}'")
                        
                        # Update UI if needed
                        if self.main_window and hasattr(self.main_window, 'group_mode'):
                            if self.selected_group == group_name:
                                self.main_window.after_idle(
                                    lambda: self.main_window.group_mode.update_group_members_list(group_name)
                                )
                
                # Remove from pending invitations
                if hasattr(self.group_manager, 'pending_invitations') and group_name in self.group_manager.pending_invitations:
                    if from_user in self.group_manager.pending_invitations[group_name]:
                        self.group_manager.pending_invitations[group_name].remove(from_user)
                
                # Show notification
                self.add_temp_message(f"{from_user} accepted your invitation to group '{group_name}'")
                
            # Handle decline
            elif response_type == 'decline':
                # Remove from pending invitations
                if hasattr(self.group_manager, 'pending_invitations') and group_name in self.group_manager.pending_invitations:
                    if from_user in self.group_manager.pending_invitations[group_name]:
                        self.group_manager.pending_invitations[group_name].remove(from_user)
                
                # Show notification
                self.add_temp_message(f"{from_user} declined your invitation to group '{group_name}'")
            
            return {'type': 'ack', 'status': 'received'}
        
        elif msg_type == 'file_transfer_start':
            # Handle the start of a file transfer
            return self.handle_file_transfer_start(message)
        
        elif msg_type == 'discover_response':
            # Handle peer discovery response
            peer_username = message.get('username')
            peer_port = message.get('port')
            
            # Update or add peer information
            if peer_username and peer_username != self.current_user.username:
                # Extract sender IP from the connection
                sender_ip = "127.0.0.1"  # Default for local testing
                if hasattr(message, '_sender_address') and message._sender_address:
                    sender_ip = message._sender_address[0]
                
                # Update or create user
                if peer_username in self.users:
                    self.users[peer_username].ip = sender_ip
                    self.users[peer_username].port = peer_port
                    self.users[peer_username].is_online = True
                else:
                    self.users[peer_username] = User(peer_username, sender_ip, peer_port)
                
                logger.debug(f"Discovered peer: {peer_username} at {sender_ip}:{peer_port}")
            
            return {'type': 'ack', 'status': 'received'}
        
        elif msg_type == 'status_update':
            # Handle peer status updates
            status = message.get('status')
            if status == 'online':
                # Update peer status
                if sender in self.users:
                    self.users[sender].is_online = True
                    logger.debug(f"Peer {sender} is now online")
            elif status == 'offline':
                # Update peer status
                if sender in self.users:
                    self.users[sender].is_online = False
                    logger.debug(f"Peer {sender} is now offline")
            
            return {'type': 'status_ack', 'status': 'received'}
        
        elif msg_type == 'ping':
            # Simple ping to check if peer is online
            return {'type': 'pong', 'status': 'alive'}
        
        elif msg_type == 'error':
            # Handle error messages from peers
            error_msg = message.get('message', 'Unknown error')
            logger.warning(f"Received error from {sender}: {error_msg}")
            return {'type': 'error_ack', 'status': 'received'}
        
        else:
            # Unknown message type
            logger.warning(f"Received unknown message type: {msg_type} from {sender}")
            return {'type': 'error', 'status': 'unknown_message_type', 'message': f"Unknown message type: {msg_type}"}
    
    # Message handlers
    def handle_file_send_request(self, message):
        """Handle file send request from a peer"""
        request_id = message['request_id']
        sender = message['sender']
        file_name = message['file_name']
        file_size = message['file_size']
        
        # Store the request with sender info
        self.file_manager.pending_file_requests[request_id] = {
            'sender': sender,
            'file_name': file_name,
            'file_size': file_size,
            'type': 'incoming_request'
        }
        
        # Notify UI - access root through main_window
        if self.main_window and hasattr(self.main_window, 'root'):
            try:
                self.main_window.root.after_idle(
                    lambda: self.main_window.show_file_notification(request_id, sender, file_name, file_size)
                )
            except Exception as e:
                logger.error(f"Error updating UI for file notification: {e}")
        else:
            logger.warning(f"Cannot show file notification: main_window or root not available")
        
        return {'status': 'notification_sent'}
    
    def handle_file_transfer_start(self, message):
        """Handle the start of a file transfer"""
        return self.file_manager.handle_file_transfer_start(message)
    
    def receive_file_chunks(self, client_socket):
        """Receive file data in chunks"""
        return self.file_manager.receive_file_chunks(client_socket)
    
    def handle_file_send_response(self, message):
        """Handle response to a file send request"""
        request_id = message['request_id']
        sender = message['sender']
        accepted = message['accepted']
        
        if request_id in self.file_manager.pending_file_requests:
            if accepted:
                # Start file transfer
                threading.Thread(
                    target=self.file_manager.start_file_transfer,
                    args=(request_id, sender),
                    daemon=True
                ).start()
            else:
                # Remove from pending requests
                del self.file_manager.pending_file_requests[request_id]
                self.add_temp_message(f"{sender} rejected the file transfer")
    
    def handle_chat_message(self, message):
        """Handle chat message from a peer"""
        sender = message['sender']
        msg_text = message['message']
        
        # Add to messages
        self.add_temp_message(f"{sender}: {msg_text}")
    
    def handle_group_invite(self, message):
        """Handle group invitation"""
        group_name = message['group_name']
        inviter = message['inviter']
        members = message.get('members', [inviter])
        
        # Store the invitation data
        self._last_group_invitation = message
        
        # Show invitation dialog
        if self.main_window:
            self.main_window.after_idle(
                lambda: self.main_window.show_group_invitation(group_name, inviter)
            )
    
    def handle_group_member_joined(self, message):
        """Handle notification that a new member joined a group"""
        group_name = message['group_name']
        new_member = message['new_member']
        updated_members = message['updated_members']
        
        # Update local group member list
        if group_name in self.group_manager.groups:
            self.group_manager.groups[group_name]['members'] = updated_members
            
            # Add notification
            self.add_temp_message(f"{new_member} joined group {group_name}")
            
            # Update UI if needed
            if self.main_window and self.selected_group == group_name:
                self.main_window.after_idle(
                    lambda: self.main_window.update_group_members_list(group_name)
                )
    
    def handle_directory_share(self, message):
        """Handle directory share notification"""
        group_name = message['group_name']
        directory = message['directory']
        sharer = message['sharer']
        
        # Update group's shared directories
        if group_name in self.group_manager.groups:
            if sharer not in self.group_manager.groups[group_name]['shared_dirs']:
                self.group_manager.groups[group_name]['shared_dirs'][sharer] = []
            
            if directory not in self.group_manager.groups[group_name]['shared_dirs'][sharer]:
                self.group_manager.groups[group_name]['shared_dirs'][sharer].append(directory)
        
            # Add notification
            self.add_temp_message(f"{sharer} shared a directory with group {group_name}")
            
            # Update UI if needed
            if self.main_window and self.selected_group == group_name:
                self.main_window.after_idle(
                    lambda: self.main_window.update_shared_directories(group_name)
                )
    
    # User actions
    def send_chat_message(self, peer, message):
        """Send chat message to a peer"""
        if not peer or not message:
            return False
        
        try:
            peer_obj = self.users[peer]
            chat_message = {
                'type': 'chat_message',
                'sender': self.current_user.username,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
            
            response = self.network.send_message(peer_obj, chat_message)
            
            if response and response.get('status') == 'received':
                # Add to local messages
                self.add_temp_message(f"You: {message}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error sending chat message: {e}")
            return False
    
    def send_file(self, peer, file_path):
        """Send a file to a peer"""
        if not peer or not file_path:
            return False, "Invalid peer or file"
        
        try:
            peer_obj = self.users[peer]
            
            # Create file request
            request = self.file_manager.create_file_request(file_path, peer_obj)
            
            # Send request
            response = self.network.send_message(peer_obj, request)
            
            if response and response.get('status') == 'notification_sent':
                self.add_temp_message(f"File send request sent to {peer}")
                return True, request['request_id']
            
            return False, "Failed to send request"
            
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            return False, str(e)
    
    def create_group(self, group_name, members):
        """Create a new group"""
        if not group_name:
            return False, "Please enter a group name"
        
        if group_name in self.group_manager.groups:
            return False, "Group name already exists"
        
        # Create the group with just the creator initially
        self.group_manager.groups[group_name] = {
            'members': [self.current_user.username],
            'shared_dirs': {}
        }
        
        # Send invitations to the selected members
        if members:
            invites_sent = 0
            for member in members:
                if member != self.current_user.username:  # Don't invite self
                    # Send invitation
                    if self.send_group_invitation(group_name, member):
                        invites_sent += 1
                        
                        # Track pending invitation
                        if group_name not in self.group_manager.pending_invitations:
                            self.group_manager.pending_invitations[group_name] = []
                        
                        self.group_manager.pending_invitations[group_name].append(member)
            
            message = f"Group created successfully. Sent {invites_sent} invitations."
        else:
            message = "Group created successfully with no additional members."
        
        return True, message

    def send_group_invitation(self, group_name, members):
        """Send a group invitation to a member or list of members"""
        if not hasattr(self, 'message_handler'):
            logger.error("Message handler not available")
            return False
        
        # Ensure we're dealing with a list
        if isinstance(members, str):
            members = [members]
        
        success = True
        for member in members:
            if member != self.current_user.username:  # Don't invite self
                # Create invitation message
                invitation = {
                    'type': 'group_invitation',
                    'group': group_name,
                    'from': self.current_user.username,
                    'timestamp': time.time()
                }
                
                # Send the invitation - use network directly instead of message handler
                try:
                    if member in self.users:
                        peer = self.users[member]
                        response = self.network.send_message(peer, invitation)
                        
                        if response and response.get('status') == 'received':
                            logger.info(f"Sent group invitation for {group_name} to {member}")
                            
                            # Add to pending invitations
                            if not hasattr(self.group_manager, 'pending_invitations'):
                                self.group_manager.pending_invitations = {}
                            
                            if group_name not in self.group_manager.pending_invitations:
                                self.group_manager.pending_invitations[group_name] = []
                            
                            if member not in self.group_manager.pending_invitations[group_name]:
                                self.group_manager.pending_invitations[group_name].append(member)
                        else:
                            logger.warning(f"Failed to send invitation to {member}")
                            success = False
                    else:
                        logger.warning(f"Member {member} not found in users list")
                        success = False
                except Exception as e:
                    logger.exception(f"Error sending invitation to {member}: {e}")
                    success = False
        
        return success
        
    def join_group(self, group_name, members, inviter):
            """Join a group"""
            if not self.group_manager.join_group(group_name, members):
                return False
            
            # Notify existing members
            self.notify_group_members_new_joiner(group_name, inviter)
            
            return True
    
    def notify_group_members_new_joiner(self, group_name, inviter):
        """Notify existing group members about new joiner"""
        if group_name not in self.group_manager.groups:
            return
        
        members = self.group_manager.get_group_members(group_name)
        
        for member in members:
            if member != self.current_user.username and member != inviter and member in self.users:
                try:
                    peer = self.users[member]
                    notification = {
                        'type': 'group_member_joined',
                        'group_name': group_name,
                        'new_member': self.current_user.username,
                        'updated_members': members,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    self.network.send_message(peer, notification)
                    
                except Exception as e:
                    logger.error(f"Error notifying {member} about new member: {e}")
    
    def share_directory(self, group_name, directory, members):
        """Share a directory with group members"""
        if not self.group_manager.share_directory(group_name, directory, members):
            return False
        
        # Send notifications
        self.send_directory_share_notifications(group_name, directory, members)
        
        return True
    
    def send_directory_share_notifications(self, group_name, directory, members):
        """Send directory share notifications"""
        for member in members:
            if member in self.users:
                try:
                    peer = self.users[member]
                    notification = {
                        'type': 'directory_share',
                        'group_name': group_name,
                        'directory': directory,
                        'sharer': self.current_user.username,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    self.network.send_message(peer, notification)
                    
                except Exception as e:
                    logger.error(f"Error sending directory share notification to {member}: {e}")
    
    # Utility methods
    def add_temp_message(self, message):
        """Add a temporary message and update UI if needed"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        self.temp_messages.append(full_message)
        
        # Update UI if needed
        if self.main_window and hasattr(self.main_window, 'root') and self.current_mode == "private":
            try:
                self.main_window.root.after_idle(
                    lambda: self.main_window.update_chat_display(full_message)
                )
            except Exception as e:
                logger.error(f"Error updating chat display: {e}")
        
    def on_file_received(self, file_info):
        """Called when a file has been received"""
        self.add_temp_message(
            f"File '{file_info['file_name']}' received from {file_info['sender']} and saved to {file_info['file_path']}"
        )
        
        # Show notification in UI
        if self.main_window:
            self.main_window.after_idle(
                lambda: self.main_window.show_file_received_notification(file_info)
            )
    
    def shutdown(self):
        """Shutdown the application"""
        logger.info("Shutting down application")
        self.network.shutdown()
        
    def send_message_to_peer(self, peer_username, message_data):
        """Send a message to a peer with proper error handling"""
        if peer_username not in self.users:
            logger.error(f"Unknown peer: {peer_username}")
            return False, "Peer not found"
        
        peer = self.users[peer_username]
        
        # Check if peer is marked as online
        if hasattr(peer, 'is_online') and not peer.is_online:
            # Try to check if they're back online
            if not self.network.check_peer_availability(peer):
                return False, "Peer appears to be offline"
            else:
                # Mark them as online again
                peer.is_online = True
        
        # Send the message
        response = self.network.send_message(peer, message_data)
        
        if response and response.get("status") == "error":
            return False, response.get("message", "Unknown error")
        
        return True, response
    def show_firewall_instructions(self):
        """Show instructions for configuring firewall"""
        messagebox.showinfo(
            "Network Connectivity Issues",
            "Connection issues detected. This may be due to firewall settings.\n\n"
            "To allow P2P connections:\n\n"
            "1. Make sure Windows Firewall allows Python/this app\n"
            "2. Allow incoming connections on ports 12345-12370\n"
            "3. Make sure all peers are on the same network\n"
            "4. Try restarting the application on both sides\n\n"
            f"Your IP: {self.network.local_ip}, Port: {self.current_user.port}"
        )
        
    def show_group_invitation_dialog(self, group_name, from_user):
        """Show dialog to accept/reject group invitation"""
    
        
        result = messagebox.askyesno(
            "Group Invitation", 
            f"{from_user} has invited you to join group '{group_name}'.\nDo you want to accept?",
            icon=messagebox.QUESTION
        )
        
        if result:
            self.accept_group_invitation(group_name, from_user)
        else:
            self.decline_group_invitation(group_name, from_user)

    def accept_group_invitation(self, group_name, from_user):
        """Accept a group invitation"""
        logger.info(f"Accepting invitation to group '{group_name}' from {from_user}")
        
        # Create the group locally
        if not hasattr(self.group_manager, 'groups'):
            self.group_manager.groups = {}
            
        if group_name not in self.group_manager.groups:
            self.group_manager.groups[group_name] = {
                'members': [self.current_user.username, from_user],
                'shared_dirs': {}
            }
        else:
            # Add self to the group if not already a member
            if self.current_user.username not in self.group_manager.groups[group_name]['members']:
                self.group_manager.groups[group_name]['members'].append(self.current_user.username)
        
        # Send acceptance response
        response = {
            'type': 'group_invitation_response',
            'group': group_name,
            'response': 'accept',
            'from': self.current_user.username
        }
        
        # Send response
        if from_user in self.users:
            peer = self.users[from_user]
            self.network.send_message(peer, response)
        
        # Remove from received invitations
        for inv in self.group_manager.received_invitations[:]:
            if inv.get('group') == group_name and inv.get('from') == from_user:
                self.group_manager.received_invitations.remove(inv)
                break
        
        # Update UI if needed
        if self.main_window and hasattr(self.main_window, 'group_mode'):
            self.main_window.after_idle(
                lambda: self.main_window.group_mode.update_my_groups_list()
            )
        
        # Show confirmation
        from tkinter import messagebox
        messagebox.showinfo("Group Joined", f"You have joined group '{group_name}'")

    def decline_group_invitation(self, group_name, from_user):
        """Decline a group invitation"""
        logger.info(f"Declining invitation to group '{group_name}' from {from_user}")
        
        # Send decline response
        response = {
            'type': 'group_invitation_response',
            'group': group_name,
            'response': 'decline',
            'from': self.current_user.username
        }
        
        # Send response
        if from_user in self.users:
            peer = self.users[from_user]
            self.network.send_message(peer, response)
        
        # Remove from received invitations
        for inv in self.group_manager.received_invitations[:]:
            if inv.get('group') == group_name and inv.get('from') == from_user:
                self.group_manager.received_invitations.remove(inv)
                break
        
    def handle_group_invitation_response(self, message):
        """Handle response to group invitation"""
        group_name = message.get('group')
        response_type = message.get('response')
        from_user = message.get('from')
        
        # Log the response
        logger.info(f"Received {response_type} response from {from_user} for group '{group_name}'")
        
        # Handle acceptance
        if response_type == 'accept':
            # Add user to group members
            if group_name in self.group_manager.groups:
                members = self.group_manager.groups[group_name]['members']
                if from_user not in members:
                    members.append(from_user)
                    logger.info(f"Added {from_user} to group '{group_name}'")
                    
                    # Update UI if needed
                    if self.main_window and hasattr(self.main_window, 'group_mode'):
                        if self.selected_group == group_name:
                            self.main_window.after_idle(
                                lambda: self.main_window.group_mode.update_group_members_list(group_name)
                            )
            
            # Remove from pending invitations
            if hasattr(self.group_manager, 'pending_invitations') and group_name in self.group_manager.pending_invitations:
                if from_user in self.group_manager.pending_invitations[group_name]:
                    self.group_manager.pending_invitations[group_name].remove(from_user)
            
            # Show notification
            self.add_temp_message(f"{from_user} accepted your invitation to group '{group_name}'")
            
        # Handle decline
        elif response_type == 'decline':
            # Remove from pending invitations
            if hasattr(self.group_manager, 'pending_invitations') and group_name in self.group_manager.pending_invitations:
                if from_user in self.group_manager.pending_invitations[group_name]:
                    self.group_manager.pending_invitations[group_name].remove(from_user)
            
            # Show notification
            self.add_temp_message(f"{from_user} declined your invitation to group '{group_name}'")