"""
Socket client
"""

import socket
import threading
import time
import uuid
import pickle

from constants import HEARTBEAT_INTERVAL, LOG_LEVEL, LOG_FILE_PATH
from utils.message_sender import send_message
from utils.connection import Connection

CLIENT_NAME = str(uuid.uuid4())

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

def connection_handler(connection):
    """
    Function to recieve messages from the server
    """

    # define first hearbeat timestamp as this function's initiation timestamp
    connection.last_heartbeat_ack = time.time()

    # spawn a new thread to handle inbound messages from server
    inbound_message_thread = threading.Thread(target=inbound_message_handler, args=(connection,))
    inbound_message_thread.start()

    # spawn a new thread to check incoming heartbeats from server
    check_heartbeat_thread = threading.Thread(target=check_heartbeat, args=(connection,))
    check_heartbeat_thread.start()

    inbound_message_thread.join()
    check_heartbeat_thread.join()

def inbound_message_handler(connection):
    """
    Function to handle inbound messages from Server
    """

    # continuous loop contingent on status of connection's threads
    while not connection.connection_thread_stopper.is_set():

        # recieve inbound messages
        try:
            message = connection.conn.recv(1024)

            # unserialize messages
            unserialized_message = pickle.loads(message)

            # check if the messages is a heartbeat
            if unserialized_message.name == "Heartbeat":
                print(f"Received heartbeat at {time.time()}")

                # send heartbeat_ack back to server
                send_message(connection.conn, "Heartbeat_ack", "Heartbeat_ack", CLIENT_NAME)
                print("Sent Heartbeat_ack")

                # update last heartbeat timestamp
                connection.last_heartbeat_ack = time.time()

            # check if the messages is a Greeting_ack
            elif unserialized_message.name == "Greeting_ack":
                print("Received Greeting_ack")
                print("connection_id from server is %s", unserialized_message.data)

                # assign connection id
                connection.id = unserialized_message.data

            elif unserialized_message.name == "Data":
                print("recieved message from server with payload: %s", unserialized_message.data)

        # trigger error when thread can't read from socket
        except OSError:
            print("Error reading from Socket")
            break

        # trigger error when incomplete message arrives from peer due to disruption / failure
        except EOFError:
            print("Error reading from Socket. Suspending inbound_message_handler")
            break

def attempt_reconnection(connection):
    """
    Function to handle reconnection attempts
    """

    # attempt to establish the same connection again
    try:
        server_handler(connection.addr, connection.id)

    # continue to try reconnection every 10 seconds
    except OSError:
        print("unable to reconnect to server, trying again in 10 seconds...")
        time.sleep(10)
        attempt_reconnection(connection)

def check_heartbeat(connection):
    """
    Function to check heartbeats coming from server
    """

    # continuous loop contingent on status of connection's threads
    while not connection.connection_thread_stopper.is_set():

        # get current time
        current_time = time.time()

        # check how long its been since last heartbeat
        if current_time - connection.last_heartbeat_ack > 3 * HEARTBEAT_INTERVAL:

            # handle missed heartbeats
            print("Heartbeats not recieved from server. Disconnecting from server...")
            end_connection(connection)

            # start attempting to reconnect to server
            attempt_reconnection(connection)

            break

        time.sleep(1)

def server_handler(peer_address, existing_connection_id = None):
    """
    Function to connection to a peer socket server
    """

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
        try:
            conn.connect(peer_address)
            print("Connected to server")

            # instantiate connection object
            connection = Connection(conn)
            
            # set connection object peer address tuple
            connection.addr = peer_address

            if existing_connection_id == None:
                # send gretting message to peer
                send_message(connection.conn, "Greeting", "", CLIENT_NAME)
                print("sent greeting message")

            else:
                # send reconnect message to peer
                send_message(connection.conn, "reconnect_attempt", existing_connection_id, CLIENT_NAME)
                print("sent reconnection message")

            # define variable to stop threads associated with peer connection
            connection.connection_thread_stopper = threading.Event()

            # spawn a new thread to handle inbound messages from the peer
            connection_handler_thread = threading.Thread(target=connection_handler, args=(connection,))
            connection_handler_thread.start()
            connection_handler_thread.join()

        # stop threads and close connection if keyboard interrupt
        except KeyboardInterrupt:
            end_connection(connection)

def main():
    """
    Main function for client
    """

    # define peer location
    host = '127.0.0.1'
    port = 12332

    # peer address tuple
    peer_address = (host,port)

    # attempt to connection to server
    try:
        server_handler(peer_address)

    except OSError:
        print("Unable to connect to server. Has the Server been started?")

if __name__ == "__main__":
    print(CLIENT_NAME)
    main()