import socket
import threading
import json
import logging
from datetime import datetime 
import time

logger = logging.getLogger(__name__)

class NetworkManager:
    def __init__(self, app_controller):
        self.app_controller = app_controller
        self.server_socket = None
        self.is_server_running = False
        self.all_ports = list(range(12345, 12370))
        
        # Get and store local IP
        self.local_ip = self.get_local_ip()
        logger.info(f"Using local network IP: {self.local_ip}")
    
    def get_local_ip(self):
        """Get the local IP address of this machine on the network"""
        try:
            # This creates a socket and connects to an external server
            # It doesn't actually send any data, but it allows us to get the local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # We don't actually connect to Google, just use it to figure out which 
            # network interface would be used
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            logger.warning(f"Error getting primary network IP: {e}")
            # Fall back to hostname resolution if the above fails
            try:
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                if local_ip.startswith("127."):
                    # This is still a loopback address, try to find better ones
                    ips = socket.gethostbyname_ex(hostname)[2]
                    for ip in ips:
                        if not ip.startswith("127."):
                            return ip
                return local_ip
            except Exception as e:
                logger.error(f"Error getting hostname IP: {e}")
                # If all else fails, default to localhost
                return "127.0.0.1"
       
       
    def check_peer_availability(self, peer):
        """Check if a peer is available"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((peer.ip, peer.port))
            sock.close()
            
            if result == 0:
                # Connection successful - peer is online
                return True
            else:
                logger.warning(f"Peer {peer.username} appears to be offline (code: {result})")
                return False
        except Exception as e:
            logger.error(f"Error checking peer availability: {e}")
            return False 
    def discover_used_ports(self):
        """Discover which ports are already in use using threading"""
        used_ports = set()
        
        def check_port(port):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.2)
                result = sock.connect_ex((self.local_ip, port))
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
            thread.join(timeout=0.5)
        
        return used_ports
        
    def start_server(self, requested_port):
        """Start the server on an available port"""
        max_attempts = 10
        current_port = requested_port
        
        # Get used ports concurrently
        try:
            used_ports = self.discover_used_ports()
        except Exception as e:
            logger.error(f"Error discovering used ports: {e}")
            used_ports = set()
        
        for attempt in range(max_attempts):
            # Skip ports that are already in use
            if current_port in used_ports:
                current_port += 1
                continue
                
            try:
                # Log the port we're trying to bind to
                logger.info(f"Attempting to bind to 0.0.0.0:{current_port} (all interfaces)")
                
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                # Bind to all interfaces directly - better for localhost communication
                self.server_socket.bind(('0.0.0.0', current_port))
                self.server_socket.listen(5)
                self.is_server_running = True
                
                # Start server thread
                server_thread = threading.Thread(target=self.server_listener, daemon=True)
                server_thread.start()
                
                logger.info(f"Server started on all interfaces, port {current_port}")
                return current_port
                
            except Exception as e:
                logger.error(f"Server start error on port {current_port}: {e}")
                if self.server_socket:
                    self.server_socket.close()
                current_port += 1
                
        # If we get here, we couldn't start the server on any port
        # Try one last time with a very basic approach
        try:
            logger.warning("Trying one last attempt with fallback binding...")
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind(('0.0.0.0', 12345))
            self.server_socket.listen(5)
            self.is_server_running = True
            
            server_thread = threading.Thread(target=self.server_listener, daemon=True)
            server_thread.start()
            
            logger.info("Server started on fallback port 12345")
            return 12345
        except Exception as e:
            logger.error(f"Final fallback server start failed: {e}")
            return None
    
    def server_listener(self):
        """Listen for incoming connections"""
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
                    logger.error(f"Server error: {e}")
    
    def handle_client(self, client_socket, address):
        """Handle client connection and process messages"""
        try:
            client_socket.settimeout(30)
            data = client_socket.recv(8192)
            logger.info(f"Received discovery request from {message.get('username')} at {message.get('ip')}:{message.get('port')}")
            if not data:
                return
            
            try:
                message = json.loads(data.decode())
                msg_type = message.get('type')
                
                if msg_type == 'file_transfer_start':
                    response = self.app_controller.handle_file_transfer_start(message)
                    client_socket.send(json.dumps(response).encode())
                    
                    if response.get('status') == 'ready':
                        self.app_controller.receive_file_chunks(client_socket)
                else:
                    response = self.app_controller.process_message(message)
                    if response:
                        client_socket.send(json.dumps(response).encode())
                        
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
            except Exception as e:
                logger.error(f"Message processing error: {e}")
                
        except socket.timeout:
            logger.warning("Client socket timeout")
        except Exception as e:
            logger.error(f"Client handling error: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def discover_peers(self, current_user):
        """Discover peers on the network"""
        discovered_peers = []
        
        def scan_target(ip, port):
            # Skip scanning our own IP:port
            if ip == self.local_ip and port == current_user.port:
                return
            logger.info(f"Starting peer discovery from {self.local_ip} (User: {current_user.username}, Port: {current_user.port})")
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(30)  # Shorter timeout for network scanning
                result = sock.connect_ex((ip, port))
                if result == 0:
                    message = {
                        'type': 'discover', 
                        'username': current_user.username,
                        'port': current_user.port,
                        'ip': self.local_ip
                    }
                    sock.send(json.dumps(message).encode())
                    
                    sock.settimeout(2)
                    response = sock.recv(1024)
                    if response:
                        peer_info = json.loads(response.decode())
                        if peer_info.get('username') != current_user.username:
                            discovered_peers.append(peer_info)
                        
                sock.close()
            except Exception as e:
                logger.debug(f"Discovery error for {ip}:{port}: {e}")
        
        # Get the subnet base from local IP dynamically
        ip_parts = self.local_ip.split('.')
        subnet_base = '.'.join(ip_parts[0:3]) + '.'
        
        # Store our own last octet for comparison
        our_last_octet = int(ip_parts[3])
        
        # Create threads list
        threads = []
        
        # 1. Scan localhost on all ports (existing functionality)
        for port in self.all_ports:
            t = threading.Thread(target=scan_target, args=(self.local_ip, port))
            threads.append(t)
            t.start()
        
        # 2. Scan network devices - optimized for your subnet
        # Focus on the most common IP ranges first
        
        # Scan common device IPs first (1-20, where routers and servers often are)
        for last_octet in range(1, 21):
            # Skip our own IP as we already scanned all ports on it
            if last_octet == our_last_octet:
                continue
                
            target_ip = subnet_base + str(last_octet)
            # For these important IPs, scan a few ports
            for port in self.all_ports[:3]:  # First 3 ports in your range
                t = threading.Thread(target=scan_target, args=(target_ip, port))
                threads.append(t)
                t.start()
        
        # Then scan the rest of the subnet with fewer ports per IP
        # This is where most client devices would be
        for last_octet in range(21, 255):
            # Skip our own IP
            if last_octet == our_last_octet:
                continue
                
            target_ip = subnet_base + str(last_octet)
            # For regular IPs, just scan the first port in our range to reduce traffic
            port = self.all_ports[0]  # Just the first port
            t = threading.Thread(target=scan_target, args=(target_ip, port))
            threads.append(t)
            t.start()
        
        # Set a maximum wait time for all threads (45 seconds total for a full subnet scan)
        start_time = time.time()
        for t in threads:
            # Don't wait more than remaining time
            remaining_time = max(45 - (time.time() - start_time), 0.1)
            t.join(timeout=remaining_time)
            
        logger.info(f"Discovered {len(discovered_peers)} peers on the network")
        return discovered_peers
    
    def send_message(self, peer, message_data, timeout=5):
        """Send a message to a peer with proper timeout"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)  # Set a strict timeout
            
            # Determine if peer is on the same machine
            is_local_peer = peer.ip == self.local_ip or peer.ip.startswith('127.') or peer.ip == 'localhost'
            
            # Use the appropriate IP for connection
            connect_ip = '127.0.0.1' if is_local_peer else peer.ip
            
            # Log the connection attempt (only once with the correct IP)
            logger.info(f"Connecting to {peer.username} at {connect_ip}:{peer.port}")
            
            # Try to connect using connect_ip, not peer.ip
            sock.connect((connect_ip, peer.port))
            
            # Send the message
            sock.send(json.dumps(message_data).encode())
            
            # Wait for response with timeout
            sock.settimeout(timeout)
            response = sock.recv(1024)
            sock.close()
            
            if response:
                return json.loads(response.decode())
            return None
            
        except socket.timeout:
            logger.error(f"Connection to {peer.username} timed out")
            raise TimeoutError(f"Connection to {peer.username} timed out")
            
        except ConnectionRefusedError:
            logger.error(f"Connection to {peer.username} refused at {connect_ip}:{peer.port}")
            raise ConnectionRefusedError(f"Peer {peer.username} refused connection")
            
        except Exception as e:
            logger.error(f"Error sending message to {peer.username}: {e}")
            raise
            
    def shutdown(self):
        """Shutdown the server"""
        self.is_server_running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass