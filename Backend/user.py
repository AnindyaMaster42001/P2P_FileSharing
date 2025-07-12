from datetime import datetime

class User:
    def __init__(self, username, ip, port):
        self.username = username
        self.ip = ip
        self.port = port
        self.is_online = True
        self.last_seen = datetime.now()
        
    def __str__(self):
        return f"User({self.username}, {self.ip}:{self.port})"
        
    def update_last_seen(self):
        self.last_seen = datetime.now()