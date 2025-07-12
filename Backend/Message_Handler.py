import logging
import time
import json

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self, app_controller):
        self.app_controller = app_controller
        self.logger = logging.getLogger(__name__)
        
    def send_message(self, recipient, message):
        """
        Send a message to a specific recipient
        
        Args:
            recipient (str): Username of the recipient
            message (dict): Message data to send
        
        Returns:
            bool: Success status
        """
        try:
            # Check if recipient exists
            if recipient in self.app_controller.users:
                # Add sender information if not already included
                if 'sender' not in message:
                    message['sender'] = self.app_controller.current_user.username
                
                # Log outgoing message
                self.logger.info(f"Sending message to {recipient}: {message.get('type', 'unknown')}")
                
                # Send the message using the network component
                success, response = self.app_controller.send_message_to_peer(recipient, message)
                return success
            else:
                self.logger.warning(f"Recipient {recipient} not found")
                return False
            
        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")
            return False
    
    def process_message(self, message, sender):
        """
        Process received messages based on their type
        
        Args:
            message (dict): The message data
            sender (str): Username of the sender
        """
        message_type = message.get('type', '')
        
        # Handle different message types
        if message_type == 'chat_message':
            # Already handled in app_controller.handle_chat_message
            pass
            
        elif message_type == 'group_invitation':
            # Handle group invitation
            self.handle_group_invitation(message, sender)
            
        elif message_type == 'group_invitation_response':
            # Handle invitation response
            self.handle_group_invitation_response(message, sender)
    
    def handle_group_invitation(self, message, sender):
        """Handle received group invitation"""
        group_name = message.get('group')
        
        # Store the invitation in group manager
        if not hasattr(self.app_controller.group_manager, 'received_invitations'):
            self.app_controller.group_manager.received_invitations = []
            
        # Check if invitation already exists
        for inv in self.app_controller.group_manager.received_invitations:
            if inv.get('group') == group_name and inv.get('from') == sender:
                # Already have this invitation
                return
                
        # Add the invitation
        self.app_controller.group_manager.received_invitations.append(message)
        
        # Show notification in UI
        self.app_controller.add_temp_message(f"Group invitation received from {sender} for group '{group_name}'")
        
        # Show UI notification if main_window exists
        if hasattr(self.app_controller, 'main_window') and self.app_controller.main_window:
            self.app_controller.main_window.root.after_idle(
                lambda: self.app_controller.main_window.show_group_invitation_notification(message)
            )
    
    def handle_group_invitation_response(self, message, sender):
        """Handle response to a group invitation"""
        group_name = message.get('group')
        response = message.get('response')
        
        # Update pending invitations
        if hasattr(self.app_controller.group_manager, 'pending_invitations'):
            if group_name in self.app_controller.group_manager.pending_invitations:
                if sender in self.app_controller.group_manager.pending_invitations[group_name]:
                    # Remove from pending
                    self.app_controller.group_manager.pending_invitations[group_name].remove(sender)
        
        # Process the response
        if response == 'accept':
            # Add member to the group
            if group_name in self.app_controller.group_manager.groups:
                members = self.app_controller.group_manager.groups[group_name]['members']
                if sender not in members:
                    members.append(sender)
                    
                # Show notification
                self.app_controller.add_temp_message(f"{sender} accepted your invitation to group '{group_name}'")
                
                # Update UI if showing the group
                if (hasattr(self.app_controller, 'main_window') and 
                    self.app_controller.main_window and 
                    self.app_controller.selected_group == group_name):
                    self.app_controller.main_window.root.after_idle(
                        lambda: self.app_controller.main_window.update_group_members_list(group_name)
                    )
        
        elif response == 'decline':
            # Show notification
            self.app_controller.add_temp_message(f"{sender} declined your invitation to group '{group_name}'")