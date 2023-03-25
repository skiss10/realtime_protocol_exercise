"""
Exception Handling module
"""

import pickle
from utils.message import Message

def send_message(conn, msg_name, msg_data, msg_senderId):
    """
    Utility function to send messages over a connection
    """

    message = Message(msg_name, msg_data, msg_senderId)

    serialized_message = pickle.dumps(message)

    conn.sendall(serialized_message)

    return

