"""
Module to define message format
"""

class Message:
    """
    Define a message object to be sent over the socket
    """
    def __init__(self, name, data, client_id):
        self.name = name
        self.data = data
        self.client_id = client_id