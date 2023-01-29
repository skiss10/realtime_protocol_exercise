"""
Test module for server.py
"""

import unittest
from unittest.mock import MagicMock, call
import pickle
import struct
from utils.message import Message
from utils.checksum import calculate_checksum
from server import message_handler

class TestServer(unittest.TestCase):
    """
    Server test class
    """

    def test_message_handler(self):
        """
        Method to test message_handler function in server.py

        Ensure that the correct number of messages are sent 
        to the client socket and that they are serialized correctly.
        """

        # create a mock client socket for testing
        self.client_socket = MagicMock()

        # create a mock incoming message for testing
        incoming_message = MagicMock()

        incoming_message.name = "greeting"
        incoming_message.data = 3
        incoming_message.client_id = "Client-01"

        server_name = "Server-01"

        # call the message_handler function
        message_handler(incoming_message, self.client_socket, server_name)

        # assert that the correct number of messages were sent to the client
        self.assertEqual(self.client_socket.sendall.call_count, 4)

        # assert that the correct messages were sent to the client
        expected_calls = [
            call(pickle.dumps(Message("stream_payload", struct.pack('>I', 1), server_name))),
            call(pickle.dumps(Message("stream_payload", struct.pack('>I', 2), server_name))),
            call(pickle.dumps(Message("stream_payload", struct.pack('>I', 3), server_name))),
            call(pickle.dumps(Message("checksum", calculate_checksum([struct.pack('>I', num) for num in range(1, 4)]), "Server-01")))
        ]
        self.client_socket.sendall.assert_has_calls(expected_calls)

if __name__ == '__main__':
    unittest.main()