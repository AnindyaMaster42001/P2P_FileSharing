import os
import hashlib
import shutil
from datetime import datetime
import logging
import socket
import json

logger = logging.getLogger(__name__)

class FileManager:
    def __init__(self, app_controller):
        self.app_controller = app_controller
        self.pending_file_requests = {}  # {request_id: file_info}
        self.current_file_transfer = None
        
    def create_file_request(self, file_path, peer):
        """Create a file transfer request"""
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        # Generate unique request ID
        request_id = hashlib.md5(
            f"{self.app_controller.current_user.username}_{file_name}_{datetime.now().isoformat()}".encode()
        ).hexdigest()
        
        # Store file info for later transfer
        self.pending_file_requests[request_id] = {
            'file_path': file_path,
            'file_name': file_name,
            'file_size': file_size,
            'peer': peer.username
        }
        
        return {
            'type': 'file_send_request',
            'request_id': request_id,
            'sender': self.app_controller.current_user.username,
            'file_name': file_name,
            'file_size': file_size,
            'timestamp': datetime.now().isoformat()
        }
    
    def handle_file_transfer_start(self, message):
        """Handle the start of a file transfer"""
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
            logger.error(f"Error preparing for file transfer: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def start_file_transfer(self, request_id, receiver):
        """Start sending a file to the receiver"""
        if request_id not in self.pending_file_requests:
            logger.error(f"File request {request_id} not found")
            return False
            
        file_info = self.pending_file_requests[request_id]
        
        try:
            peer = self.app_controller.users[file_info['peer']]
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect((peer.ip, peer.port))
            
            # Send file transfer header
            header = {
                'type': 'file_transfer_start',
                'request_id': request_id,
                'sender': self.app_controller.current_user.username,
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
                    # File transfer successful
                    del self.pending_file_requests[request_id]
                    return True
            
            return False
                
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            return False
    
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
            
            # Notify the application controller
            self.app_controller.on_file_received(file_info)
            
            return True
            
        except Exception as e:
            error_response = {'status': 'error', 'message': str(e)}
            try:
                client_socket.send(json.dumps(error_response).encode())
            except:
                pass
            logger.error(f"Error receiving file: {e}")
            return False
        finally:
            # Clean up
            self.current_file_transfer = None
            
    @staticmethod
    def format_file_size(size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f} {size_names[i]}"