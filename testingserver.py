"""
Socket server
"""

import socket
import threading
import time
import uuid
import pickle
import logging

from constants import HEARTBEAT_INTERVAL, LOG_LEVEL, LOG_FILE_PATH
from utils.message_sender import send_message
from utils.connection import Connection

SERVER_NAME = str(uuid.uuid4())

def client_handler(connection):
    """
    Handler for all inbound clients
    """

    # define variable to stop threads associated with client
    connection.connection_thread_stopper = threading.Event()

    # define first hearbeat_ack timestamp as client_handler initiation timestamp
    connection.last_heartbeat_ack = time.time()

    # create lock for shared variables between threads
    lock = threading.Lock()

    # spawn a new thread to handle inbound messages from client
    inbound_messages_thread = threading.Thread(target=inbound_message_handler, args=(connection, lock,))
    inbound_messages_thread.start()

    # spawn a new thread to monitor heartbeats_acks from the client
    heartbeat_ack_thread = threading.Thread(target=check_heartbeat_ack, args=(connection, lock,))
    heartbeat_ack_thread.start()

    # spawn a new thread to send heartbeats to the client
    heartbeat_thread = threading.Thread(target=send_heartbeat, args=(connection,))
    heartbeat_thread.start()

def inbound_message_handler(connection, lock):
    """
    Handler for all messages inbound to the client.
    """

    # Continuous loop contingent on status of connection's threads
    while not connection.connection_thread_stopper.is_set():

        # retrieve inbound data from client
        try:
            serialized_message = connection.conn.recv(1024)

            # unserialize data from socket
            message = pickle.loads(serialized_message)
            print(f"Received message type {message.name} from {connection.addr} with data: {message.data}" )

            # check if the messages is a heartbeat_ack
            if message.name == "Heartbeat_ack":

                # aquire lock to update shared last_heartbeat_ack variable in other threads
                with lock:

                    # update last heartbeat ack timestamp
                    connection.last_heartbeat_ack = time.time()

        except OSError:
            print("Issue recieving data. New messages not being read by inbound_message_handler")
            break

def check_heartbeat_ack(connection, lock):
    """
    Function to ensure heartbeats are being recieved from client
    """

    # Continuous loop that considers status of peer client threads
    while not connection.connection_thread_stopper.is_set():

        # get current timestamp
        current_time = time.time()

        with lock:

            # check for three missed heartbeats
            if current_time - connection.last_heartbeat_ack > HEARTBEAT_INTERVAL * 3:
                print("Heartbeat_acks are not being recieved from client. Disconnecting Client...")
                
                # stop other threads running for the client
                connection.connection_thread_stopper.set()

                # close the connection
                connection.conn.close()

                break

        # sleep thread checking for heartbeat_acks
        time.sleep(1)

def send_heartbeat(connection):
    """
    Function to continously send heartbeats from the server
    to the client
    """

    # Continuous loop that considers status of peer client threads
    while not connection.connection_thread_stopper.is_set():

        # send heartbeats
        try:
            time.sleep(HEARTBEAT_INTERVAL)
            send_message(connection.conn, "Heartbeat" , "", SERVER_NAME)
            print(f"Sent Heartbeat to {connection.addr} at {time.time()}")

        except OSError:
            pass

def main():
    """
    main function for server
    """

    # define server address
    host = '127.0.0.1'
    port = 12331

    # start server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen(5)
        print("Server listening on port", port)

        logging.info("===== Server - starting %s =====", SERVER_NAME)

        while True:

            # listen for new connections
            conn, addr = s.accept()
            print(f"Connected by {addr}")
            logging.info("[%s] Server - Socket - incoming client socket %s", SERVER_NAME, s)

            # instantiate connection object
            connection = Connection(conn)

            # set connection object peer address
            connection.addr = addr

            # handle each client in a separate thread
            client_thread = threading.Thread(target=client_handler, args=(connection,))
            client_thread.start()
          
if __name__ == "__main__":

    # Configure logging
    logging.basicConfig(level=LOG_LEVEL,
                        filename=LOG_FILE_PATH,
                        format='[%(asctime)s] %(levelname)s: %(message)s',
                        datefmt='%m-%d %H:%M:%S')

    main()
