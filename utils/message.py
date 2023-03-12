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

    # def serialize(self, message):
    #     """
    #     Serialize a message
    #     """

    #     #serialize checksum message
    #     serialized_message = pickle.dumps(message)
    #     return serialized_message

    # def deserialize(self, serialized_message):
    #     """
    #     Deserialize a message
    #     """

    #     #deserialize checksum message
    #     deserialized_message = pickle.loads(serialized_message)
    #     return deserialized_message
    