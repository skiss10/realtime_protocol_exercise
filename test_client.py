# import unittest
# import socket
# import mock
# import uuid
# import random
# import pickle
# import logging
# from utils.checksum import calculate_checksum
# import constants
# from client import Message, compare_stream_hash, message_handler, format_greeting, connect_to_server

# class TestClient(unittest.TestCase):
#     #Test to ensure inputs to message handler are standardized.
#     def test_message_handler(self):
#         uint32_numbers = []
#         client_socket = mock.Mock()
#         incoming_message = Message("stream_payload", 123456, None)
#         message_handler(client_socket, incoming_message, uint32_numbers)
#         self.assertEqual(uint32_numbers, [123456])

#     #test for format_greeting function
#     def test_format_greeting(self):
#         sequence_length = 10
#         client_id = "1234"
#         serialized_message = format_greeting(sequence_length, client_id)
#         self.assertTrue(isinstance(serialized_message, bytes))
#         deserialized_message = pickle.loads(serialized_message)
#         self.assertEqual(deserialized_message.name, "greeting")
#         self.assertEqual(deserialized_message.data, 10)
#         self.assertEqual(deserialized_message.client_id, "1234")

# if __name__ == '__main__':
#     unittest.main()



