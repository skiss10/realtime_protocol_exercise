import socket
import sys
import uuid
import random
import pickle
import logging
from utils.checksum import calculate_checksum
import constants

class Message:
    """
    Define a message object to be sent over the socket
    """
    def __init__(self, name, data, client_id):
        self.name = name
        self.data = data
        self.client_id = client_id

def message_handler(client_socket, incoming_message, uint32_numbers):
    """
    Handle inbound data from server
    """
    if incoming_message.name == "stream_payload":
        uint32_numbers.append(incoming_message.data)

    if incoming_message.name == "checksum":
        logging.info("Client - uint32 numbers recieved from server are %s" % uint32_numbers)
        # compare checksums
        server_checksum = incoming_message.data
        client_checksum = calculate_checksum(uint32_numbers)
        logging.info("Client - checksum recieved from server: %s" % server_checksum)
        logging.info("Client - calculated checksum from client: %s" % client_checksum)

        if server_checksum == client_checksum:
            logging.info("Client - PASS - Checksums from client and Server are the same")

        else:
            logging.info("Client - FAIL - Checksums from client and Server are not the same")
        
        # close the connection
        logging.info("Client - closing connection")
        client_socket.close()

def connect_to_server(host_ip, port, client_id, sequence_length):
    """
    Initiate server connection
    """
    # create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # connect to the server
    logging.info("Client - connecting to server...")
    client_socket.connect((host_ip, port))

    # format introduction message
    message = Message("greeting", sequence_length, client_id)
    logging.info("Client - requested sequence of length: %s", sequence_length)

    # serialize message
    serialized_message = pickle.dumps(message)

    # send a message to the server
    logging.info("Client - sending greeting message")
    client_socket.sendall(serialized_message)

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
    logging.info("===== Client - starting %s =====" % client_id)

    # get the port number and number of messages from command line
    port = int(sys.argv[1])
    sequence_length = int(sys.argv[2]) if len(sys.argv) > 2 else random.randint(1, 0xffff)

    # sequence store
    uint32_numbers = []

    # define server ip
    host_ip = 'localhost'

    # connect to server
    client_socket = connect_to_server(host_ip, port, client_id, sequence_length)

    while True:
        # receive data from the client
        # TODO #write test for data recieved from server format
        serialized_message = client_socket.recv(1024)

        # unserialize message
        incoming_message = pickle.loads(serialized_message)
        logging.info("Client - message type recieved: %s", incoming_message.name)

        # send to incoming message handler
        message_handler(client_socket, incoming_message, uint32_numbers)

if __name__ == '__main__':
    main()
