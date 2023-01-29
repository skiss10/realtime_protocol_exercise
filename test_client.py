"""
Client.py test module
"""
import unittest
import socket
import pickle
from mock import patch, mock_open
from utils.checksum import calculate_checksum
from client import Message, message_handler, format_greeting, connect_to_server

class TestClient(unittest.TestCase):
    @patch('socket.socket')
    def test_connect_to_server(self, mock_socket):
        # Test connecting to server
        mock_socket.return_value.connect.return_value = None
        host_ip = '127.0.0.1'
        port = 1234
        client_socket = connect_to_server(host_ip, port)
        mock_socket.assert_called_with(socket.AF_INET, socket.SOCK_STREAM)
        # client_socket.connect.assert_called_with((host_ip, port))

    def test_format_greeting(self):
        # Test formatting greeting message
        sequence_length = 10
        client_id = 'client1'
        message = format_greeting(sequence_length, client_id)
        deserialized_message = pickle.loads(message)
        self.assertEqual(deserialized_message.name, "greeting")
        self.assertEqual(deserialized_message.data, sequence_length)
        self.assertEqual(deserialized_message.client_id, client_id)

    def test_message_handler(self):
        # Test message handling
        uint32_numbers = []
        client_socket = mock_open()
        client_checksum = calculate_checksum(uint32_numbers)
        incoming_message = Message("checksum", client_checksum, 'client1')
        message_handler(client_socket, incoming_message, uint32_numbers)
        self.assertEqual(client_socket.close.call_count, 1)