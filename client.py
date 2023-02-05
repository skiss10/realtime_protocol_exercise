import socket
import sys
import uuid
import random
import pickle
import logging
import time
import constants
import asyncio

from utils.message import Message
from utils.checksum import calculate_checksum

# generate a random uuid client identifier
CLIENT_ID = str(uuid.uuid4())

def compare_stream_hash(uint32_numbers, incoming_message): #TODO, make test to ensure both are unserialzied list of uint32
    """
    Compare local and recieved hash of uint32 sequence
    """
    logging.info("[%s] Client - Message - uint32 numbers recieved from server are %s", CLIENT_ID, uint32_numbers)
    # compare checksums
    server_checksum = incoming_message.data
    client_checksum = calculate_checksum(uint32_numbers)
    logging.info("[%s] Client - Message - checksum recieved from server: %s", CLIENT_ID, server_checksum)
    logging.info("[%s] Client - Message - calculated checksum from client: %s", CLIENT_ID, client_checksum)

    if server_checksum == client_checksum:
        logging.info("[%s] Client - PASS - Checksums from client and Server are the same", CLIENT_ID)

    else:
        logging.info("[%s] Client - FAIL - Checksums from client and Server are not the same", CLIENT_ID)

def message_handler(client_socket, incoming_message, uint32_numbers):
    """
    Handle inbound data from server
    """
    if incoming_message.name == "stream_payload":
        uint32_numbers.append(incoming_message.data)

    elif incoming_message.name == "checksum":
        compare_stream_hash(uint32_numbers, incoming_message)

        # close the connection
        logging.info("[%s] Client - Socket - closing connection", CLIENT_ID)
        client_socket.close()

    elif incoming_message.name == "heartbeat":
        logging.info("[%s] Client - Heartbeat - recieved heartbeat from server %s", CLIENT_ID, incoming_message.sender_id)

    else:
        logging.info("[%s] Client - message_handler recieved unknown message name type. Discarding message...", CLIENT_ID)

def server_handler(client_socket, uint32_numbers):
        """
        Handle Server IO
        """
        while True:
            try:
                # perform socket I/O operations
                serialized_message = client_socket.recv(1024)

                # unserialize message
                incoming_message = pickle.loads(serialized_message)
                logging.info("[%s] Client - Message - message type recieved: %s", CLIENT_ID, incoming_message.name)

                # send to incoming message handler
                message_handler(client_socket, incoming_message, uint32_numbers)

            except OSError:
                # The socket is closed if a socket.error is raised
                print("The client socket has been closed.")
                logging.info("[%s] Client - the socket has been closed.", CLIENT_ID)
                break

def format_greeting(sequence_length, client_id):
    """
    Function to format greeting message from client to server
    """

    # format introduction message
    message = Message("greeting", sequence_length, client_id)
    logging.info("[%s] Client - Message - requesting sequence of length: %s", CLIENT_ID, sequence_length)

    # serialize message
    serialized_message = pickle.dumps(message)

    #return serialized message
    return serialized_message

def connect_to_socket(host_ip, port):
    """
    Connect to server and return the socket
    """
    # create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # flag to indicate if a connection has been established
    connected = False

    # keep trying to connect to the server every 15 seconds until a connection is established
    while not connected:
        try:
            # connect to the server
            logging.info("[%s] Client - Socket - attempting to connect to server...", CLIENT_ID)
            client_socket.connect((host_ip, port))

            # set the connected flag to True
            connected = True

        except socket.error as err:
            logging.info("[%s] Client - Socket - connection error: %s", CLIENT_ID, err)
            logging.info("[%s] Client - Socket - retrying connection in 15 seconds...", CLIENT_ID)
            time.sleep(15)

    return client_socket

def main():
    """
    Main for client.py
    """
    # define client id
    client_id = CLIENT_ID

    # Configure logging
    logging.basicConfig(
        level=constants.LOG_LEVEL,
        filename=constants.LOG_FILE_PATH,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%m-%d %H:%M:%S'
        )
    logging.info("===== Client - starting %s =====", client_id)

    # get the port number and number of messages from command line
    #TODO add assert here somewhere
    port = int(sys.argv[1])
    sequence_length = int(sys.argv[2]) if len(sys.argv) > 2 else random.randint(1, 0xffff)

    # local sequence store
    uint32_numbers = []

    # define server ip
    host_ip = 'localhost'

    # connect to server
    client_socket = connect_to_socket(host_ip, port)

    # create greeting message for server
    serialized_greeting = format_greeting(sequence_length, client_id)

    # send a message to the server
    logging.info("[%s] Client - Message - sending greeting message", CLIENT_ID)
    client_socket.sendall(serialized_greeting)

    server_handler(client_socket, uint32_numbers)

if __name__ == '__main__':
    main()
    # asyncio.run(main())
