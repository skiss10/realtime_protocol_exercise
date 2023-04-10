"""
Module to define a connection object
"""

import time
import threading
import uuid

class Connection:
    """
    Define a Connection object
    """
    def __init__(self, conn, addr):
        """
        Initialize connection attributes
        """
        self.conn = conn
        self.id = str(uuid.uuid4())
        self.addr = addr
        self.connection_thread_stopper = threading.Event()
        self.last_heartbeat_ack = time.time()
        self.last_heartbeat_rcvd = time.time()
        self.state = None # initial_connection, disconnected, reconnected, closed
        self.client_id = None
        self.threading_lock = threading.Lock()
        self.sequence_length = None
        self.all_uint32_numbers = []
        self.queued_uint32_numbers = []
        self.sent_uint32_numbers = []
        self.uint32_numbers_recieved = []
        self.checksum = None
        self.replacement_connection_id = None
        self.is_complete = False

