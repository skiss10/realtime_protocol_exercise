import unittest
import threading
import sys
import socket

sys.path.append('/Users/stephenkiss/Documents/Ably Docs/realtime_protocol_exercise')

import server
import client
from utils.message_sender import send_message


class TestHandlingGreetingAck(unittest.TestCase):

    def setUp(self):
        # create two separate threads to establish a connection between a server and client

    def test_server_connection(self):

        #fake message
        
        # pass client connection into 

        self.thread = client.handle_greeting_ack(client_connection, message)


if __name__ == '__main__':
    unittest.main()