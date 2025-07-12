import os
from supabase import create_client
import logging
from datetime import datetime


logger = logging.getLogger(__name__)

class SupabaseAuth:
    def __init__(self):
        # Get Supabase credentials from environment variables
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            logger.error("Supabase credentials not found in environment variables")
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
            
        self.client = create_client(self.supabase_url, self.supabase_key)
    
    def sign_up(self, email, password):
        """Register a new user"""
        try:
            response = self.client.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if response.user:
                return True, response.user
            else:
                # If there's an error in the response
                error_msg = "Registration failed. Please try again."
                if hasattr(response, 'error') and response.error:
                    error_msg = response.error.message
                return False, error_msg
                
        except Exception as e:
            logger.error(f"Sign up error: {e}")
            return False, str(e)
    
    def sign_in(self, email, password):
        """Sign in an existing user"""
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user:
                return True, response.user
            else:
                error_msg = "Login failed. Please check your credentials."
                if hasattr(response, 'error') and response.error:
                    error_msg = response.error.message
                return False, error_msg
                
        except Exception as e:
            logger.error(f"Sign in error: {e}")
            return False, str(e)
    
    def sign_out(self):
        """Sign out the current user"""
        try:
            self.client.auth.sign_out()
            return True, None
        except Exception as e:
            logger.error(f"Sign out error: {e}")
            return False, str(e)
    
    def get_user(self):
        """Get the current user"""
        try:
            return self.client.auth.get_user()
        except:
            return None
    
    def get_profile(self, user_id):
        """Get user profile from the profiles table"""
        try:
            response = self.client.from_('profiles').select('*').eq('id', user_id).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return None
    
    def update_profile(self, user_id, updates):
        """Update user profile"""
        try:
            # Add updated_at timestamp
            updates['updated_at'] = datetime.now().isoformat()
            
            response = self.client.from_('profiles').update(updates).eq('id', user_id).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return None