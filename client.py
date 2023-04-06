"""
Socket client

Author: Stephen Kiss (stephenkiss986@gmail.com)
Date: 01/23/2023
"""


import socket
import threading
import time
import uuid
import pickle
import logging
import sys
import random

from constants import HEARTBEAT_INTERVAL, LOG_LEVEL, LOG_FILE_PATH, SERVER_DEFAULT_PORT
from utils.message_sender import send_message
from utils.connection import Connection
from utils.checksum import calculate_checksum

CLIENT_NAME = str(uuid.uuid4())

def end_connection(connection):
    """
    Function to stop all threads and close all sockets for a given connection
    """

    # stop threads related to connection
    try:

        # check status of connection_thread_stopper
        if not connection.connection_thread_stopper.is_set():

            # set connection's threads to stop
            connection.connection_thread_stopper.set()

            # log stopping threads
            print(f"connection - conn id {connection.id} stopping threads")
            logging.info(f" connection - conn id {connection.id} stopping threads")

    # handle OSError stopping connection's threads
    except OSError as error:

        # log error
        print(f"system - err {error} conn id {connection.id} when stopping threads")
        logging.error(f"system - err {error} conn id {connection.id} when stopping threads")

    # close the connection's socket
    try:

        # check connection state
        if connection.state != "closed":

            # set connection state to closed
            connection.state = "closed"

            # close connection
            connection.conn.close()

            # log closing connection
            print(f"connection - conn id {connection.id} is closed")
            logging.info(f" connection - conn id {connection.id} is closed")

    # handle OSError closing connection's socket
    except OSError as error:

        # log error
        print(f"system - err {error} conn id {connection.id} when closing sockets")
        logging.error(f"system - err {error} conn id {connection.id} when closing sockets")

def handle_greeting_ack(connection, unserialized_message):
    """
    Function to handle incoming messages of type "greeting_ack" from server
    """

    # assign connection id from server to client's connection object
    connection.id = unserialized_message.data

    # inform user
    print(f"message - recieved greeting_ack")
    print(f"message - new conn id {connection.id}")
    logging.info(f" message - recieved greeting_ack")
    logging.info(f" message - new conn id {connection.id}")

def handle_heartbeats(connection):
    """
    Function to handle incoming messages of type "heartbeat" from server
    """
    
    # log heartbeat
    print(f"message - recieved heartbeat")
    logging.info(f" message - conn id {connection.id} received heartbeat")

    # send heartbeat_ack back to server
    send_message(connection.conn, "Heartbeat_ack", "Heartbeat_ack", CLIENT_NAME)

    # log sent heartbat response
    print(f"heartbeat - sent heartbeat_ack")
    logging.info(f" heartbeat - sent heartbeat_ack")

    # update last heartbeat timestamp
    connection.last_heartbeat_ack = time.time()

def handle_data(connection, unserialized_message):
    """
    Function to handle incoming messages of type "data" from server
    """
                
    # gather newly recieved payload
    uint32_num = unserialized_message.data

    # add new uint32 number to connection uint32_numbers_recieved attribute
    connection.uint32_numbers_recieved.append(uint32_num)

    # log mesasge info
    print(f"message - recieved message type {unserialized_message.name} with payload: {unserialized_message.data}")
    logging.info(f" message - recieved message type {unserialized_message.name} with payload: {unserialized_message.data}")

def handle_checksum(connection, unserialized_message):
    """
    Function to handle incoming messages of type "checksum" from server
    """

    # gather checksum from server
    server_checksum = unserialized_message.data

    # log checksum
    print(f"checksum - server checksum {server_checksum}")
    logging.info(f" checksum - server checksum {server_checksum}")

    # calculate checksum locally
    local_checksum = calculate_checksum(connection.uint32_numbers_recieved)
    print(f"checksum - local checksum {local_checksum}")
    logging.info(f" checksum - local checksum {local_checksum}")

    # determine if checksums are equivalent
    if local_checksum == server_checksum:

        # inform user of successful transfer of uint32 numbers
        print(f"system - SUCCESS! local checksum and server checksum are equal")
        logging.info(f" system - SUCCESS! local checksum and server checksum are equal")

    # end connection
    end_connection(connection)

    # close program
    sys.exit()

def handle_reconnect_rejection(connection, unserialized_message):
    """
    Function to handle incoming messages of type "Reconnect_rejected" from server
    """

    # inform user of reconnection failure
    print(f"reconnection - failed: {unserialized_message.data}")
    logging.info(f" reconnection - failed: {unserialized_message.data}")

    # close connection
    end_connection(connection)

def handle_reconnect_accepted(connection, unserialized_message):
    """
    Function to handle incoming messages of type "Reconnect_accepted" from server
    """

    # set new connection id
    connection.id = unserialized_message.data

    # inform user of reconnection accepted
    print(f"reconnection - accepted. new conn id {connection.id}")
    logging.info(f" reconnection - accepted. new conn id {connection.id}")

def inbound_message_handler(connection):
    """
    Function to handle inbound messages from Server
    """

    # continuous loop contingent on status of connection's threads
    while not connection.connection_thread_stopper.is_set():

        # recieve inbound messages
        try:

            # recieve new messages over the socket
            message = connection.conn.recv(1024)

            # unserialize messages
            unserialized_message = pickle.loads(message)

            # check if the messages is a Greeting_ack
            if unserialized_message.name == "Greeting_ack":
                handle_greeting_ack(connection, unserialized_message)
        
            if unserialized_message.name == "Data":
                handle_data(connection, unserialized_message)
            
            # check if the messages is a heartbeat
            if unserialized_message.name == "Heartbeat":
                handle_heartbeats(connection)

            if unserialized_message.name == "Checksum":
                handle_checksum(connection, unserialized_message)

            if unserialized_message.name == "Reconnect_rejected":
                handle_reconnect_rejection(connection, unserialized_message)

            if unserialized_message.name == "Reconnect_accepted":
                handle_reconnect_accepted(connection, unserialized_message)

        # trigger error when thread can't read from socket
        except OSError as error:

            # inform user of error when thread can't read from socket
            print(f"system - err {error} when reading message from server")
            print(f"system - suspending inbound_message_handler")
            logging.error(f"system - err {error} when reading message from server")
            logging.info(f" system - suspending inbound_message_handler")

            # stop / suspend inbound_message_handler thread
            break

        # trigger error when incomplete message arrives from peer due to disruption / failure
        except EOFError as error:

            # inform user of error when incomplete message arrives from peer due to disruption / failure
            print(f"system - err {error} when reading message from server")
            print(f"system - suspending inbound_message_handler")
            logging.error(f"system - err {error} when reading message from server")
            logging.info(f" system - suspending inbound_message_handler")

            # stop / suspend inbound_message_handler thread
            break

def check_heartbeat(connection):
    """
    Function to check that last_heartbeat_ack timestame in connection
    is being updated. Otherwise the connection is stale and needs to be dropped 
    """

    # continuous loop contingent on status of connection's threads
    while not connection.connection_thread_stopper.is_set():

        # get current time
        current_time = time.time()

        # check how long its been since last heartbeat for this connection
        if current_time - connection.last_heartbeat_ack > 3 * HEARTBEAT_INTERVAL:

            # inform user of missed heartbeats
            print(f"heartbeat - multiple missed heartbeats from server.")
            print(f"system - Suspending check_heartbeat. Disconnecting from server")
            logging.info(f" heartbeat - multiple missed heartbeats from server.")
            logging.info(f" system - Suspending check_heartbeat. Disconnecting from server")

            # close connection
            end_connection(connection)

            # start attempting to reconnect to server
            attempt_reconnection(connection)

            # stop / suspend check_heartbeat
            break

        # check_heartbeat again in one second
        time.sleep(1)

def connection_handler(connection):
    """
    Function to recieve messages from the server
    """

    # define first hearbeat timestamp as this function's initiation timestamp
    connection.last_heartbeat_ack = time.time()

    # spawn a new thread to handle inbound messages from server
    inbound_message_thread = threading.Thread(target=inbound_message_handler, args=(connection,))
    inbound_message_thread.start()
    
    # log thread start
    logging.debug(f"system - started inbound_message_handler thread")

    # spawn a new thread to check incoming heartbeats from server
    check_heartbeat_thread = threading.Thread(target=check_heartbeat, args=(connection,))
    check_heartbeat_thread.start()

    # log thread start
    logging.debug(f"system - started check_heartbeat thread")

    # run all threads until completed
    inbound_message_thread.join()
    check_heartbeat_thread.join()

def attempt_reconnection(connection):
    """
    Function to indefinitely handle reconnection attempts
    """

    # attempt to establish the same connection again
    try:

        # connect to server with old connection info
        server_handler(connection.addr, connection)

    # continue to try reconnection every 10 seconds
    except OSError:

        # inform user of issues reconnecting
        print(f"reconnection - server unreachable, trying again in 10 seconds...")
        logging.info(f" reconnection - server unreachable, trying again in 10 seconds...")

        # wait 10 seconds
        time.sleep(10)

        # try reconnecting again
        attempt_reconnection(connection)
   
def server_handler(peer_address, former_connection = None, sequence_length = None):
    """
    Function to connection to a peer socket server
    """

    # create context for new socket object
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:

        # connect to peer address
        try:

            # estabislih connection
            conn.connect(peer_address)
            print(f"connection - connected to server at {peer_address}")
            logging.info(f" connection - connected to server at {peer_address}")

            # instantiate connection object
            connection = Connection(conn, peer_address)
            
            # set connection object peer address tuple
            connection.addr = peer_address

            # adding this conditional for test.py
            if sequence_length is None:

                # set sequence length / generate sequence lengeth if not explictly set on command line
                connection.sequence_length = int(sys.argv[2]) if len(sys.argv) > 2 else random.randint(1, 0xffff)

            else:

                # test with a default sequence_length of 11
                connection.sequence_length = 11

            # define variable to stop threads associated with connection
            connection.connection_thread_stopper = threading.Event()

            # check if a previous connection was supplied
            if former_connection is None:

                # send greeting message to peer
                send_message(connection.conn, "Greeting", connection.sequence_length, CLIENT_NAME)

                # log greeting
                print(f"message - sent greeting")
                logging.info(f" message - sent greeting")

            else:

                # map formerly recieved numbers from previous connection into new connection object
                connection.uint32_numbers_recieved = former_connection.uint32_numbers_recieved

                # send reconnect message to server with previous connection_id and last message recieved by this client
                send_message(connection.conn, "reconnect_attempt", (former_connection.id, former_connection.uint32_numbers_recieved[-1]), CLIENT_NAME)
                
                # log reconnect_attempt
                print("message - sent reconnection message")
                logging.info(" message - sent reconnection message")
                logging.debug(f"message - sent reconnection for {former_connection.id} via conn id {connection.id} with last sequence payload of {former_connection.uint32_numbers_recieved[-1]}")

            # spawn a new thread to handle inbound messages from the peer
            connection_handler_thread = threading.Thread(target=connection_handler, args=(connection,))
            connection_handler_thread.start()
            connection_handler_thread.join()

            # inform the user connection_handler started
            logging.debug(f"system - started connection_handler thread for connection {connection.id}")

        # stop threads and close connection if keyboard interrupt
        except KeyboardInterrupt:

            # stop the connection
            end_connection(connection)

            # inform the user of Keyboard Interrupt
            logging.info(f" system - stopped due to keyboard interrupt")

def main():
    """
    Main function for client
    """

    # define peer location
    host = '127.0.0.1'

    # set default port (server port)
    port = SERVER_DEFAULT_PORT

    # handle optional input paramater for port
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    # peer address tuple
    peer_address = (host, port)

    # attempt to connection to server
    try:
        
        # connect to server
        server_handler(peer_address)

    # handle OS errors when attempting connection
    except OSError:

        # inform user of OSError
        print("system - unable to connect to server. Has the Server and/or proxy server been started? Is the port > 1023?")
        logging.info(f" system - unable to connect to server. as the Server and/or proxy server been started? Is the port > 1023?")

if __name__ == "__main__":

    # Configure logging
    logging.basicConfig(
    level=LOG_LEVEL,
    filename=LOG_FILE_PATH,
    format=f'[%(asctime)s] - Client - {CLIENT_NAME} - %(levelname)s - %(message)s',
    datefmt='%m-%d %H:%M:%S')

    # print client name to console
    print(f"===== Client - starting {CLIENT_NAME} =====")
    logging.info(f" ===== Client - starting {CLIENT_NAME} =====")

    # start client main
    main()
