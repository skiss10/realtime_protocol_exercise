"""
Test module for client.py
"""

import unittest
from unittest.mock import MagicMock
import pickle
from client import Message, message_handler, format_greeting

class TestClient(unittest.TestCase):
    #Test to ensure stream_payload messages are appending incoming string to list
    def test_message_handler(self):
        # Create a MagicMock object
        mock_socket = MagicMock()

        uint32_numbers = []
        incoming_message = Message("stream_payload", '123456', None)
        message_handler(mock_socket, incoming_message, uint32_numbers)
        self.assertEqual(uint32_numbers, ['123456'])

    #test for format_greeting function
    def test_format_greeting(self):
        sequence_length = 10
        client_id = "1234"
        serialized_message = format_greeting(sequence_length, client_id)
        self.assertTrue(isinstance(serialized_message, bytes))
        deserialized_message = pickle.loads(serialized_message)
        self.assertEqual(deserialized_message.name, "greeting")
        self.assertEqual(deserialized_message.data, 10)
        self.assertEqual(deserialized_message.client_id, "1234")

if __name__ == '__main__':
    unittest.main()
