"""
Module to define a connection object
"""

# TODO Implement these properties for the connection: https://ably.com/docs/api/realtime-sdk/connection?lang=nodejs

# TODO: Implement methods to run upon initialization of Connection object  

class Connection:
    """
    Define a Connection object
    """
    def __init__(self, conn):
        """
        Initialize connection attributes
        """
        self.conn = conn
        self.id = None
        self.addr = None
        self.connection_thread_stopper = None
        self.last_heartbeat_ack = None
        self.state = None
        self.client_id = None

    def detect_heartbeat(self):
        """
        test
        """
