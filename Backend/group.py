import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class GroupManager:
    def __init__(self, app_controller):
        self.app_controller = app_controller
        self.groups = {}  # {group_name: {'members': [usernames], 'shared_dirs': {username: [dir_paths]}}}
        
    def create_group(self, group_name, members):
        """Create a new group with the specified members"""
        if group_name in self.groups:
            return False
            
        self.groups[group_name] = {
            'members': [self.app_controller.current_user.username] + members,
            'shared_dirs': {}
        }
        
        return True
        
    def join_group(self, group_name, members):
        """Join an existing group"""
        if group_name not in self.groups:
            self.groups[group_name] = {'members': members, 'shared_dirs': {}}
            
        if self.app_controller.current_user.username not in self.groups[group_name]['members']:
            self.groups[group_name]['members'].append(self.app_controller.current_user.username)
            
        return True
        
    def add_member(self, group_name, member):
        """Add a member to a group"""
        if group_name not in self.groups:
            return False
            
        if member not in self.groups[group_name]['members']:
            self.groups[group_name]['members'].append(member)
            
        return True
        
    def share_directory(self, group_name, directory, members):
        """Share a directory with group members"""
        if group_name not in self.groups:
            return False
            
        if not os.path.exists(directory):
            return False
            
        # Add to group's shared directories
        username = self.app_controller.current_user.username
        if username not in self.groups[group_name]['shared_dirs']:
            self.groups[group_name]['shared_dirs'][username] = []
                    # Check if directory already shared
        if directory not in self.groups[group_name]['shared_dirs'][username]:
            self.groups[group_name]['shared_dirs'][username].append(directory)
        
        return True
        
    def get_shared_directories(self, group_name):
        """Get all directories shared with the current user in a group"""
        if group_name not in self.groups:
            return {}
            
        shared_dirs = {}
        for sharer, directories in self.groups[group_name]['shared_dirs'].items():
            if sharer != self.app_controller.current_user.username:
                shared_dirs[sharer] = directories
                
        return shared_dirs
        
    def get_group_members(self, group_name):
        """Get all members of a group"""
        if group_name not in self.groups:
            return []
            
        return self.groups[group_name]['members']
        
    def list_user_groups(self):
        """List all groups the current user is a member of"""
        user_groups = []
        for group_name, group_data in self.groups.items():
            if self.app_controller.current_user.username in group_data['members']:
                user_groups.append(group_name)
                
        return user_groups