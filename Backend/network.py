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
        self.discovery_socket = None
        self.discovery_listener_running = False
        self.all_ports = list(range(12345, 12370))
        
        # Get and store local IP
        self.local_ip = self.get_local_ip()
        logger.info(f"Using local network IP: {self.local_ip}")
        
        # Initialize known peers
        self.known_peers = {}
        self.discovered_peers_cache = []
        self.discovery_lock = threading.Lock()
        
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
        
    def test_bidirectional_connectivity(self, peer, current_user):
        """Test if both devices can connect to each other"""
        # Test outgoing connection
        can_connect_out = self.check_peer_availability(peer)
        
        # Request peer to test connection back to us
        if can_connect_out:
            try:
                test_message = {
                    'type': 'connectivity_test',
                    'test_ip': self.local_ip,
                    'test_port': current_user.port
                }
                response = self.send_message(peer, test_message, timeout=5)
                can_connect_in = response and response.get('status') == 'connected'
                
                logger.info(f"Connectivity test with {peer.username}: "
                        f"Outgoing={'OK' if can_connect_out else 'FAIL'}, "
                        f"Incoming={'OK' if can_connect_in else 'FAIL'}")
                
                return can_connect_out, can_connect_in
            except Exception as e:
                logger.error(f"Connectivity test failed: {e}")
                return can_connect_out, False
        
        return False, False
        
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
    
    def start_discovery_listener(self, current_user):
        """Start a persistent discovery listener on a dedicated port"""
        if self.discovery_listener_running:
            logger.info("Discovery listener already running")
            return
            
        discovery_port = current_user.port + 100  # Use a different port for discovery
        
        def discovery_listener_thread():
            max_retries = 5
            retry_count = 0
            
            while retry_count < max_retries and not self.discovery_listener_running:
                try:
                    self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self.discovery_socket.bind(('0.0.0.0', discovery_port))
                    self.discovery_socket.listen(5)
                    self.discovery_listener_running = True
                    
                    logger.info(f"Discovery listener started on port {discovery_port}")
                    
                    while self.discovery_listener_running:
                        try:
                            self.discovery_socket.settimeout(1.0)
                            client, addr = self.discovery_socket.accept()
                            
                            # Handle discovery request in a separate thread
                            threading.Thread(
                                target=self.handle_discovery_request,
                                args=(client, addr, current_user),
                                daemon=True
                            ).start()
                            
                        except socket.timeout:
                            continue
                        except Exception as e:
                            if self.discovery_listener_running:
                                logger.error(f"Discovery listener error: {e}")
                                
                except OSError as e:
                    if e.errno == 98:  # Address already in use
                        discovery_port += 1
                        retry_count += 1
                        logger.warning(f"Port in use, trying port {discovery_port}")
                    else:
                        logger.error(f"Failed to start discovery listener: {e}")
                        break
                except Exception as e:
                    logger.error(f"Unexpected error in discovery listener: {e}")
                    break
                    
            logger.info("Discovery listener stopped")
            
        threading.Thread(target=discovery_listener_thread, daemon=True).start()
        time.sleep(0.5)  # Give the listener time to start
        
        # Store the discovery port for future use
        self.discovery_port = discovery_port
        
    def handle_discovery_request(self, client, addr, current_user):
        """Handle incoming discovery request"""
        try:
            client.settimeout(2.0)
            data = client.recv(1024)
            
            if data:
                try:
                    msg = json.loads(data.decode())
                    if msg.get('type') == 'discover':
                        # Send our details back
                        response = {
                            'type': 'discovery_response',
                            'username': current_user.username,
                            'port': current_user.port,
                            'ip': self.local_ip
                        }
                        client.send(json.dumps(response).encode())
                        
                        # Store the peer with their ACTUAL IP
                        with self.discovery_lock:
                            # FIXED: Always use the actual connection IP for remote peers
                            actual_peer_ip = addr[0]  # This is the real IP they connected from
                            
                            # Only use localhost if they ACTUALLY connected from localhost
                            # AND they're claiming to be on localhost
                            if actual_peer_ip == '127.0.0.1' and msg.get('ip') == '127.0.0.1':
                                # They're truly local
                                peer_ip = '127.0.0.1'
                            else:
                                # They're remote - use their actual IP
                                peer_ip = actual_peer_ip
                                
                            peer_info = {
                                'username': msg.get('username'),
                                'ip': peer_ip,  # Use the corrected IP
                                'port': msg.get('port'),
                                'discovered_at': time.time(),
                                'discovery_method': 'passive_response',
                                'claimed_ip': msg.get('ip'),  # Store for debugging
                                'actual_connection_ip': addr[0]  # Store the real connection IP
                            }
                            
                            # Only add if not already there
                            if not any(p.get('username') == peer_info['username'] 
                                    for p in self.discovered_peers_cache):
                                self.discovered_peers_cache.append(peer_info)
                                
                            logger.info(f"Discovered {msg.get('username')} from {addr[0]}:{addr[1]}")
                            logger.info(f"  - Actual IP: {peer_ip}")
                            logger.info(f"  - Claimed IP: {msg.get('ip')}")
                            logger.info(f"  - Using IP: {peer_ip}")
                            
                except json.JSONDecodeError:
                    logger.warning(f"Invalid discovery request from {addr}")
                    
        except Exception as e:
            logger.error(f"Error handling discovery request: {e}")
        finally:
            try:
                client.close()
            except:
                pass

    def fix_localhost_ips(self, discovered_peers, current_user):
        """Fix any peers that have localhost IPs but are actually remote"""
        fixed_peers = []
        
        for peer in discovered_peers:
            peer_copy = peer.copy()
            
            # Check if this peer has a localhost IP
            if peer_copy.get('ip', '').startswith('127.'):
                username = peer_copy.get('username')
                port = peer_copy.get('port')
                
                logger.info(f"Peer {username} has localhost IP, attempting to find real IP...")
                
                # Try to find their real IP by scanning the network
                real_ip = self.find_peer_real_ip_by_username(username, port)
                
                if real_ip and real_ip != '127.0.0.1':
                    logger.info(f"Found {username}'s real IP: {real_ip}")
                    peer_copy['ip'] = real_ip
                    peer_copy['localhost_fixed'] = True
                else:
                    # If we can't find them on the network, check if they're truly local
                    if self.is_peer_on_same_machine(username, port):
                        logger.info(f"Peer {username} is on the same machine (localhost is correct)")
                    else:
                        logger.warning(f"Could not find real IP for {username}, keeping localhost")
            
            fixed_peers.append(peer_copy)
        
        return fixed_peers

    def find_peer_real_ip_by_username(self, username, port):
        """Scan the network to find a peer's real IP by their username"""
        ip_parts = self.local_ip.split('.')
        subnet_base = '.'.join(ip_parts[0:3]) + '.'
        
        logger.info(f"Scanning subnet {subnet_base}0/24 for {username} on port {port}")
        
        # Parallel scanning with threading
        found_ip = [None]  # Use list to make it mutable in threads
        scan_lock = threading.Lock()
        
        def scan_ip(ip):
            if found_ip[0]:  # Already found, skip
                return
                
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.0)
                
                if sock.connect_ex((ip, port)) == 0:
                    # Port is open, verify it's the right peer
                    message = {
                        'type': 'discover',
                        'username': 'scanner',
                        'port': 0,
                        'ip': self.local_ip
                    }
                    sock.send(json.dumps(message).encode())
                    
                    sock.settimeout(2)
                    response = sock.recv(1024)
                    if response:
                        try:
                            peer_info = json.loads(response.decode())
                            if peer_info.get('username') == username:
                                with scan_lock:
                                    if not found_ip[0]:  # First to find it
                                        found_ip[0] = ip
                                        logger.info(f"Found {username} at {ip}:{port}")
                        except:
                            pass
                sock.close()
            except:
                pass
        
        # Scan all IPs in subnet except our own
        threads = []
        for last_octet in range(1, 255):
            ip = subnet_base + str(last_octet)
            if ip != self.local_ip:  # Skip our own IP
                thread = threading.Thread(target=scan_ip, args=(ip,))
                threads.append(thread)
                thread.start()
        
        # Wait for threads with timeout
        for thread in threads:
            thread.join(timeout=0.1)
            if found_ip[0]:  # Stop waiting if we found it
                break
        
        return found_ip[0]

    def is_peer_on_same_machine(self, username, port):
        """Check if a peer is actually on the same machine"""
        try:
            # Try connecting to localhost
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            
            if sock.connect_ex(('127.0.0.1', port)) == 0:
                # Send discovery message
                message = {
                    'type': 'discover',
                    'username': 'local_check',
                    'port': 0,
                    'ip': '127.0.0.1'
                }
                sock.send(json.dumps(message).encode())
                
                sock.settimeout(2)
                response = sock.recv(1024)
                if response:
                    try:
                        peer_info = json.loads(response.decode())
                        if peer_info.get('username') == username:
                            sock.close()
                            return True
                    except:
                        pass
            sock.close()
        except:
            pass
        
        return False

    def update_known_peers(self, discovered_peers):
        """Update the list of known peers for future discovery"""
        for peer in discovered_peers:
            if 'username' in peer and 'ip' in peer and 'port' in peer:
                key = peer['username']
                
                # Don't overwrite a good IP with localhost
                if key in self.known_peers:
                    existing_ip = self.known_peers[key]['ip']
                    new_ip = peer['ip']
                    
                    # Keep the non-localhost IP if we have one
                    if existing_ip.startswith('127.') and not new_ip.startswith('127.'):
                        # New IP is better, use it
                        logger.info(f"Updating {key} from localhost to {new_ip}")
                    elif not existing_ip.startswith('127.') and new_ip.startswith('127.'):
                        # Existing IP is better, keep it
                        logger.info(f"Keeping {key}'s existing IP {existing_ip} instead of localhost")
                        continue
                
                self.known_peers[key] = {
                    'ip': peer['ip'],
                    'port': peer['port'],
                    'discovery_port': peer.get('discovery_port', peer['port'] + 100),
                    'last_seen': time.time()
                }

    def fix_peer_ip_manually(self, username, correct_ip):
        """Manually fix a peer's IP address"""
        # Fix in known_peers
        if username in self.known_peers:
            old_ip = self.known_peers[username]['ip']
            self.known_peers[username]['ip'] = correct_ip
            logger.info(f"Fixed {username}'s IP from {old_ip} to {correct_ip}")
        
        # Fix in discovered_peers_cache
        with self.discovery_lock:
            for peer in self.discovered_peers_cache:
                if peer.get('username') == username:
                    old_ip = peer.get('ip')
                    peer['ip'] = correct_ip
                    logger.info(f"Fixed {username}'s cached IP from {old_ip} to {correct_ip}")
        
        # Fix in the app_controller's users list
        if hasattr(self.app_controller, 'users') and username in self.app_controller.users:
            user = self.app_controller.users[username]
            if hasattr(user, 'ip'):
                old_ip = user.ip
                user.ip = correct_ip
                logger.info(f"Fixed {username}'s user object IP from {old_ip} to {correct_ip}")
    
    def discover_peers(self, current_user):
        """Discover peers on the network with improved bidirectional discovery"""
        discovered_peers = []
        scan_results = {}
        
        # Clear the cache before starting new discovery
        with self.discovery_lock:
            self.discovered_peers_cache = []
        
        # Ensure discovery listener is running
        self.start_discovery_listener(current_user)
        
        def scan_target(ip, port, discovery_port=None):
            # Skip scanning ourselves
            if ip == self.local_ip and port == current_user.port:
                return
                
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                
                scan_key = f"{ip}:{port}"
                
                # Try main port first
                result = sock.connect_ex((ip, port))
                if result == 0:
                    # Send discovery message
                    message = {
                        'type': 'discover',
                        'username': current_user.username,
                        'port': current_user.port,
                        'ip': self.local_ip,
                        'discovery_port': getattr(self, 'discovery_port', current_user.port + 100)
                    }
                    sock.send(json.dumps(message).encode())
                    
                    # Wait for response
                    sock.settimeout(3)
                    try:
                        response = sock.recv(1024)
                        if response:
                            try:
                                peer_info = json.loads(response.decode())
                                if peer_info.get('username') != current_user.username:
                                    peer_info['discovery_method'] = 'active_scan'
                                    peer_info['discovered_at'] = time.time()
                                    
                                    # CRITICAL FIX: Always use the IP we connected to,
                                    # not what the peer claims
                                    # Only use localhost if we explicitly connected to localhost
                                    if ip not in ['127.0.0.1', 'localhost', '::1']:
                                        peer_info['ip'] = ip  # Use the actual IP we connected to
                                    else:
                                        # We connected to localhost, so keep it
                                        peer_info['ip'] = ip
                                    
                                    logger.info(f"Discovered peer {peer_info.get('username')} "
                                            f"at {ip}:{port} (peer reported IP: {peer_info.get('ip', 'unknown')})")
                                    
                                    with self.discovery_lock:
                                        discovered_peers.append(peer_info)
                                        
                                    scan_results[scan_key] = f"Found peer: {peer_info.get('username')}"
                                    
                            except json.JSONDecodeError:
                                scan_results[scan_key] = "Invalid response"
                    except socket.timeout:
                        scan_results[scan_key] = "Response timeout"
                        
                sock.close()
                
                # Also try discovery port if different from main port
                if discovery_port and discovery_port != port:
                    try:
                        sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock2.settimeout(1.0)
                        if sock2.connect_ex((ip, discovery_port)) == 0:
                            # Send discovery message
                            sock2.send(json.dumps(message).encode())
                            sock2.settimeout(2)
                            response = sock2.recv(1024)
                            if response:
                                peer_info = json.loads(response.decode())
                                if (peer_info.get('username') != current_user.username and
                                    not any(p.get('username') == peer_info.get('username') 
                                        for p in discovered_peers)):
                                    peer_info['discovery_method'] = 'discovery_port_scan'
                                    peer_info['discovered_at'] = time.time()
                                    
                                    # Use actual IP from connection
                                    if ip not in ['127.0.0.1', 'localhost', '::1']:
                                        peer_info['ip'] = ip
                                    else:
                                        peer_info['ip'] = ip
                                        
                                    with self.discovery_lock:
                                        discovered_peers.append(peer_info)
                                    logger.info(f"Found peer via discovery port: {peer_info.get('username')} at {ip}")
                        sock2.close()
                    except:
                        pass
                        
            except Exception as e:
                scan_results[scan_key] = f"Error: {str(e)}"
                logger.debug(f"Discovery error for {ip}:{port}: {e}")
        
        # Get subnet info
        ip_parts = self.local_ip.split('.')
        subnet_base = '.'.join(ip_parts[0:3]) + '.'
        
        threads = []
        
        # Prioritized scanning
        scan_targets = []
        
        # 1. Known peers
        for peer in self.get_known_peers():
            scan_targets.append((peer['ip'], peer['port'], peer.get('discovery_port')))
            
        # 2. Common ports on our IP (for same-machine peers)
        for port in self.all_ports[:5]:  # First 5 ports
            if port != current_user.port:
                scan_targets.append((self.local_ip, port, port + 100))
                scan_targets.append(('127.0.0.1', port, port + 100))  # Also check localhost
                
        # 3. Local subnet scan
        our_last_octet = int(ip_parts[3])
        
        # Scan nearby IPs first (±10 from our IP)
        for offset in range(-10, 11):
            last_octet = our_last_octet + offset
            if 1 <= last_octet <= 254 and last_octet != our_last_octet:
                target_ip = subnet_base + str(last_octet)
                for port in self.all_ports[:3]:  # First 3 ports
                    scan_targets.append((target_ip, port, port + 100))
                    
        # 4. Scan common device IPs (routers, servers often at .1, .2, etc)
        for last_octet in [1, 2, 3, 100, 200]:
            if last_octet != our_last_octet:
                target_ip = subnet_base + str(last_octet)
                scan_targets.append((target_ip, self.all_ports[0], self.all_ports[0] + 100))
                
        # 5. Broader subnet scan for remaining IPs
        for last_octet in range(1, 255):
            if last_octet == our_last_octet or abs(last_octet - our_last_octet) <= 10:
                continue  # Skip our IP and nearby IPs (already scanned)
            target_ip = subnet_base + str(last_octet)
            # Just scan the primary port for these
            scan_targets.append((target_ip, self.all_ports[0], None))
                    
        # Start scanning
        for target in scan_targets:
            t = threading.Thread(target=scan_target, args=target)
            threads.append(t)
            t.start()
            
        # Wait for threads with timeout
        max_wait = 30
        start_time = time.time()
        
        for t in threads:
            remaining = max(0.1, max_wait - (time.time() - start_time))
            t.join(timeout=remaining)
            if time.time() - start_time > max_wait:
                logger.info("Discovery scan timeout reached")
                break
                
        # Also wait a bit for passive discoveries
        time.sleep(2)
        
        # Combine active and passive discoveries
        with self.discovery_lock:
            for peer in self.discovered_peers_cache:
                # Check if we already have this peer from active scanning
                existing = next((p for p in discovered_peers if p.get('username') == peer.get('username')), None)
                
                if existing:
                    # Prefer non-localhost IPs
                    if existing.get('ip', '').startswith('127.') and not peer.get('ip', '').startswith('127.'):
                        # Update with the better IP
                        existing['ip'] = peer['ip']
                        logger.info(f"Updated {peer.get('username')} IP from localhost to {peer['ip']}")
                else:
                    # Add new peer from passive discovery
                    discovered_peers.append(peer)
        
        # FIX LOCALHOST IPs BEFORE UPDATING KNOWN PEERS
        discovered_peers = self.fix_localhost_ips(discovered_peers, current_user)
        
        # Update known peers
        self.update_known_peers(discovered_peers)
        
        # Log discovery results
        logger.info(f"Discovery completed: {len(discovered_peers)} peers found")
        for peer in discovered_peers:
            logger.info(f"  - {peer.get('username')} at {peer.get('ip')}:{peer.get('port')} "
                    f"(method: {peer.get('discovery_method', 'unknown')})")
        
        # Debug: Log any peers with localhost IPs
        localhost_peers = [p for p in discovered_peers if p.get('ip', '').startswith('127.')]
        if localhost_peers:
            logger.warning(f"Found {len(localhost_peers)} peers with localhost IPs:")
            for peer in localhost_peers:
                logger.warning(f"  - {peer.get('username')} at {peer.get('ip')}")
        
        return discovered_peers
    
    # def update_known_peers(self, discovered_peers):
    #     """Update the list of known peers for future discovery"""
    #     for peer in discovered_peers:
    #         if 'username' in peer and 'ip' in peer and 'port' in peer:
    #             key = peer['username']
    #             self.known_peers[key] = {
    #                 'ip': peer['ip'],
    #                 'port': peer['port'],
    #                 'discovery_port': peer.get('discovery_port', peer['port'] + 100),
    #                 'last_seen': time.time()
    #             }
    
    def get_known_peers(self):
        """Get previously discovered peers for prioritized scanning"""
        result = []
        for username, data in self.known_peers.items():
            result.append({
                'username': username,
                'ip': data['ip'],
                'port': data['port'],
                'discovery_port': data.get('discovery_port', data['port'] + 100),
                'last_seen': data['last_seen']
            })
        
        result.sort(key=lambda x: x['last_seen'], reverse=True)
        return result[:10]  # Return only the 10 most recently seen peers
    
    def send_message(self, peer, message_data, timeout=5):
        """Send a message to a peer with proper timeout"""
        try:
            # Debug what peer object we're getting
            logger.debug(f"send_message called for peer: {vars(peer)}")
            
            # Check if peer has localhost IP but isn't actually local
            if peer.ip.startswith('127.') and peer.username != self.app_controller.current_user.username:
                logger.warning(f"Peer {peer.username} has localhost IP, attempting to find real IP...")
                
                # Try to find real IP
                real_ip = self.find_peer_real_ip_by_username(peer.username, peer.port)
                if real_ip and not real_ip.startswith('127.'):
                    logger.info(f"Found {peer.username}'s real IP: {real_ip}")
                    # Fix it everywhere
                    self.fix_peer_ip_manually(peer.username, real_ip)
                    # Update the peer object we're using
                    peer.ip = real_ip
                else:
                    logger.error(f"Could not find real IP for {peer.username}")
                    # Try known_peers as last resort
                    if peer.username in self.known_peers:
                        known_ip = self.known_peers[peer.username].get('ip')
                        if known_ip and not known_ip.startswith('127.'):
                            logger.info(f"Using known IP for {peer.username}: {known_ip}")
                            peer.ip = known_ip
            
            connect_ip = peer.ip
            logger.info(f"Connecting to {peer.username} at {connect_ip}:{peer.port}")
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            # Try to connect
            sock.connect((connect_ip, peer.port))
            
            # Send the message
            sock.send(json.dumps(message_data).encode())
            
            # Wait for response
            response = sock.recv(8192)
            sock.close()
            
            if response:
                return json.loads(response.decode())
            return None
            
        except socket.timeout:
            logger.error(f"Connection to {peer.username} timed out at {connect_ip}:{peer.port}")
            raise TimeoutError(f"Connection to {peer.username} timed out")
            
        except ConnectionRefusedError:
            logger.error(f"Connection to {peer.username} refused at {connect_ip}:{peer.port}")
            # Call debug method to see what's stored
            self.debug_peer_info(peer.username)
            raise ConnectionRefusedError(f"Peer {peer.username} refused connection")
            
        except Exception as e:
            logger.error(f"Error sending message to {peer.username}: {type(e).__name__}: {e}")
            raise
            
    def debug_peer_info(self, username):
        """Debug method to see all stored info about a peer"""
        logger.info(f"\n=== DEBUG INFO FOR {username} ===")
        
        # Check known_peers
        if username in self.known_peers:
            logger.info(f"Known peers entry: {self.known_peers[username]}")
        else:
            logger.info(f"Not found in known_peers")
        
        # Check discovered_peers_cache
        with self.discovery_lock:
            for peer in self.discovered_peers_cache:
                if peer.get('username') == username:
                    logger.info(f"Discovery cache entry: {peer}")
        
        # Check app_controller users
        if hasattr(self.app_controller, 'users') and username in self.app_controller.users:
            user = self.app_controller.users[username]
            logger.info(f"App controller user: {vars(user)}")
        
        logger.info("=== END DEBUG INFO ===\n")
    def shutdown(self):
        """Shutdown the server and discovery listener"""
        self.is_server_running = False
        self.discovery_listener_running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        if hasattr(self, 'discovery_socket') and self.discovery_socket:
            try:
                self.discovery_socket.close()
            except:
                pass