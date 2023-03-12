"""
Module to define a connection object
"""

class Connection:
    """
    Define a Connection object
    """
    def __init__(self, peer_socket, peer_address, local_hostname, session_storage):
        """
        Initialize connection attributes
        """
        self.peer_socket = peer_socket
        self.peer_address = peer_address
        self.local_hostname = local_hostname
        self.session_storage = session_storage
        self.connection_id = None
        self.remote_hostname = None
        self.state = None
        self.last_message = None

    def detect_heartbeat(self):
        """
        
        """
        pass