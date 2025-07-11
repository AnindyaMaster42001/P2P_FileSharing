import os
import logging
from datetime import datetime

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