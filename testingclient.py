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

        except OSError:
            print("Error reading from Socket. Suspending inbound_message_handler")
            break

        # when incomplete message arrives from peer due to disruption / failure
        except EOFError:
            print("Error reading from Socket. Suspending inbound_message_handler")
            break

def attempt_reconnection(connection):
    """
    Function to handle reconnection attempts
    """

    # attempt to establish the same connection again
    try:
        server_handler(connection.addr)

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
        current_time = time.time()

        if current_time - connection.last_heartbeat_ack > 3 * HEARTBEAT_INTERVAL:
            print("Heartbeats not recieved from server. Disconnecting from server...")
            connection.connection_thread_stopper.set()
            connection.conn.close()
            attempt_reconnection(connection)

        time.sleep(1)

def generate_message(connection):
    """
    Function to generate messages to peer
    """

    print("Begin typing your messages to the server!")

    # continuous loop contingent on status of connection's threads
    while not connection.connection_thread_stopper.is_set():

        # try sending user input messages to peer
        try:
            data = input("Enter message to send: ")
            send_message(connection.conn, "Data", data, CLIENT_NAME)

        except OSError:
            print("Unable to send messages over the socket. Suspending generate_message function")
            break

def server_handler(peer_address):
    """
    Function to connection to a peer socket server
    """

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
        conn.connect(peer_address)
        print("Connected to server")

        # instantiate connection object
        connection = Connection(conn)
        
        # set connection object peer address tuple
        connection.addr = peer_address

        # send gretting message to peer
        send_message(connection.conn, "Greeting", "", CLIENT_NAME)

        # define variable to stop threads associated with peer connection
        connection.connection_thread_stopper = threading.Event()

        # spawn a new thread to handle inbound messages from the peer
        heartbeat_thread = threading.Thread(target=connection_handler, args=(connection,))
        heartbeat_thread.start()

        # spawn a new thread to send messages to the peer
        message_thread = threading.Thread(target=generate_message, args=(connection,))
        message_thread.start()

        heartbeat_thread.join()
        message_thread.join()

def main():
    """
    Main function for client
    """

    # define peer location
    host = '127.0.0.1'
    port = 12331

    # peer address tuple
    peer_address = (host,port)

    # attempt to connection to server
    try:
        server_handler(peer_address)

    except OSError:
        print("Unable to connect to server.")

if __name__ == "__main__":
    main()