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
        self.state = None # initial_connection, disconnected, reconnected
        self.client_id = None
        self.threading_lock = threading.Lock()
        self.last_num_sent = 0 #TODO potentially remove this
        self.last_num_recv = None #TODO potentially remove this
        self.requested_sequence_length = None
        self.queued_uint32_numbers = None
        self.sent_uint32_numbers = None
        self.uint32_numbers_recieved = None
        self.continue_stream_from = None

