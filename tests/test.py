"""
Testing module

Author: Stephen Kiss (stephenkiss986@gmail.com)
Date: 01/23/2023
"""

# pylint: disable=import-error
# pylint: disable=wrong-import-position

import unittest
import threading
import sys
import socket
import struct
import pickle
import uuid
import time
import redis

sys.path.append('/Users/stephenkiss/Documents/Ably Docs/realtime_protocol_exercise')

import server
from utils.message_sender import send_message
from utils.session_store import RedisStore

# class TestServer(unittest.TestCase):
#     """
#     Class to test server
#     """

#     def setUp(self):
#         """
#         Setup sequence server in a separate thread
#         """

#         # setup defaul server address
#         self.peer_address = ('localhost', 49155)

#         # set up thread for server main
#         self.server_connection = threading.Thread(target=server.main, args=())
#         self.server_connection.start()

#         self.client_id = str(uuid.uuid4())
#         self.connection_id = str(uuid.uuid4())
#         self.REDIS_STORAGE = RedisStore()

#         self.all_uint32_numbers = server.generate_prng_sequence(10)

#     def test_greeting_ack(self):
#         """
#         Test that the server sends a greeting ack in response to a greeting message
#         """

#         # create socket object
#         with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:

#             # estabislih connection
#             conn.connect(self.peer_address)
        
#             # set sequence length
#             sequence_length = 11

#             # spin up thread to send greeting message
#             send_greeting = threading.Thread(target=send_message, args=(conn, "Greeting", sequence_length, "TEST_CLIENT",))
#             send_greeting.start()

#             # monitor for new messages over the socket
#             message = conn.recv(1024)

#             # unserialize messages
#             unserialized_message = pickle.loads(message)

#             # assert we get a greeting_ack back
#             self.assertEqual(unserialized_message.name, "Greeting_ack")

#             # asser the greeting ack contains a uuid string
#             self.assertIsInstance(unserialized_message.data, str)

#     def test_failed_reconnection(self):
#         """
#         Test that the server properly fails a bogus reconnection attempt
#         """

#         # create socket object
#         with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:

#             # estabislih connection
#             conn.connect(self.peer_address)

#             send_greeting = threading.Thread(target=send_message, args=(conn, "reconnect_attempt", ("BAD_CONN_ID", "BAD_UINT32_NUM"), "TEST_CLIENT",))
#             send_greeting.start()

#             # recieve new messages over the socket
#             message = conn.recv(1024)

#             # unserialize messages
#             unserialized_message = pickle.loads(message)

#             conn.close()

#             # assert we get a greeting_ack back
#             self.assertEqual(unserialized_message.name, "Reconnect_rejected")

#             # assert we get a greeting_ack back
#             self.assertEqual(unserialized_message.data, "no_recorded_state")

#     # create a test for adding a connection to redis

#         # redis_client.set('client_session_state:{client_id}:{connection_id}', connection.all_uint32_numbers)
#         # redis_client.expire('client_session_state:{client_id}:{connection_id}', 30)

#     # create a test for updating the TTL for redis

#     # create a test for checking for a specific connection ID from redis upon reconnect

class TestGeneratePRNGSequence(unittest.TestCase):
    """
    Class to test random sequence generator
    """

    def test_sequence_length(self):
        """
        Assert generate_prng_sequence sequence length
        """

        # generate a sequence of length 10
        sequence = server.generate_prng_sequence(10)
        self.assertEqual(len(sequence), 10)
        
    def test_sequence_values(self):
        """
        Assert generate_prng_sequence within acceptable range
        """
        # generate a sequence of length 5
        sequence = server.generate_prng_sequence(5)
        
        # check that each number in the sequence is between 0 and 2^32-1
        for num in sequence:
            num_value = struct.unpack('>I', num)[0]
            self.assertGreaterEqual(num_value, 0)
            self.assertLess(num_value, 2**32)
            
    def test_sequence_bytes(self):
        """
        Assert generate_prng_sequence in bytes
        """
        # generate a sequence of length 3
        sequence = server.generate_prng_sequence(3)
        
        # check that each number in the sequence is a bytes object
        for num in sequence:
            self.assertIsInstance(num, bytes)
        
    def test_sequence_randomness(self):
        """
        Assert generate_prng_sequence randomness
        """
        # generate two sequences of length 5
        sequence1 = server.generate_prng_sequence(5)
        sequence2 = server.generate_prng_sequence(5)

        # check that the sequences are not equal
        self.assertNotEqual(sequence1, sequence2)

class TestRedisStore(unittest.TestCase):

    def setUp(self):
        self.REDIS_STORAGE = RedisStore()
        self.client_id = 'test_client'
        self.connection_id = 'test_connection'
        self.sequence = server.generate_prng_sequence(10)
        self.TTL = 2

    def test_redis_set_store(self):
        """
        
        """
        from server import redis_set_store
        
        # update redis session info
        redis_set_store(self.REDIS_STORAGE, self.client_id, self.connection_id, self.sequence, TTL = self.TTL)

        # retrieve redis session
        session_state = self.REDIS_STORAGE.get(f'client_session_state:{self.client_id}:{self.connection_id}')

        # assert info was uplaoded properly
        self.assertEqual(pickle.loads(session_state), self.sequence)

        # wait for TTL
        time.sleep(2)

        # retireve expired session
        session_state = self.REDIS_STORAGE.get(f'client_session_state:{self.client_id}:{self.connection_id}')

        # ensure its gone
        self.assertIsNone(session_state)

if __name__ == '__main__':
    unittest.main()
