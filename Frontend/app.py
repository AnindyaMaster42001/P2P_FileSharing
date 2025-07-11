import logging
import socket
import threading
import json
from datetime import datetime

from Backend.user import User
from Backend.network import NetworkManager
from Backend.file_manager import FileManager
from Backend.group import GroupManager
from Backend.utils import setup_logger, get_app_version

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
        
        # State
        self.current_user = None
        self.users = {}  # {username: User object}
        self.temp_messages = []  # Temporary chat messages
        
        # UI references (will be set by UI components)
        self.main_window = None
        
        # Initialize mode and selections
        self.current_mode = "login"
        self.selected_peer = None
        self.selected_group = None
        
    def login_user(self, username, port):
        """Log in a user and start the server"""
        if not username:
            return False, "Please enter a username"
            
        try:
            port = int(port)
        except ValueError:
            return False, "Please enter a valid port number"
            
        # Start server
        server_port = self.network.start_server(port)
        if not server_port:
            return False, f"Could not start server on any available port starting from {port}"
            
        # Create user
        self.current_user = User(username, "127.0.0.1", server_port)
        self.users[username] = self.current_user
        
        logger.info(f"User {username} logged in on port {server_port}")
        
        return True, server_port
    
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
        
        # Notify UI
        if self.main_window:
            self.main_window.after_idle(
                lambda: self.main_window.show_file_notification(request_id, sender, file_name, file_size)
            )
        
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
        
        if not members:
            return False, "Please select at least one member"
        
        # Create group
        if not self.group_manager.create_group(group_name, members):
            return False, "Failed to create group"
        
        # Send invitations
        self.send_group_invitations(group_name, members)
        
        return True, "Group created successfully"
    
    def send_group_invitations(self, group_name, members):
        """Send group invitations to members"""
        current_members = self.group_manager.get_group_members(group_name)
        
        for member in members:
            if member in self.users:
                try:
                    peer = self.users[member]
                    invitation = {
                        'type': 'group_invite',
                        'group_name': group_name,
                        'inviter': self.current_user.username,
                        'members': current_members,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    self.network.send_message(peer, invitation)
                    
                except Exception as e:
                    logger.error(f"Error sending invitation to {member}: {e}")
    
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
        if self.main_window and self.current_mode == "private":
            self.main_window.after_idle(
                lambda: self.main_window.update_chat_display(full_message)
            )
    
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