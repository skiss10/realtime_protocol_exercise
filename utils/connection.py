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
        self.state = None # initial_connection, disconnected, reconnected
        self.client_id = None
        self.session_storage = None
        self.threading_lock = None
        self.last_num_sent = 0
        self.last_num_recv = None

    def detect_heartbeat(self):
        """
        test
        """
