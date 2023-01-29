import socket
import sys
import time
import logging
import pickle
import struct
from _thread import start_new_thread
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

def message_handler(incoming_message, client_socket, server_name):
    """
    Handle incoming messages
    """
    if incoming_message.name == "greeting":
    # make incrementing uint34 list of messages
        sequence_length = incoming_message.data
        logging.info("Server - sequence length requested: %s", sequence_length)
        uint32_numbers = [struct.pack('>I', num) for num in range(1, sequence_length+1)]
        logging.info("Server - list of uint32 numbers: %s", uint32_numbers)

        # Send each uint32
        logging.info("Server - sending uint32 numbers to client %s" , incoming_message.client_id)
        for num in uint32_numbers:
            # create response message
            message = Message("stream_payload", num, server_name)

            #serialize message
            serialized_message = pickle.dumps(message)
            
            # send stream payload message
            logging.info("Server - Sending: " + str(num) + " to " + str(incoming_message.client_id))
            client_socket.sendall(serialized_message)
            time.sleep(1)

        # get the hexadecimal representation of the md5 hash
        checksum = calculate_checksum(uint32_numbers)
        logging.info("Server - calculated checksum: %s" , checksum)

        # create response message
        message = Message("checksum", checksum, "Server-01") # TODO figure out client_id field

        #serialize message
        serialized_message = pickle.dumps(message)

        # send a message to the server
        logging.info("Server - sending checksum payload to client")
        client_socket.sendall(serialized_message)

    # # close the connection
    # logging.info("Server - closing connection")
    # client_socket.close()
    # logging.info("Server - connection closed")

def client_handler(client_socket, client_address, server_name):
    """
    client_thread handles all logic needed on a per
    client basis.

    Input: client socket and client address
    """
    logging.info("Server - Connection on: %s", client_address)

    # receive data from the client
    serialized_message = client_socket.recv(1024) #write test for data format (num bytes and format)

    # unserialize message
    incoming_message = pickle.loads(serialized_message)
    logging.info("Server - message recieved of type: %s", incoming_message.name)

    # handle message
    message_handler(incoming_message, client_socket, server_name)

def start_server(port):
    """
    This function initates the server socket and sets
    it to listen on the local host at a given port

    Input: port number for local host

    Output: socket object
    """
    # create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # bind the socket to a specific address and port
    server_socket.bind(('localhost', port))

    # listen for incoming connections
    server_socket.listen(1)
    logging.info("Listening on localhost:{%s} ...", port)

    return server_socket

def main():
    #define server name
    server_name = "server-01"

    # Configure logging
    logging.basicConfig(
        level=constants.LOG_LEVEL,
        filename=constants.LOG_FILE_PATH,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%m-%d %H:%M:%S'
        )
    logging.info("===== Server - starting %s =====" % server_name)

    # get the port number
    port = int(sys.argv[1])

    # start the server
    server_socket = start_server(port)

    while True:
        # establish a connection
        client_socket, client_address = server_socket.accept()

        # Start a new thread for each client
        start_new_thread(client_handler, (client_socket, client_address, server_name))

if __name__ == '__main__':
    main()
