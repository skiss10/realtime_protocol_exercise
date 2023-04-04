"""
Socket client
"""

import socket
import threading
import time
import uuid
import pickle
import logging
import sys
import random

from constants import HEARTBEAT_INTERVAL, LOG_LEVEL, LOG_FILE_PATH
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
            print("threads for connection are flagged to stop")
            logging.info(f" Connection - Threads for connection {connection.id} to server are flagged to stop")

    # handle OSError stopping connection's threads
    except OSError as error:

        print("Error stopping the connection's theads")
        logging.error(f"Connection - Error {error} stopping the theads for {connection.id}")

    # close the connection's socket
    try:

        # check connection state
        if connection.state != "closed":

            # set connection state to closed
            connection.state = "closed"

            # close connection
            connection.conn.close()
            print("socket for connection closed")
            logging.info(f" Connection - Connection {connection.id} stopped")

    # handle OSError closing connection's socket
    except OSError as error:

        # inform user of error hit
        print("Error closing the connections socket")
        logging.error(f"Connection - Error {error} closing socket for {connection.id}")

def handle_greeting_ack(connection, unserialized_message):
    """
    Function to handle incoming messages of type "greeting_ack" from server
    """

    # assign connection id from server to client's connection object
    connection.id = unserialized_message.data

    # inform user
    print("Received Greeting_ack")
    print(f"connection_id from server is {unserialized_message.data}")
    logging.info(f" Message - Recieved Greeting_ack over {connection.id}")
    logging.info(f" Message - Connection_id from server is {unserialized_message.data}")

def handle_heartbeats(connection):
    """
    Function to handle incoming messages of type "heartbeat" from server
    """
    
    print(f"Received heartbeat")
    logging.info(f" Message - Received heartbeat over {connection.id}")

    # send heartbeat_ack back to server
    send_message(connection.conn, "Heartbeat_ack", "Heartbeat_ack", CLIENT_NAME)
    print("Sent Heartbeat_ack")
    logging.info(f" Message - Sent heartbeat_ack over {connection.id}")

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
    print(f"recieved message from server with payload: {uint32_num}")
    logging.info(f" Message - Recieved message from server with payload: {uint32_num}")

def handle_checksum(connection, unserialized_message):
    """
    Function to handle incoming messages of type "checksum" from server
    """

    # gather checksum from server
    server_checksum = unserialized_message.data
    print(f"Server sent checksum {server_checksum}")
    logging.info(f" Checksum - Recieved checksum from server with payload: {server_checksum}")

    # calculate checksum locally
    local_checksum = calculate_checksum(connection.uint32_numbers_recieved)
    logging.info(f" Checksum - Local checksum calculated as: {local_checksum}")
    print(f"Locally calculated checksum is {local_checksum}")

    # determine if checksums are equivalent
    if local_checksum == server_checksum:

        # inform user of successful transfer of uint32 numbers
        print(f"Transfer of uint32 numbers successful!")
        logging.info(f" System - SUCCESS! local checksum and server checksum are equivalent")

    # end connection
    end_connection(connection)

    # close program
    sys.exit()

def handle_reconnect_rejection(connection, unserialized_message):
    """
    Function to handle incoming messages of type "Reconnect_rejected" from server
    """

    # inform user of reconnection failure
    print(f"Reconenction rejected: {unserialized_message.data}")
    logging.info(f" Reconnect - Failed: {unserialized_message.data}")

    # close connection
    end_connection(connection)

def handle_reconnect_accepted(connection, unserialized_message):
    """
    Function to handle incoming messages of type "Reconnect_accepted" from server
    """

    # inform user of reconnection accepted
    print(f"Reconenction accepted. Updated connection.id: {unserialized_message.data}")
    logging.info(f" Reconnect - Accepted. Updated connection.id: {unserialized_message.data}")

    # set new connection id
    connection.id = unserialized_message.data

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
            print(f"Error reading from Socket: {error} - Suspending inbound_message_handler")
            logging.error(f"Message - Error {error} reading message from server. Suspending inbound_message_handler")

            # stop / suspend inbound_message_handler thread
            break

        # trigger error when incomplete message arrives from peer due to disruption / failure
        except EOFError as error:

            # inform user of error when incomplete message arrives from peer due to disruption / failure
            print("Error reading from Socket. Suspending inbound_message_handler")
            logging.error(f"Message - Error {error} reading message from server. Suspending inbound_message_handler")

            # stop / suspend inbound_message_handler thread
            break

def check_heartbeat(connection):
    """
    Function to check heartbeats coming from server
    """

    # continuous loop contingent on status of connection's threads
    while not connection.connection_thread_stopper.is_set():

        # get current time
        current_time = time.time()

        # check how long its been since last heartbeat for this connection
        if current_time - connection.last_heartbeat_ack > 3 * HEARTBEAT_INTERVAL:

            # inform user of missed heartbeats
            print("Heartbeats not recieved from server. Disconnecting from server...")
            logging.info(f" Heartbeats - Heartbeats not recieved from server. Suspending check_heartbeat and Dsconnecting from server")

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
    logging.debug(f"Connection - Started inbound_message_handler thread for connection {connection.id}")

    # spawn a new thread to check incoming heartbeats from server
    check_heartbeat_thread = threading.Thread(target=check_heartbeat, args=(connection,))
    check_heartbeat_thread.start()
    logging.debug(f"Connection - Started check_heartbeat thread for connection {connection.id}")

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
        print("unable to reconnect to server, trying again in 10 seconds...")
        logging.info(f" Reconnect - Unable to reconnect to server, trying again in 10 seconds...")

        # wait 10 seconds
        time.sleep(10)

        # try reconnecting again
        attempt_reconnection(connection)
   
def server_handler(peer_address, former_connection = None):
    """
    Function to connection to a peer socket server
    """

    # create context for new socket object
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:

        # connect to peer address
        try:

            # estabislih connection
            conn.connect(peer_address)
            print(f"Connection to server at {peer_address}")
            logging.info(f" Connection - Connected to Server at {peer_address}")

            # instantiate connection object
            connection = Connection(conn, peer_address)
            
            # set connection object peer address tuple
            connection.addr = peer_address

            # set sequence length / generate sequence lengeth if not explictly set on command line
            connection.sequence_length = int(sys.argv[2]) if len(sys.argv) > 2 else random.randint(1, 0xffff)

            # define variable to stop threads associated with connection
            connection.connection_thread_stopper = threading.Event()

            # check if a previous connection was supplied
            if former_connection is None:

                # send greeting message to peer
                send_message(connection.conn, "Greeting", connection.sequence_length, CLIENT_NAME)
                print("sent greeting message")
                logging.info(f" Message - Sent greeting message to Server at {connection.addr}")

            else:

                # map formerly recieved numbers from previous connection into new connection object
                connection.uint32_numbers_recieved = former_connection.uint32_numbers_recieved

                # send reconnect message to server with previous connection_id and last message recieved by this client
                send_message(connection.conn, "reconnect_attempt", (former_connection.id, former_connection.uint32_numbers_recieved[-1]), CLIENT_NAME)
                print("sent reconnection message")
                logging.info(f" Message - Sent reconnection message to Server at {connection.addr} with info in tuple of {former_connection.id} and {former_connection.uint32_numbers_recieved[-1]}")


            # spawn a new thread to handle inbound messages from the peer
            connection_handler_thread = threading.Thread(target=connection_handler, args=(connection,))
            connection_handler_thread.start()
            connection_handler_thread.join()

            # inform the user connection_handler started
            logging.debug(f"Started connection_handler thread for connection {connection.id}")

        # stop threads and close connection if keyboard interrupt
        except KeyboardInterrupt:

            # stop the connection
            end_connection(connection)

            # inform the user of Keyboard Interrupt
            logging.info(f" System - Stopped due to Keyboard Interrupt")

def main():
    """
    Main function for client
    """

    # define peer location
    host = '127.0.0.1'

    # handle input paramater for port
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
        print("Unable to connect to server. Has the Server and/or proxy server been started?")
        logging.info(f" System - Unable to connect to server. Has the Server and/or proxy server been started?")

if __name__ == "__main__":

    # print client name to console
    print(f"===== Client - starting {CLIENT_NAME} =====")
    logging.info(f" ===== Client - starting {CLIENT_NAME} =====")

    # Configure logging
    logging.basicConfig(
    level=LOG_LEVEL,
    filename=LOG_FILE_PATH,
    format=f'[%(asctime)s] - Client - {CLIENT_NAME} - %(levelname)s - %(message)s',
    datefmt='%m-%d %H:%M:%S')

    # start client main
    main()
