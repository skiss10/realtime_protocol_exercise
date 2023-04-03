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

# define server interface with memory store
SESSION_STORAGE = InMemoryStore()

def generate_message(connection):
    """
    Function to generate messages to peer
    """

    print("Starting to send messages to client!")
    logging.info(f"{SERVER_NAME} Server - Messages - Started sending messages to client {connection.client_id} over connection {connection.id}")

    # continuous loop contingent on status of connection's threads
    while not connection.connection_thread_stopper.is_set():

        # get connection state from inbound message handlers before sending / continuing data stream
        if connection.state is None:
            pass

        elif connection.state == "reconnected":
            # try sending user input messages to peer
            try:
                send_message(connection.conn, "Data", connection.continue_stream_from, SERVER_NAME)
                print(f"sent messages to client {connection.client_id} with payload: {connection.continue_stream_from}")
                logging.info(f"{SERVER_NAME} Server - Messages -sending message to {connection.client_id} over connection {connection.continue_stream_from}")

                # send an incrementing counter every 1 second to server
                time.sleep(1)

                # increment last number sent
                connection.continue_stream_from += 1 #TODO fix this ugliness

            except OSError:
                print("Unable to send messages over the socket. Suspending generate_message")
                logging.error(f"{SERVER_NAME} Server - Message - Unable to send messages over the socket. Suspending generate_message")
                break
        else:
            # try sending user input messages to peer
            try:
                send_message(connection.conn, "Data", connection.last_num_sent, SERVER_NAME)
                print(f"sent messages to client {connection.client_id} with payload: {connection.last_num_sent}")
                logging.info(f"{SERVER_NAME} Server - Message- Sent message to client {connection.client_id} with payload: {connection.last_num_sent}")

                # send an incrementing counter every 1 second to server
                time.sleep(1)

                # increment last number sent
                connection.last_num_sent += 1

            except OSError:
                print("Unable to send messages over the socket. Suspending generate_message")
                logging.error(f"{SERVER_NAME} Server - Message - Unable to send messages over the socket. Suspending generate_message")
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
            logging.info(f"{SERVER_NAME} Server - Connection - Threads for connection {connection.id} to client {connection.client_id} are flagged to stop")

    except OSError:
        print("Error stopping the connection's theads")

    # close the connection's socket
    try:
        if connection.state != "closed":
            connection.state = "closed"
            connection.conn.close()
            print(f"socket connection_id {connection.id} closed pointing to client {connection.client_id}")
            logging.info(f"{SERVER_NAME} Server - Connection - Closed socket connection_id {connection.id} to client {connection.client_id}")

    except OSError:
        print(f"Error closing connection socket for {connection.id}")
        logging.error(f"{SERVER_NAME} Server - Connection - Error closing the connections socket for {connection.id}")

def client_handler(connection):
    """
    Handler function for all inbound clients
    """

    # spawn a new thread to handle inbound messages from client
    inbound_messages_thread = threading.Thread(target=inbound_message_handler, args=(connection,))
    inbound_messages_thread.start()
    logging.debug(f"{SERVER_NAME} Server - Started inbound_message_handler thread for connection {connection.id}")

    # spawn a new thread to monitor heartbeats_acks from the client
    heartbeat_ack_thread = threading.Thread(target=check_heartbeat_ack, args=(connection,))
    heartbeat_ack_thread.start()
    logging.debug(f"{SERVER_NAME} Server - Started check_heartbeat_ack thread for connection {connection.id}")

    # spawn a new thread to send messages to the peer
    message_thread = threading.Thread(target=generate_message, args=(connection,))
    message_thread.start()
    logging.debug(f"{SERVER_NAME} Server - Started generate_message thread for connection {connection.id}")

    # spawn a new thread to send heartbeats to the client
    heartbeat_thread = threading.Thread(target=send_heartbeat, args=(connection,))
    heartbeat_thread.start()
    logging.debug(f"{SERVER_NAME} Server - Started send_heartbeat thread for connection {connection.id}")

def greeting_message_handler(connection, message):
    """
    Function to handle client greeting message
    """
    try:
        # assign client_id for connection
        connection.client_id = message.sender_id
        logging.debug(f"{SERVER_NAME} Server - Connection - client_id for {connection.id} updated to {connection.client_id}")

        # set connection state
        connection.state = "initial_connection"
        logging.debug(f"{SERVER_NAME} Server - Connection - connection state for {connection.id} updated to {connection.state}")

        # send greeting ack response with connection id inclueded
        send_message(connection.conn, "Greeting_ack", connection.id, SERVER_NAME)
        logging.info(f"{SERVER_NAME} Server - Message - Greeting_ack sent over {connection.id} to {connection.client_id}")

    except OSError as error:
        print("OSError hit attemptng send Greeting_ack. stopping inbound_message_handler thread for connection, %s", connection.client_id)
        logging.error(f"{SERVER_NAME} Server - Message - error {error} sending greeting_ack over {connection.id} to {connection.client_id}")

def reconnection_attempt_message_handler(connection, message):
    """
    Function to handle reconnections from the client
    """

    # assign client_id for connection
    connection.client_id = message.sender_id
    print(f"reconnection attempt from client {connection.client_id}")
    logging.info(f"{SERVER_NAME} Server - Reconnection - recieved reconnection attempt from {connection.client_id} over connection_id {connection.id}")

    # boolean to see if connection object exists
    connection_id_not_found = True

    # Loop over connections connections in data store
    for _, connection_object in SESSION_STORAGE.store.items():

        # check if the requested connection_id is there
        if connection_object.id == message.data[0]:

            # log that we found the connection_id provided by the connected peer
            logging.info(f"{SERVER_NAME} Server - Reconnection - connection_id {message.data[0]} provided by {message.sender_id} over new connection_id {connection.id} was found in session_store")

            # set boolean as connection id from message found in storage
            connection_id_not_found =  False

            # get current timestamp
            current_time = time.time()

            # see if the last heartbeat ack was recieved within the reconnection window
            if current_time - connection_object.last_heartbeat_ack < RECONNECT_WINDOW:

                # update last_heartbeat so check_session_store removes the connection sooner but gives reconnection_attempt_message_handler enough time to get needed data
                connection_object.last_heartbeat_ack = time.time() - 58

                # pick up stream where it left off
                connection.last_num_sent = connection_object.last_num_sent
                print("successful reconnect attempt")
                logging.info(f"{SERVER_NAME} Server - Reconnection - Successful reconnection attempt from {message.sender_id}")

                # configure next message to send
                connection.continue_stream_from = message.data[1]
                logging.debug(f"{SERVER_NAME} Server - Reconnection - Last Reported Number received by {message.sender_id} was {message.data[1]}")

                # set connection cleint_id
                connection.client_id = message.sender_id

                # set connection condition
                connection.state = "reconnected"

            else:
                
                print(f"reconnection request from {message.sender_id} rejected because the reconnection window timed out")
                send_message(connection.conn, "Reconnect_Rejected", "timeout", send_message)
                logging.info(f"{SERVER_NAME} Server - Reconnection - Failed reconnection attempt from {message.sender_id} because reconnection window timed out")

    if connection_id_not_found:
        print(f"reconnect request from {message.sender_id} was rejected as there is no record of the provided connection_id")
        send_message(connection.conn, "Reconnect_Rejected", "no_recorded_state", send_message)
        logging.info(f"{SERVER_NAME} Server - Reconnection - Failed reconnection attempt from {message.sender_id} as there is no record of the provided connection_id")

def heartbeat_ack_message_handler(connection):
    """
    Function to handle heartbeat ack messages from client
    """
    try:
        # aquire lock to update shared last_heartbeat_ack variable in other threads
        with connection.threading_lock:

            # update last heartbeat ack timestamp
            connection.last_heartbeat_ack = time.time()
            logging.debug(f"{SERVER_NAME} Server - Heartbeat_ack - Updated heartbeat_ack timestamp for connection {connection.id}")


    except OSError as err:
        print("OSError hit attemptng to aquire the threading lock to update the connection's last_heartbeat_ack. stopping inbound_message_handler thread for connection, %s", connection.client_id)
        logging.error(f"{SERVER_NAME} Server - Heartbeat_ack - error {err} updating heartbeat_ack timestamp for connection {connection.id}")

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
            logging.info(f"{SERVER_NAME} Server - Message - Received message type {message.name} on connection {connection.id} from {message.sender_id} with data: {message.data}")

            # check if the messages is a heartbeat_ack
            if message.name == "Heartbeat_ack":
                heartbeat_ack_message_handler(connection)
                logging.debug(f"{SERVER_NAME} Server - Message - Sent type {message.name} from {message.sender_id} over {connection.id} to triggered heartbeat_ack_message_handler")

            # check if the messages is a greeing
            elif message.name == "Greeting":
                greeting_message_handler(connection, message)
                logging.debug(f"{SERVER_NAME} Server - Message - Sent type {message.name} from {message.sender_id} over {connection.id} to triggered greeting_message_handler")

            # check if the messages is a reconnect
            elif message.name == "reconnect_attempt":
                reconnection_attempt_message_handler(connection, message)
                logging.debug(f"{SERVER_NAME} Server - Message - Sent type {message.name} from {message.sender_id} over {connection.id} to triggered reconnect_attempt")


        # handle socket read errors
        except OSError as error:
            print("Issue recieving data. stopping inbound_message_handler for connection %s", connection.client_id)
            logging.error(f"{SERVER_NAME} Server - Message - Error {error} recieving data from {connection.client_id} over connection {connection.id}. Stopping inbound_message_handler for {connection.id}")

            # handle corrupted inbound data from peer. This is not a realistic failure scenario for an Ably client so will break loop
            break

        # handle corrupted inbound data from peer. This is not a realistic failure scenario for an Ably client so will break loop
        except EOFError as error:
            print("recieved corrupted data from peer. Peer likely closed connection. suspending inbound_message_handler for %s", connection.client_id)
            logging.error(f"{SERVER_NAME} Server - Message - Error {error}. Recieved corrupted data from {connection.client_id}. Peer likely closed connection. suspending inbound_message_handler for {connection.id}")
            break

def check_heartbeat_ack(connection):
    """
    Function to ensure heartbeats are being recieved from client
    """

    # Continuous loop that considers status of other client threads
    while not connection.connection_thread_stopper.is_set():

        # get current timestamp
        current_time = time.time()

        try:
            with connection.threading_lock:

                # check for three missed heartbeats
                if current_time - connection.last_heartbeat_ack > HEARTBEAT_INTERVAL * 3:
                    print(f"Heartbeat_acks are not being recieved from client. Disconnecting Client {connection.client_id}")
                    logging.info(f"{SERVER_NAME} Server - Heartbeats - Heartbeat_acks are not being recieved from {connection.client_id} over {connection.id}. Disconnecting Client {connection.client_id}")
                    # close threads and socket
                    end_connection(connection)

                    #break loop
                    break

        except OSError as error:
            print("OSError hit attemptng to aquire the threading lock to update the connection's last_heartbeat_ack for connection %s" , connection.client_id)
            logging.error(f"{SERVER_NAME} Server - Heartbeats - OSError {error} hit attemptng to aquire the threading lock to update the connection {connection.id}'s last_heartbeat_ack")
            break

        # sleep thread checking for heartbeat_acks
        time.sleep(1)

def send_heartbeat(connection):
    """
    Function to continously send heartbeats from the server
    to the client
    """

    # Continuous loop that considers status of other client threads
    while not connection.connection_thread_stopper.is_set():

        # check session state before sending heartbeats
        if connection.state in ['initial_connection', 'reconnected']:

            # send heartbeats
            try:
                send_message(connection.conn, "Heartbeat" , "", SERVER_NAME)
                print(f"Sent Heartbeat to {connection.client_id}")
                logging.debug(f"{SERVER_NAME} Server - Heartbeat - Sent Heartbeat to {connection.client_id}")
                time.sleep(HEARTBEAT_INTERVAL)

            # handle issue sending outbound data to peer. This is not a realistic failure scenario for an Ably client so will break loop / thread
            except OSError as error:
                print("OSError when trying to send heartbeat. Suspending send_heartbeat function")
                logging.error(f"{SERVER_NAME} Server - Heartbeat - Error {error} when trying to send heartbeat over {connection.client_id}. Suspending send_heartbeat function")
                break


def check_session_store():
    """
    Function to ensure heartbeats are being recieved from client
    """

    print("Started check_session_store")
    logging.info(f"{SERVER_NAME} Server - Storage - check_session_store is running")

    # Continuous loop that considers status of other client threads
    while True:

        # get current timestamp
        current_time = time.time()

        active_connections = SESSION_STORAGE.store.items()

        stale_connections = []

        try:
            for _, connection_object in active_connections:

                # check for stale connection entries
                # adding one second to give reconnection_attempt_message_handler time to evaluate last heartbeat
                if current_time - connection_object.last_heartbeat_ack > RECONNECT_WINDOW +1:
                    
                    # add stale connections to list for removal
                    stale_connections.append(connection_object)

                    print(f"Adding {connection_object.id} to session removal list due to not recieving new heartbeats_acks over that connection's socket within RECONNECT_WINDOW")
                    logging.info(f"{SERVER_NAME} Server - Storage - Preparing to remove {connection_object.id} from session storage due to not recieving new heartbeats_acks over that connection's socket within RECONNECT_WINDOW")

        except OSError as error:
            print("OSError hit in check_session_store.")
            logging.error(f"{SERVER_NAME} Server - Heartbeats - OSError {error} hit OSError hit in check_session_store. Suspending check_session_store")
            break

        # remove stale connections outside of loop
        for connection_object in stale_connections:
            if connection_object.id in SESSION_STORAGE.store:
                SESSION_STORAGE.delete(connection_object.id)
                print(f"Server removed stale connection {connection_object.id} from session_store")
                logging.info(f"{SERVER_NAME} Server - Storage - Server removied stale connection {connection_object.id} from session_store")

        # sleep thread checking for heartbeat_acks
        time.sleep(1)

def main():
    """
    main function for server
    """

    # define server address
    host = '127.0.0.1'
    port = 12331

    check_session_store_thread = threading.Thread(target=check_session_store, args=())
    check_session_store_thread.start()
    logging.debug(f"{SERVER_NAME} Server - Storage - started check_session_store_thread")

    # start server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            s.listen(5)
            print("Server listening on port", port)
            logging.info(f"{SERVER_NAME} Server - Socket - Listening on localhost:{port} ...")
        
        except OSError as error:
            # handle error when OS hasn't recycled port needed for binding
            if error.errno == 48:
                print("Socket has not been closed by OS yet. Wait before trying again")
                logging.error(f"{SERVER_NAME} Server - Socket - Socket port has not been closed by OS yet. port: {port}")
            
            # handle error when socket isn't initialized poroperly
            elif error.errno == 22:
                print("Hit OSError: %s", error)
                logging.error(f"{SERVER_NAME} Server - Socket - Hit OS error: {error}")

            # handle all other OS failures
            else:
                print("hit OSError: %s", error)
                logging.error(f"{SERVER_NAME} Server - Socket - Hit OS error: {error}")

        # handle inbound connection attempts
        try:

            # listen for new connections
            while True:
                conn, addr = s.accept()
                print(f"Connected by {addr}")
                logging.info(f"{SERVER_NAME} Server - Socket - Recieved connection on:{addr} ...")

                # instantiate connection object
                connection = Connection(conn, addr)

                logging.debug(f"{SERVER_NAME} Server - Socket - Assigned connection_id {connection.id} to connection over {addr}")

                # add new connection to connections list
                SESSION_STORAGE.set(connection.id, connection)

                # handle each client in a separate thread
                client_thread = threading.Thread(target=client_handler, args=(connection,))
                client_thread.start()
                logging.debug(f"{SERVER_NAME} Server - client_handler - started client_handler thread for connection: {connection.id} ...")

        except KeyboardInterrupt:
            print("Server stopped listening for new connections")

            # check for connections
            if len(SESSION_STORAGE.store) >= 1:

                # close all sockets and stop threads for each connection
                for _, connection_object in SESSION_STORAGE.store.items():
                    end_connection(connection_object)
                    print(f"All connection sockets closed and threads stopped for connection {connection_object.id} and client {connection_object.client_id}")

        except OSError as error:
            # operating system is preventing the socket from accepting connections.
            if error.errno == 22:
                print("OS is preventing the socket from accepting connections.")
                logging.error(f"{SERVER_NAME} Server - System - OS is preventing the socket from accepting new connections.")

if __name__ == "__main__":

    # Configure logging
    logging.basicConfig(
        level=LOG_LEVEL,
        filename=LOG_FILE_PATH,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%m-%d %H:%M:%S'
        )
    
    logging.info("===== Server - starting %s =====", SERVER_NAME)

    # start server
    main()
