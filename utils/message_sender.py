"""
Exception Handling module
"""

import pickle
from utils.message import Message

def send_message(conn, msg_name, msg_data, sender_id):
    """
    Utility function to send messages over a connection
    """

    # create message object with input params
    message = Message(msg_name, msg_data, sender_id)

    # serialize the message object
    serialized_message = pickle.dumps(message)

    # sent the serialized message over the provided connection socket
    conn.sendall(serialized_message)

