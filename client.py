import socket
import sys
import uuid
import random
import pickle
import logging
from utils.message import Message
from utils.checksum import calculate_checksum
import constants
import time

def compare_stream_hash(uint32_numbers, incoming_message): #TODO, make test to ensure both are unserialzied list of uint32
    """
    Compare local and recieved hash of uint32 sequence
    """
    logging.info("Client - uint32 numbers recieved from server are %s", uint32_numbers)
    # compare checksums
    server_checksum = incoming_message.data
    client_checksum = calculate_checksum(uint32_numbers)
    logging.info("Client - checksum recieved from server: %s", server_checksum)
    logging.info("Client - calculated checksum from client: %s", client_checksum)

    if server_checksum == client_checksum:
        logging.info("Client - PASS - Checksums from client and Server are the same")

    else:
        logging.info("Client - FAIL - Checksums from client and Server are not the same")

def message_handler(client_socket, incoming_message, uint32_numbers):
    """
    Handle inbound data from server
    """
    if incoming_message.name == "stream_payload":
        uint32_numbers.append(incoming_message.data)

    elif incoming_message.name == "checksum":
        compare_stream_hash(uint32_numbers, incoming_message)

        # close the connection
        logging.info("Client - closing connection")
        client_socket.close()

    else:
        logging.info("Client - message_handler recieved unknown message name type. Discarding message...")

def format_greeting(sequence_length, client_id):
    """
    Function to format greeting message from client to server
    """

    # format introduction message
    message = Message("greeting", sequence_length, client_id)
    logging.info("Client - requesting sequence of length: %s", sequence_length)

    # serialize message
    serialized_message = pickle.dumps(message)

    #return serialized message
    return serialized_message

def connect_to_server(host_ip, port):
    """
    Initiate server connection
    """
    # create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # flag to indicate if a connection has been established
    connected = False

    # keep trying to connect to the server every 15 seconds until a connection is established
    while not connected:
        try:
            # connect to the server
            logging.info("Client - connecting to server...")
            client_socket.connect((host_ip, port))

            # set the connected flag to True
            connected = True

        except socket.error as err:
            logging.info("Client - connection error: %s", err)
            logging.info("Client - retrying connection in 15 seconds...")
            time.sleep(15)

    # return connected socket
    return client_socket

def main():
    """
    Main for client.py
    """
    # generate a random uuid client identifier
    client_id = str(uuid.uuid4())

    # Configure logging
    logging.basicConfig(
        level=constants.LOG_LEVEL,
        filename=constants.LOG_FILE_PATH,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%m-%d %H:%M:%S'
        )
    logging.info("===== Client - starting %s =====", client_id)

    # get the port number and number of messages from command line
    port = int(sys.argv[1]) #TODO add assert here somewhere
    sequence_length = int(sys.argv[2]) if len(sys.argv) > 2 else random.randint(1, 0xffff)

    # local sequence store
    uint32_numbers = []

    # define server ip
    host_ip = 'localhost'

    # connect to server
    client_socket = connect_to_server(host_ip, port)

    # create greeting message for server
    serialized_greeting = format_greeting(sequence_length, client_id)

    # send a message to the server
    logging.info("Client - sending greeting message")
    client_socket.sendall(serialized_greeting)

    while True:
        try:
            # perform socket I/O operations
            serialized_message = client_socket.recv(1024)

            # unserialize message
            incoming_message = pickle.loads(serialized_message)
            logging.info("Client - message type recieved: %s", incoming_message.name)

            # send to incoming message handler
            message_handler(client_socket, incoming_message, uint32_numbers)

        except OSError:
            # The socket is closed if a socket.error is raised
            print("The client socket has been closed.")
            logging.info("Client - the client socket for %s has been closed.", client_id)
            break

if __name__ == '__main__':
    main()
