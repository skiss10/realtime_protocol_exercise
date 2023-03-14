"""
Module to define a connection object
"""

# TODO Implement these properties for the connection: https://ably.com/docs/api/realtime-sdk/connection?lang=nodejs

# TODO: Implement methods to run upon initialization of Connection object  

class Connection:
    """
    Define a Connection object
    """
    def __init__(self, peer_socket, session_storage):
        """
        Initialize connection attributes
        """
        self.peer_socket = peer_socket
        self.session_storage = session_storage
        self.peer_address = None
        self.local_hostname = None
        self.connection_id = None
        self.remote_hostname = None
        self.state = None
        self.last_message = None

    def detect_heartbeat(self):
        """
        test
        """
