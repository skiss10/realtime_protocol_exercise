import socket
import sys
import time
import logging
import pickle
import struct
import asyncio
import uuid

from _thread import start_new_thread
from utils.message import Message
from utils.checksum import calculate_checksum
from constants import HEARTBEAT_INTERVAL, LOG_LEVEL, LOG_FILE_PATH

SERVER_NAME = str(uuid.uuid4())

async def send_heartbeats(client_socket, server_name):
    """
    Continuously send heartbeats to the client until the socket is torn down
    """

    while True:
        try:
            
            # timestamp and sign heartbeat
            server_timestamp = str(time.time())
            heartbeat = Message("heartbeat", server_timestamp, server_name)

            #serialize message
            serialized_heartbeat = pickle.dumps(heartbeat)

            # send stream payload message
            logging.info("[%s] Server - Sending heartbeat to client: %s", SERVER_NAME, client_socket)
            client_socket.sendall(serialized_heartbeat)
            await asyncio.sleep(HEARTBEAT_INTERVAL)

        except socket.error as err:

            # stop sending heartbeats if socket throws error
            logging.info("[%s] Server - connection error: %s", SERVER_NAME, err)
            logging.info("[%s] Server - stopping hearbeats to %s", SERVER_NAME, client_socket)
            break

async def send_sequence(incoming_message, client_socket, server_name):
    """
    Send a sequence of messages every second with incrementing uint32 numbers as the payload.
    """

    # Create an incrementing list of uint32 numbers
    sequence_length = incoming_message.data
    logging.info("[%s] Server - sequence length requested: %s", SERVER_NAME, sequence_length)
    uint32_numbers = [struct.pack('>I', num) for num in range(1, sequence_length+1)]
    logging.info("[%s] Server - list of uint32 numbers: %s", SERVER_NAME, uint32_numbers)

    # Send each uint32
    logging.info("[%s] Server - sending uint32 numbers to client %s" , SERVER_NAME, incoming_message.sender_id)
    for num in uint32_numbers:

        # create a single sequence message
        message = Message("stream_payload", num, server_name)

        #serialize the message
        serialized_message = pickle.dumps(message)

        # send sequence message
        logging.info("[%s] Server - Sending: %s to %s", SERVER_NAME, num, incoming_message.sender_id)
        client_socket.sendall(serialized_message)

        # wait for 1 second before sending the next number
        await asyncio.sleep(1)

    # get the md5 hash for the list of uint32 numbers
    checksum = calculate_checksum(uint32_numbers)
    logging.info("[%s] Server - calculated checksum: %s" , SERVER_NAME, checksum)

    # create checksum message
    message = Message("checksum", checksum, SERVER_NAME) # TODO figure out client_id field

    #serialize checksum message
    serialized_message = pickle.dumps(message)

    # send checksum message to the server
    logging.info("[%s] Server - sending checksum payload to client", SERVER_NAME)
    client_socket.sendall(serialized_message)

async def message_handler(incoming_message, client_socket, server_name):
    """
    Handle incoming messages
    """

    if incoming_message.name == "greeting":
        await send_sequence(incoming_message, client_socket, server_name)

    if incoming_message.name == "reconnection":
        pass #TODO add functionality to handle client reconnection attempts

async def client_handler(client_socket, client_address, server_name):
    """
    Handle all logic needed on a per
    client basis.

    Input: client socket and client address
    """

    logging.info("[%s] Server - Connection on: %s", SERVER_NAME, client_address)

    # receive data from the client
    serialized_message = client_socket.recv(1024) #write test for data format (num bytes and format)

    # unserialize message
    incoming_message = pickle.loads(serialized_message)
    logging.info("[%s] Server - message recieved of type: %s", SERVER_NAME, incoming_message.name)

    # handle incoming messages
    await message_handler(incoming_message, client_socket, server_name)

def start_server(port):
    """
    Initiate the server socket and set
    it to listen on the localhost at a given port

    Input: port number for local host

    Output: socket object
    """
    # create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # bind the socket to a specific address and port
    server_socket.bind(('localhost', port))

    # listen for incoming connections
    server_socket.listen(1)
    logging.info("[%s] Server - Listening on localhost:{%s} ...", SERVER_NAME, port)

    return server_socket

async def run_client_handler(client_socket, client_address, server_name):
    """
    Establish tastks to run for each client in parallel
    """

    logging.debug("[%s] Server - starting client handler for %s", SERVER_NAME, client_socket)
    logging.debug("[%s] Server - Starting to send heartbeats to %s", SERVER_NAME, client_socket)

    # Run parallel tasks for new client
    await asyncio.gather(
        client_handler(client_socket, client_address, server_name),
        send_heartbeats(client_socket, server_name)
        )

def add_new_client(client_socket, client_address, server_name):
    """
    Handle Client Asynchronously
    """
    asyncio.run(run_client_handler(client_socket, client_address, server_name))

async def main():
    """
    Main
    """

    #define server name
    server_name = SERVER_NAME

    # Configure logging
    logging.basicConfig(
        level=LOG_LEVEL,
        filename=LOG_FILE_PATH,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%m-%d %H:%M:%S'
        )
    logging.info("===== Server - starting %s =====", SERVER_NAME)

    # get the port number from commandline
    port = int(sys.argv[1])

    # start the server
    server_socket = start_server(port)

    # continuosly listen for connection requests
    try:
        while True:
          
            # accept inbound connection attempts from clients
            client_socket, client_address = server_socket.accept()
            logging.info("[%s] Server - incoming client socket %s", SERVER_NAME, client_socket)

            # Start a new thread for each client
            start_new_thread(add_new_client, (client_socket, client_address, server_name))

    except KeyboardInterrupt:
        server_socket.close()
        print("The Server has been stopped and the server socket has been closed.")
        logging.info("Server - the server has been stopped")

if __name__ == '__main__':
    asyncio.run(main())
