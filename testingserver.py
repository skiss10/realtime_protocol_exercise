"""
Socket server
"""

import socket
import threading
import time
import uuid
import pickle
import logging

from utils.connection import Connection
from utils.session_store import InMemoryStore
from utils.message_sender import send_message
from constants import HEARTBEAT_INTERVAL, LOG_LEVEL, LOG_FILE_PATH, RECONNECT_WINDOW

# create a unique server name
SERVER_NAME = str(uuid.uuid4())

# dictionary of all connections for this server
CONNECTION_LIST = {}

def generate_message(connection):
    """
    Function to generate messages to peer
    """

    print("Starting to send messages to client!")

    # continuous loop contingent on status of connection's threads
    while not connection.connection_thread_stopper.is_set():

        # get connection state from inbound message handlers before sending / continuing data stream
        if connection.state is None:
            pass

        elif connection.state == "reconnected":
            # try sending user input messages to peer
            try:
                # increment last recieved number
                connection.last_num_recv += 1

                
                send_message(connection.conn, "Data", connection.last_num_recv, SERVER_NAME)
                print(f"sent messages to client {connection.client_id} with payload: {connection.last_num_recv}")

                # send an incrementing counter every 1 second to server
                time.sleep(1)


            except OSError:
                print("Unable to send messages over the socket. Suspending generate_message")
                break
        else:
            # try sending user input messages to peer
            try:
                send_message(connection.conn, "Data", connection.last_num_sent, SERVER_NAME)
                print(f"sent messages to client {connection.client_id} with payload: {connection.last_num_sent}")

                # send an incrementing counter every 1 second to server
                time.sleep(1)

                # increment last number sent
                connection.last_num_sent += 1

            except OSError:
                print("Unable to send messages over the socket. Suspending generate_message")
                break

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
            print(f"socket for connection {connection.client_id} closed over connection {connection.id}")

    except OSError:
        print("Error closing the connections socket")

def client_handler(connection):
    """
    Handler function for all inbound clients
    """

    # define variable to stop threads associated with client
    connection.connection_thread_stopper = threading.Event()

    # define first hearbeat_ack timestamp as client_handler initiation time
    connection.last_heartbeat_ack = time.time()

    # create lock for shared last_heartbeat_ack variable between threads
    connection.threading_lock = threading.Lock()

    # spawn a new thread to handle inbound messages from client
    inbound_messages_thread = threading.Thread(target=inbound_message_handler, args=(connection,))
    inbound_messages_thread.start()

    # spawn a new thread to monitor heartbeats_acks from the client
    heartbeat_ack_thread = threading.Thread(target=check_heartbeat_ack, args=(connection,))
    heartbeat_ack_thread.start()

    # spawn a new thread to send messages to the peer
    message_thread = threading.Thread(target=generate_message, args=(connection,))
    message_thread.start()

    # spawn a new thread to send heartbeats to the client
    heartbeat_thread = threading.Thread(target=send_heartbeat, args=(connection,))
    heartbeat_thread.start()

def greeting_message_handler(connection, message):
    """
    Function to handle client greeting message
    """
    try:
        # set connection state
        connection.state = "initial_connection"

        # assign client_id for connection
        connection.client_id = message.sender_id

        # send greeting ack response with connection id inclueded
        send_message(connection.conn, "Greeting_ack", connection.id, SERVER_NAME)

    except OSError:
        print("OSError hit attemptng send Greeting_ack. stopping inbound_message_handler thread for connection, %s", connection.client_id)

def reconnection_attempt_message_handler(connection, message):
    """
    Function to handle reconnections from the client
    """

    # assign client_id for connection
    connection.client_id = message.sender_id
    print(f"reconnection attempt from client {connection.client_id}")

    # boolean to see if connection object exists
    connection_id_not_found = True

    # Loop over connections connections in data store
    for _, connection_object in CONNECTION_LIST.items():

        # check if the requested connection_id is there
        if connection_object.id == message.data[0]:

            # set boolean as connection id from message found in storage
            connection_id_not_found =  False

            # get current timestamp
            current_time = time.time()

            # see if the last heartbeat ack was recieved within the reconnection window
            if current_time - connection_object.last_heartbeat_ack < RECONNECT_WINDOW:

                # pick up stream where it left off
                connection.last_num_sent = connection_object.last_num_sent
                print("successful reconnect attempt")

                # set connection condition
                connection.state = "reconnected"

                # set last message recieved
                connection.last_num_recv = message.data[1]

            else:
                
                print(f"reconnection request from {message.sender_id} rejected because the reconnection window timed out")
                send_message(connection.conn, "Reconnect_Rejected", "timeout", send_message)

    if connection_id_not_found:
        print(f"reconnect request from {message.sender_id} was rejected as there is no record of the provided connection_id state")
        send_message(connection.conn, "Reconnect_Rejected", "no_recorded_state", send_message)

def heartbeat_ack_message_handler(connection):
    """
    Function to handle heartbeat ack messages from client
    """
    try:
        # aquire lock to update shared last_heartbeat_ack variable in other threads
        with connection.threading_lock:

            # update last heartbeat ack timestamp
            connection.last_heartbeat_ack = time.time()

    except OSError:
        print("OSError hit attemptng to aquire the threading lock to update the connection's last_heartbeat_ack. stopping inbound_message_handler thread for connection, %s", connection.client_id)

def inbound_message_handler(connection):
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
            print(f"Received message type {message.name} from {message.sender_id} with data: {message.data}" )

            # check if the messages is a heartbeat_ack
            if message.name == "Heartbeat_ack":
                heartbeat_ack_message_handler(connection)

            # check if the messages is a greeing
            elif message.name == "Greeting":
                greeting_message_handler(connection, message)

            # check if the messages is a reconnect
            elif message.name == "reconnect_attempt":
                reconnection_attempt_message_handler(connection, message)

        # handle socket read errors
        except OSError:
            print("Issue recieving data. stopping inbound_message_handler for connection %s", connection.client_id)

            # handle corrupted inbound data from peer. This is not a realistic failure scenario for an Ably client so will break loop
            break

        # handle corrupted inbound data from peer. This is not a realistic failure scenario for an Ably client so will break loop
        except EOFError:
            print("recieved corrupted data from peer. Peer likely closed connection. suspending inbound_message_handler for %s", connection.client_id)
            break

def check_heartbeat_ack(connection):
    """
    Function to ensure heartbeats are being recieved from client
    """

    # Continuous loop that considers status of peer client threads
    while not connection.connection_thread_stopper.is_set():

        # get current timestamp
        current_time = time.time()

        try:
            with connection.threading_lock:

                # check for three missed heartbeats
                if current_time - connection.last_heartbeat_ack > HEARTBEAT_INTERVAL * 3:
                    print("Heartbeat_acks are not being recieved from client. Disconnecting Client %s", connection.client_id)
                    
                    # close threads and socket
                    end_connection(connection)

                    #break loop
                    break

        except OSError:
            print("OSError hit attemptng to aquire the threading lock to update the connection's last_heartbeat_ack for connection %s" , connection.client_id)
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
            print(f"Sent Heartbeat to {connection.client_id}")
            time.sleep(HEARTBEAT_INTERVAL)

        # handle issue sending outbound data to peer. This is not a realistic failure scenario for an Ably client so will break loop / thread
        except OSError:
            print("OSError when trying to send heartbeat. Suspending send_heartbeat function")
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

                # create connection session storage
                connection.session_storage = InMemoryStore()

                # add new connection to connections list
                CONNECTION_LIST[connection.id]=connection

                # handle each client in a separate thread
                client_thread = threading.Thread(target=client_handler, args=(connection,))
                client_thread.start()

        except KeyboardInterrupt:
            print("Server stopped listening for new connections")

            # check for connections
            if len(CONNECTION_LIST) >= 1:

                # close all sockets and stop threads for each connection
                for _, connection_object in CONNECTION_LIST.items():
                    end_connection(connection_object)
                    print(f"All connection sockets closed and threads stopped for connection {connection_object.id} and client {connection_object.client_id}")

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
