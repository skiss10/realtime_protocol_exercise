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

def end_connection(connection):
    """
    Function to stop all threads and close all sockets for a given connection
    """
    # stop threads related to connection
    try:
        if not connection.connection_thread_stopper.is_set():
            connection.connection_thread_stopper.set()
            print("threads for connection are flagged to stop")

    except OSError:
        print("Error stopping the connection's theads")

    # close the connection's socket
    try:
        if connection.state != "closed":
            connection.state = "closed"
            connection.conn.close()
            print("socket for connection closed")

    except OSError:
        print("Error closing the connections socket")

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

                try:
                    # aquire lock to update shared last_heartbeat_ack variable in other threads
                    with lock:

                        # update last heartbeat ack timestamp
                        connection.last_heartbeat_ack = time.time()

                except OSError:
                    print("OSError hit attemptng to aquire the threading lock to update the connection's last_heartbeat_ack. stopping inbound_message_handler thread for connection, %s", connection.id)
                    break

        # handle socket read errors
        except OSError:
            print("Issue recieving data. stopping inbound_message_handler for connection %s", connection.id)

            # handle corrupted inbound data from peer. This is not a realistic failure scenario for an Ably client so will break loop
            break

        # handle corrupted inbound data from peer. This is not a realistic failure scenario for an Ably client so will break loop
        except EOFError:
            print("recieved corrupted data from peer. Peer likely closed connection. Server disconnecting from peer for connection %s", connection.id)
            break

def check_heartbeat_ack(connection, lock):
    """
    Function to ensure heartbeats are being recieved from client
    """

    # Continuous loop that considers status of peer client threads
    while not connection.connection_thread_stopper.is_set():

        # get current timestamp
        current_time = time.time()

        try:
            with lock:

                # check for three missed heartbeats
                if current_time - connection.last_heartbeat_ack > HEARTBEAT_INTERVAL * 3:
                    print("Heartbeat_acks are not being recieved from client. Disconnecting Client...")
                    
                    # close treads and socket
                    end_connection(connection)

                    #break loop
                    break

        except OSError:
            print("OSError hit attemptng to aquire the threading lock to update the connection's last_heartbeat_ack for connection %s" , connection.id)
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
            send_message(connection.conn, "Heartbeat" , "", SERVER_NAME)
            print(f"Sent Heartbeat to {connection.addr} at {time.time()}")
            time.sleep(HEARTBEAT_INTERVAL)

        # handle issue sending outbound data to peer. This is not a realistic failure scenario for an Ably client so will break loop / thread
        except OSError:
            print("OSError when trying to send heartbeat")
            break

def main():
    """
    main function for server
    """

    # define server address
    host = '127.0.0.1'
    port = 12331

    # start server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            s.listen(5)
            print("Server listening on port", port)

            # keep track of active connections.
            connection_list = []
        
        except OSError as error:
            # handle error when OS hasn't recycled port needed for binding
            if error.errno == 48:
                print("Socket has not been closed by OS yet. Wait before trying again")
            
            # handle error when socket isn't initialized poroperly
            elif error.errno == 22:
                print("Hit OSError: %s", error)

            # handle all other OS failures
            else:
                print("hit OSError: %s", error)       

        try:
            while True:
                # listen for new connections
                conn, addr = s.accept()
                print(f"Connected by {addr}")

                # instantiate connection object
                connection = Connection(conn)

                # give connection an id
                connection.id = str(uuid.uuid4())

                # set connection object peer address
                connection.addr = addr

                # add new connection to connections list
                connection_list.append(connection)

                # handle each client in a separate thread
                client_thread = threading.Thread(target=client_handler, args=(connection,))
                client_thread.start()

        except KeyboardInterrupt:
            print("Server stopped listening for new connections")

            # check for connections
            if len(connection_list) >= 1:

                # close sockets and stop threads for each connection
                for connection_object in connection_list:
                    end_connection(connection_object)
                    print("All connection sockets closed and threads stopped for connect %s" , connection_object.id)

        except OSError as error:
            # operating system is preventing the socket from accepting connections.
            if error.errno == 22:
                print("OS is preventing the socket from accepting connections.")

if __name__ == "__main__":

    # Configure logging
    logging.basicConfig(level=LOG_LEVEL,
                        filename=LOG_FILE_PATH,
                        format='[%(asctime)s] %(levelname)s: %(message)s',
                        datefmt='%m-%d %H:%M:%S')

    main()
