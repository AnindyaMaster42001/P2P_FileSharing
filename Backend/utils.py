import os
import logging
from datetime import datetime
import socket

def setup_logger():
    """Set up application logger"""
    logger = logging.getLogger('p2p_file_sharing')
    logger.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create file handler
    file_handler = logging.FileHandler(
        os.path.join(logs_dir, f"p2p_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Add file handler to logger
    logger.addHandler(file_handler)
    
    return logger

def get_app_version():
    """Get application version"""
    return "1.0.0"

def get_download_dir():
    """Get default download directory"""
    return os.path.join(os.path.expanduser("~"), "Downloads", "P2P_Files")

def get_group_download_dir():
    """Get default download directory for group files"""
    return os.path.join(os.path.expanduser("~"), "Downloads", "P2P_Group_Files")


import socket

def get_local_ip():
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
            # If all else fails, default to localhost
            return "127.0.0.1"