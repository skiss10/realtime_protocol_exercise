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

class AbstractSessionStore:
    """
    Abstract data store to define interface
    """
    def get(self, key):
        raise NotImplementedError

    def set(self, key, value):
        raise NotImplementedError

    def delete(self, key):
        raise NotImplementedError

class InMemoryStore(AbstractSessionStore):
    """
    Class for in memory data store
    """
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)
    
    def set(self, key, value):
        self.store[key] = value
        logging.debug("[%s] Server - Storage - Setting InMemory data store %s:%s", SERVER_NAME, key, value)
    
    def delete(self, key):
        if key in self.store:
            del self.store[key]
            logging.debug("[%s] Server - Storage - Deleting InMemory data store for %s", SERVER_NAME, key)

async def send_heartbeats(socket_to_client):
    """    Continuously send heartbeats to the client until the socket is torn down
    """

    while True:
        try:
            # timestamp and sign heartbeat
            server_timestamp = str(time.time())
            heartbeat = Message("heartbeat", server_timestamp, SERVER_NAME)

            #serialize message
            serialized_heartbeat = pickle.dumps(heartbeat)

            # send heartbeat payload message
            logging.info("[%s] Server - Heartbeat - Sending heartbeat to client: %s", SERVER_NAME, socket_to_client.getpeername())
            socket_to_client.sendall(serialized_heartbeat)
            await asyncio.sleep(HEARTBEAT_INTERVAL)

        except socket.error as err:

            # stop sending heartbeats if socket throws error
            logging.info("[%s] Server - Socket - connection error: %s", SERVER_NAME, err)
            logging.info("[%s] Server - Socket - stopping hearbeats to %s", SERVER_NAME, socket_to_client)
            break

async def send_sequence(incoming_message, socket_to_client, session_storage):
    """
    Send a sequence of messages every second with incrementing uint32 numbers as the payload.
    """
    
    #TODO: add logic to handle disconnections from client mid sequence send. 

    # store incoming client_id
    session_storage.set("client_id", incoming_message.sender_id)
    session_storage.set(incoming_message.sender_id, socket_to_client.getpeername())
    logging.info("[%s] Server - Storage - stored client_id: %s", SERVER_NAME, incoming_message.sender_id)
    logging.info("[%s] Server - Storage - stored client_id to socket info %s : %s", SERVER_NAME, incoming_message.sender_id, socket_to_client.getpeername())

    # store requested sequence length
    sequence_length = incoming_message.data
    logging.info("[%s] Server - Messages - sequence length requested: %s", SERVER_NAME, sequence_length)
    session_storage.set("sequence_length", sequence_length)
    logging.info("[%s] Server - Storage - stored requested sequence_length: %s", SERVER_NAME, sequence_length)

    # Create an incrementing list of uint32 numbers
    uint32_numbers = [struct.pack('>I', num) for num in range(1, sequence_length+1)]
    logging.info("[%s] Server - System - Server created list of incrementing uint32 numbers: %s", SERVER_NAME, uint32_numbers)

    # store numbers
    session_storage.set("uint32 numbers", uint32_numbers)
    logging.info("[%s] Server - Storage - stored uint32 numbers: %s", SERVER_NAME, uint32_numbers)

    # Send each uint32
    logging.info("[%s] Server - Messages - sending uint32 numbers to client %s" , SERVER_NAME, incoming_message.sender_id)
    numbers_to_send = uint32_numbers
    numbers_sent = []
    session_storage.set("queued", numbers_to_send)
    for num in uint32_numbers:

        # create a single sequence message
        message = Message("stream_payload", num, SERVER_NAME)

        #serialize the message
        serialized_message = pickle.dumps(message)

        # send sequence message
        logging.info("[%s] Server - Sending: %s to %s", SERVER_NAME, num, incoming_message.sender_id)
        socket_to_client.sendall(serialized_message)

        # update store
        numbers_sent.append(num)
        session_storage.set("sent", numbers_sent)
        numbers_to_send = numbers_to_send[1:]
        session_storage.set("queued", numbers_to_send)
        logging.info("[%s] Server - Storage - has stored: %s", SERVER_NAME, session_storage.store)

        # wait for 1 second before sending the next number
        await asyncio.sleep(1)

    # get the md5 hash for the list of uint32 numbers
    checksum = calculate_checksum(uint32_numbers)
    logging.info("[%s] Server - Messages - calculated checksum is %s for client %s over %s" , SERVER_NAME, checksum, incoming_message.sender_id, socket_to_client.getpeername())

    # create checksum message
    message = Message("checksum", checksum, SERVER_NAME)

    #serialize checksum message
    serialized_message = pickle.dumps(message)

    # send checksum message to the server
    logging.info("[%s] Server - Messages - sending checksum payload to client %s", SERVER_NAME, incoming_message.sender_id)
    socket_to_client.sendall(serialized_message)

async def message_handler(incoming_message, socket_to_client, session_storage):
    """
    Handle incoming messages
    """

    if incoming_message.name == "greeting":
        await send_sequence(incoming_message, socket_to_client, session_storage)

    elif incoming_message.name == "reconnection":
        pass #TODO add functionality to handle client reconnection attempts

    elif incoming_message.name == "disconnection":
        pass #TODO: Implement logic to handle disconnections from client gracefully

    elif incoming_message.name == "heartbeat_ack":
        logging.info("[%s] Server - Heartbeat - Recieved hearbeat ack from client: %s", SERVER_NAME, incoming_message.sender_id)

    else:
        logging.info("[%s] Server - System - message_handler recieved unknown message name type. Discarding message...", SERVER_NAME)

async def client_handler(socket_to_client, session_storage):
    """
    Handle all logic needed on a per
    client basis.

    Input: client socket and client address
    """

    logging.info("[%s] Server - Socket - Connection on: %s", SERVER_NAME, socket_to_client.getpeername())
    while True:
        try:
            # receive data from the client
            serialized_message = socket_to_client.recv(1024)

            # unserialize message
            incoming_message = pickle.loads(serialized_message)
            logging.info("[%s] Server - Messages - message recieved of type: %s", SERVER_NAME, incoming_message.name)

            # handle incoming messages in a separate task
            await message_handler(incoming_message, socket_to_client, session_storage)

        except OSError:
            # The socket is closed if a socket.error is raised
            print("The socket has been closed.")
            logging.info("[%s] Server - Socket - the socket has been closed.", SERVER_NAME)
            break

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
    logging.info("[%s] Server - Socket - Listening on localhost:{%s} ...", SERVER_NAME, port)

    return server_socket

async def run_client_handler(socket_to_client):
    """
    Establish tastks to run for each client in parallel
    """

    logging.debug("[%s] Server - Function - starting client handler for %s", SERVER_NAME, socket_to_client)
    logging.debug("[%s] Server - Heartbeat - Starting to send heartbeats to %s", SERVER_NAME, socket_to_client)

    # start a client session store
    session_storage = InMemoryStore()
    logging.info("[%s] Server - Storage - instantiating new session store for socket connection to peer %s", SERVER_NAME, socket_to_client.getpeername())

    # Run parallel tasks for new client conccurently
    await asyncio.gather(
        client_handler(socket_to_client, session_storage),
        send_heartbeats(socket_to_client)
        )

def add_new_client(socket_to_client):
    """
    Handle Client Asynchronously
    """
    asyncio.run(run_client_handler(socket_to_client))

def main():
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

    # list of threads for each client
    threads = []

    # continuosly listen for connection requests
    try:
        while True:
          
            # accept inbound connection attempts from clients
            socket_to_client, _ = server_socket.accept()
            logging.info("[%s] Server - Socket - incoming client socket %s", SERVER_NAME, socket_to_client)

            # Start a new thread for each client
            thread_id = start_new_thread(add_new_client, (socket_to_client,))
            threads.append(thread_id)
            logging.info("[%s] Server - System - thread ids: %s", SERVER_NAME, str(threads))

    except KeyboardInterrupt:
        server_socket.close()
        print("The Server has been stopped and the server socket(s) has been closed.")
        logging.info("[%s] Server - Function - the server has been stopped", SERVER_NAME)
        logging.info("[%s] Server - System - thread ids: %s", SERVER_NAME, str(threads))

if __name__ == '__main__':
    main()
