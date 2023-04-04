"""
Module to define message object
"""

class Message:
    """
    Define a message object to be sent over the socket
    """
    def __init__(self, name, data, sender_id):
        self.name = name
        self.data = data
        self.sender_id = sender_id