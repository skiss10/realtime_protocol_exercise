import socket
import sys
import time
import logging
import pickle
import struct
import asyncio

from _thread import start_new_thread
from utils.message import Message
from utils.checksum import calculate_checksum
from constants import HEARTBEAT_INTERVAL, LOG_LEVEL, LOG_FILE_PATH

async def send_heartbeats(client_socket, server_name):
    """
    Send heartbeats over client_socket
    """
    while True:
        try:
            server_timestamp = str(time.time())
            heartbeat = Message("hearbeat", server_timestamp, server_name)

            #serialize message
            serialized_heartbeat = pickle.dumps(heartbeat)

            # send stream payload message
            logging.info("Server - Sending heartbeat to client: %s" % client_socket)
            client_socket.sendall(serialized_heartbeat)
            await asyncio.sleep(HEARTBEAT_INTERVAL)

        except socket.error as err:
            logging.info("Server - connection error: {}".format(err))
            logging.info("Server - stopping hearbeats to %s" % client_socket)
            break

async def send_payload(incoming_message, client_socket, server_name):
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
        await asyncio.sleep(1)

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

async def message_handler(incoming_message, client_socket, server_name):
    """
    Handle incoming messages
    """
    if incoming_message.name == "greeting":
        await send_payload(incoming_message, client_socket, server_name)

async def client_handler(client_socket, client_address, server_name):
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

    # handle incoming messages
    await message_handler(incoming_message, client_socket, server_name)

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

async def run_client_handler(client_socket, client_address, server_name):
    logging.debug("Server - starting client handler for %s" % client_socket)
    logging.debug("Server - Starting to send heartbeats to %s" % client_socket) 
    await asyncio.gather(client_handler(client_socket, client_address, server_name), send_heartbeats(client_socket, server_name))

def add_new_client(client_socket, client_address, server_name):
    asyncio.run(run_client_handler(client_socket, client_address, server_name))

async def main():
    #define server name
    server_name = "server-01"

    # Configure logging
    logging.basicConfig(
        level=LOG_LEVEL,
        filename=LOG_FILE_PATH,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%m-%d %H:%M:%S'
        )
    logging.info("===== Server - starting %s =====" % server_name)

    # get the port number
    port = int(sys.argv[1])

    # start the server
    server_socket = start_server(port)

    try:
        while True:
            # establish a connection
            client_socket, client_address = server_socket.accept()
            logging.info("Server - incoming client socket %s" % client_socket)

            # Start a new thread for each client
            start_new_thread(add_new_client, (client_socket, client_address, server_name))

    except KeyboardInterrupt:
        server_socket.close()
        print("The Server has been stopped and the server socket has been closed.")
        logging.info("Server - the server has been stopped")

if __name__ == '__main__':
    asyncio.run(main())
