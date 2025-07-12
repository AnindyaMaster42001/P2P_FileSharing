#!/usr/bin/env python3
import sys
import os
import logging
import threading
import traceback
from dotenv import load_dotenv
# Add parent directory to path to allow imports

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Frontend.app import AppController
from Frontend.main_window import MainWindow
from Backend.utils import setup_logger

# For debugging
print(f"SUPABASE_URL set: {'Yes' if os.environ.get('SUPABASE_URL') else 'No'}")
print(f"SUPABASE_KEY set: {'Yes' if os.environ.get('SUPABASE_KEY') else 'No'}")

def main():
    # Setup logging
    logger = setup_logger()
    logger.info("Starting P2P File Sharing Application")
    
    try:
        # Create application controller
        app_controller = AppController()
        
        # Create and run main window
        main_window = MainWindow(app_controller)
        
        # Start the application
        main_window.run()
        
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        logger.error(traceback.format_exc())
        
        # Show error in console
        print(f"Error: {e}")
        traceback.print_exc()
        
        # Exit with error code
        sys.exit(1)

if __name__ == "__main__":
    main()