"""
Socket server

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
import struct
import random
import bisect

from utils.connection import Connection
from utils.session_store import InMemoryStore, RedisStore
from utils.message_sender import send_message
from utils.checksum import calculate_checksum
from constants import HEARTBEAT_INTERVAL, LOG_LEVEL, LOG_FILE_PATH, RECONNECT_WINDOW, SERVER_DEFAULT_PORT

# pylint: disable=logging-fstring-interpolation
# pylint: disable=f-string-without-interpolation

# create a unique server name
SERVER_NAME = str(uuid.uuid4())

# define server interface with memory store
SESSION_STORAGE = InMemoryStore()

# define server interface with Redis
REDIS_STORAGE = RedisStore()

def redis_set_store(redis_store, client_id, connection_id, sequence, TTL=30):
    """
    Function to set the redis store with a TTL of 30 seconds
    """

    redis_store.set(f'client_session_state:{client_id}:{connection_id}', pickle.dumps(sequence))
    redis_store.redis_client.expire(f'client_session_state:{client_id}:{connection_id}', TTL)

def generate_prng_sequence(sequence_length):
    """
    Function to generate pseudo-random numbers
    """

    # initialize the random number generator with a random seed
    random.seed()

    # create sequence
    sequence = [random.randint(0, 2**32-1) for _ in range(sequence_length)]

    # convert each number to bytes (big-endian)
    return [struct.pack('>I', num) for num in sequence]

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
            print(f"system - conn id {connection.id} to client {connection.client_id} is closed")
            logging.info(f" system - conn id {connection.id} to client {connection.client_id} is closed")

    # handle OSError closing connection's socket
    except OSError as error:

        # log error
        print(f"system - err {error} conn id {connection.id} when closing sockets")
        logging.error(f"system - err {error} conn id {connection.id} when closing sockets")

def send_checksum(connection):
    """
    Function to send checksum to client
    """

    # calculate checksum
    checksum = calculate_checksum(connection.sent_uint32_numbers)

    # send checksum number
    send_message(connection.conn, "Checksum", checksum, SERVER_NAME)

    # log checksum
    print(f"checksum - sent checksum: {checksum} to client {connection.client_id}")
    logging.info(f" checksum - sent checksum: {checksum} to client {connection.client_id}")

def greeting_message_handler(connection, message):
    """
    Function to handle client greeting message
    """

    try:

        # assign client_id for connection
        connection.client_id = message.sender_id
        logging.debug(f"connection - conn id {connection.id} goes to client {connection.client_id}")

        # set sequence length
        connection.sequence_length = message.data
        logging.debug(f"connection - conn id {connection.id} to client {connection.client_id} has sequence length {connection.sequence_length}")

        # generate uint32 numbers to be sent over connection
        connection.all_uint32_numbers = generate_prng_sequence(connection.sequence_length)

        # set connection state
        connection.state = "initial_connection"
        logging.debug(f"connection - conn id {connection.id} has state {connection.state}")

        # send greeting ack response with connection id inclueded
        send_message(connection.conn, "Greeting_ack", connection.id, SERVER_NAME)
        logging.info(f" message - sent greeting_ack over conn id {connection.id} to client {connection.client_id}")

        # update redis connection store
        redis_set_store(REDIS_STORAGE, connection.client_id, connection.id, connection.all_uint32_numbers)

    except OSError as error:

        # log error handling greeting
        print(f"system - error {error} sending greeting_ack over connection {connection.id} to {connection.client_id}")
        logging.error(f"system - error {error} sending greeting_ack over connection {connection.id} to {connection.client_id}")

def reconnection_attempt_message_handler(connection, message):
    """
    Function to handle reconnections from the client
    """

    # assign client_id for connection
    connection.client_id = message.sender_id

    # log updated client_id
    print(f"reconnection - recieved reconnection attempt from client {connection.client_id} over connection_id {connection.id}")
    logging.info(f" reconnection - recieved reconnection attempt from client {connection.client_id} over connection_id {connection.id}")

    # boolean to see if connection object exists
    connection_id_not_found = True

    # client provided former connection_id
    alleged_connection_id = message.data[0]

    # defint the last uint32 number recieved by client
    last_uint32_num = message.data[1]
    logging.debug(f"reconnection - last reported uint32_number received by client {message.sender_id} was {last_uint32_num}")

    # Loop over connections connections in data store
    for _, stored_connection_object in SESSION_STORAGE.store.items():

        # check if the alleged connection_id from client is stored in SESSION_STORAGE 
        if stored_connection_object.id == alleged_connection_id:

            # log that we found the connection_id provided by the connected peer
            print(f"reconnection - found alleged connection {alleged_connection_id} locally")
            logging.info(f"reconnection - found alleged connection {alleged_connection_id} locally")

            # set boolean as connection id from message found in storage
            connection_id_not_found =  False

            # get current timestamp
            current_time = time.time()

            # see if the last heartbeat ack was recieved within the reconnection window
            if current_time - stored_connection_object.last_heartbeat_ack < RECONNECT_WINDOW:

                # log successful reconnection
                print(f"reconnection - successful reconnection from client {message.sender_id}")
                logging.info(f" reconnection - successful reconnection from client {message.sender_id}")

                # transfer requested numbers from old connection
                connection.all_uint32_numbers = stored_connection_object.all_uint32_numbers

                # get previously sent numbers up to last message num in sequence reported by client
                connection.sent_uint32_numbers =  stored_connection_object.all_uint32_numbers[:stored_connection_object.all_uint32_numbers.index(last_uint32_num) + 1]

                # set queued_uint32_numbers on new connection as list of remaining messages to send
                connection.queued_uint32_numbers = stored_connection_object.all_uint32_numbers[stored_connection_object.all_uint32_numbers.index(last_uint32_num) + 1:]
                logging.debug(f"reconnection - last reported uint32_number received by client {message.sender_id} was {last_uint32_num}")

                # set replacement connection
                stored_connection_object.replacement_connection_id = connection.id

                # update the stored connection object state to recovered
                stored_connection_object.state = 'recovered'

                # set connection cleint_id
                connection.client_id = message.sender_id

                # set connection condition
                connection.state = "reconnected"

                # send reconnection success message
                send_message(connection.conn, "Reconnect_accepted", connection.id, send_message)

                # stop evaluating other connections in local storage
                break

            else:

                # reject reconnection attempt
                send_message(connection.conn, "Reconnect_rejected", "timeout", send_message)

                # log reconnection rejected
                print(f"reconnection - attempt from {message.sender_id} failed from window timed out")
                logging.info(f" reconnection - attempt from {message.sender_id} failed from window timed out")

                # end connection with failed reconnect attempt
                end_connection(connection)

        # else:
            
        #     for key in REDIS_STORAGE.key_list():

        #         if key.split(':')[1] == alleged_connection_id:

        #                 # log successful reconnection
        #                 print(f"reconnection - successful reconnection from client {message.sender_id}")
        #                 logging.info(f" reconnection - successful reconnection from client {message.sender_id}")

        #                 # transfer requested numbers from old connection
        #                 connection.all_uint32_numbers = REDIS_STORAGE.get(key)

        #                 # bisect all_uint32_numbers by last_uint32_num
        #                 index = bisect.bisect_left(connection.all_uint32_numbers, last_uint32_num)

        #                 # Get the sequence of numbers before last_uint32_num
        #                 connection.sent_uint32_numbers = connection.all_uint32_numbers[:index]

        #                 # Get the numbers to be sent after last_uint32_num, including last_uint32_num
        #                 connection.queued_uint32_numbers = connection.all_uint32_numbers[index:]

        #                 # set connection cleint_id
        #                 connection.client_id = message.sender_id

        #                 # set connection condition
        #                 connection.state = "reconnected"

        #                 # update connection id to old id
        #                 connection.id = alleged_connection_id

        #                 # send reconnection success message
        #                 send_message(connection.conn, "Reconnect_accepted", connection.id, send_message)

    if connection_id_not_found:

        # reject reconnection attempt
        send_message(connection.conn, "Reconnect_rejected", "no_recorded_state", send_message)

        # log reconnection rejected
        print(f"reconnection - attempt from {message.sender_id} failed, no record of the provided connection_id")
        logging.info(f" reconnection - attempt from {message.sender_id} failed, no record of the provided connection_id")

        # end connection with failed reconnect attempt
        end_connection(connection)

def heartbeat_ack_message_handler(connection):
    """
    Function to handle heartbeat ack messages from client
    """

    try:
        # aquire lock to update shared last_heartbeat_ack variable in other threads
        with connection.threading_lock:

            # update last heartbeat ack timestamp
            connection.last_heartbeat_ack = time.time()
            
            # update redis connection store
            redis_set_store(REDIS_STORAGE, connection.client_id, connection.id, connection.all_uint32_numbers)

            # log heartbeat ack update
            logging.debug(f"heartbeat - updated heartbeat_ack timestamp on conn id {connection.id}")

    except OSError as err:

        # log error
        print(f"heartbeat - error {err} updating heartbeat_ack timestamp for conn id {connection.id}")
        logging.error(f"heartbeat - error {err} updating heartbeat_ack timestamp for conn id {connection.id}")

def checksum_ack_message_handler(connection, message):
    """
    Function to handle checksum_ack messages from client
    """
    
    if message.data == "success":

        # log sequence sent success
        print(f"system - SUCCESS! client checksum and server checksum are equal")
        logging.info(f" system - SUCCESS! client checksum and server checksum are equal")

    else:
        # log sequence sent failed
        print(f"system - FAILED! client checksum and server checksum are not equal")
        logging.info(f"system - FAILED! client checksum and server checksum are not equal")

    # set connection state to completed
    connection.is_complete = True

    # log connection state sent to completed
    print(f"connection - connection id {connection.id} to client {connection.client_id} set to state {connection.state}")
    logging.info(f" connection - connection id {connection.id} to client {connection.client_id} set to state {connection.state}")

    # end the connection after sending checksum
    end_connection(connection)

def inbound_message_handler(connection):
    """
    Handler for all messages inbound to the client.
    """

    # continuous loop contingent on status of connection's threads
    while not connection.connection_thread_stopper.is_set():

        # retrieve inbound data from client
        try:

            # listen for messages over connection
            serialized_message = connection.conn.recv(1024)

            # unserialize data from socket
            message = pickle.loads(serialized_message)

            # log new message recieved
            print(f"message - conn id {connection.id} to client {message.sender_id} recieved message type {message.name} with payload: {message.data}")
            logging.info(f" message - conn id {connection.id} to client {message.sender_id} recieved message type {message.name} with payload: {message.data}")

            # check if the messages is a heartbeat_ack
            if message.name == "Heartbeat_ack":
                heartbeat_ack_message_handler(connection)

            # check if the messages is a greeing
            if message.name == "Greeting":
                greeting_message_handler(connection, message)

            # check if the messages is a reconnect
            if message.name == "reconnect_attempt":
                reconnection_attempt_message_handler(connection, message)

            # check if the messages is a checksum_ack
            if message.name == "checksum_ack":
                checksum_ack_message_handler(connection, message)

        # handle socket read errors
        except OSError as error:

            # log error
            print(f"system - error {error} on conn id {connection.id} to client {connection.client_id}")
            print(f"system - stopping inbound_message_handler for {connection.id}")
            logging.error(f"system - error {error} on conn id {connection.id} to client {connection.client_id}")
            logging.error(f"system - stopping inbound_message_handler for {connection.id}")

            # stop / suspend inbound_message_handler
            break

        # handle corrupted inbound data from peer. This is not a realistic failure scenario for an Ably client so will break loop
        except EOFError as error:

            # log error
            print(f"system - error {error} received corrupted on {connection.id} from client {connection.client_id}. Peer likely closed connection.")
            print(f"system - suspending inbound_message_handler for {connection.id}")
            logging.error(f"system - error {error} received corrupted on {connection.id} from client {connection.client_id}. Peer likely closed connection.")
            logging.error(f"system - suspending inbound_message_handler for {connection.id}")
            
            # stop / suspend inbound_message_handler
            break

def check_heartbeat_ack(connection):
    """
    Function to ensure heartbeats are being recieved from client
    """

    # continuous loop contingent on status of connection's threads
    while not connection.connection_thread_stopper.is_set():

        # get current timestamp
        current_time = time.time()

        try:

            # check for three missed heartbeats
            if current_time - connection.last_heartbeat_ack > HEARTBEAT_INTERVAL * 3:

                # log heartbeat_acks missing
                print(f"heartbeat - conn id {connection.id} to client {connection.client_id} not recieving heartbeat_acks")
                print(f"system - disconnecting client {connection.client_id}")
                logging.info(f" heartbeat - conn id {connection.id} to client {connection.client_id} not recieving heartbeat_acks")
                logging.info(f" system - disconnecting client {connection.client_id}")
                
                # stop threads and close socket
                end_connection(connection)

                # stop / suspend check_heartbeat_ack
                break

        except OSError as error:
            print(f"heartbeat - error {error} in check_heartbeat_ack")
            print(f"system - conn id {connection.id} stopping check_heartbeat_ack")
            logging.error(f"heartbeat - error {error} in check_heartbeat_ack")
            logging.error(f"system - conn id {connection.id} stopping check_heartbeat_ack")
            

        # sleep thread checking for heartbeat_acks
        time.sleep(1)

def send_sequence(connection):
    """
    Function to generate messages to peer
    """

    # continuous loop contingent on status of connection's threads
    while not connection.connection_thread_stopper.is_set():

        # check connection state before sending / continuing data stream
        if connection.state == "initial_connection":

            # log sequence start
            print(f"sequence - started sending sequence to client {connection.client_id}")
            logging.info(f" sequence - started sending sequence to client {connection.client_id}")

            try:

                # loop over all numbers we need to send
                for num in connection.all_uint32_numbers:

                    # send next number in 1 second
                    time.sleep(1)

                    # send uint32 number
                    send_message(connection.conn, "Data", num, SERVER_NAME)

                    # log message sent
                    print(f"sequence - sent {num} to client {connection.client_id}")
                    logging.info(f" sequence - sent {num} to client {connection.client_id}")

                    # update sent numbers over this connection
                    connection.sent_uint32_numbers.append(num)

            except OSError:

                # log error
                print("system - Unable to send messages over the socket")
                print(f"system - suspending generate_message")
                logging.error(f"system - Unable to send messages over the socket")
                logging.error(f"system - suspending generate_message")

                # suspending generate_message thread / function
                break
            
            # send checksum 
            send_checksum(connection)

        elif connection.state == "reconnected":

            # log sequence restrt
            print(f"sequence - continuing sequence to client {connection.client_id} over connection id {connection.id}")
            logging.info(f" sequence - continuing sequence to client {connection.client_id} over connection id {connection.id}")

            # try sending user input messages to peer
            try:

                # loop over numbers queued to send
                for num in connection.queued_uint32_numbers:

                    # send next number in 1 second
                    time.sleep(1)

                    # send next uint32 number
                    send_message(connection.conn, "Data", num, SERVER_NAME)

                    # log message sent
                    print(f"sequence - sent {num} to client {connection.client_id}")
                    logging.info(f" sequence - sent {num} to client {connection.client_id}")

                    # add recently sent uint32 number to sent_uint32_numbers for connection
                    connection.sent_uint32_numbers.append(num)

            except OSError:

                # log error
                print("system - Unable to send messages over the socket")
                print(f"system - suspending generate_message")
                logging.error(f"system - Unable to send messages over the socket")
                logging.error(f"system - suspending generate_message")

                # suspending generate_message thread / function
                break

            # send checksum
            send_checksum(connection)

def send_heartbeat(connection):
    """
    Function to continously send heartbeats from the server
    to the client
    """

    # continuous loop contingent on status of connection's threads
    while not connection.connection_thread_stopper.is_set():

        # check session state before sending heartbeats
        if connection.state in ['initial_connection', 'reconnected']:
            time.sleep(HEARTBEAT_INTERVAL)

            # send heartbeats
            try:

                # send heartbeat
                send_message(connection.conn, "Heartbeat" , "", SERVER_NAME)

                # log sending heartbeat
                print(f"heartbeat - sent heartbeat over conn id {connection.id} to client {connection.client_id}")
                logging.info(f" heartbeat - sent heartbeat over conn id {connection.id} to client {connection.client_id}")

            # handle issue sending outbound data to peer. This is not a realistic failure scenario for an Ably client so will break loop / thread
            except OSError as error:

                # log error
                print(f"heartbeat - error {error} in send_heartbeat")
                print(f"system - conn id {connection.id} stopping send_heartbeat")
                logging.error(f"heartbeat - error {error} in send_heartbeat")
                logging.error(f"system - conn id {connection.id} stopping send_heartbeat")

                # stop / suspend send_heartbeat
                break

def client_handler(connection):
    """
    Handler function for all inbound clients
    """

    # spawn a new thread to handle inbound messages from client
    inbound_messages_thread = threading.Thread(target=inbound_message_handler, args=(connection,))
    inbound_messages_thread.start()

    # log starting thread
    logging.debug(f"system - conn id {connection.id} started inbound_message_handler")

    # spawn a new thread to monitor heartbeats_acks from the client
    heartbeat_ack_thread = threading.Thread(target=check_heartbeat_ack, args=(connection,))
    heartbeat_ack_thread.start()

    # log starting thread
    logging.debug(f"system - conn id {connection.id} started check_heartbeat_ack")

    # spawn a new thread to send messages to the peer
    send_sequence_thread = threading.Thread(target=send_sequence, args=(connection,))
    send_sequence_thread.start()

    # log starting thread
    logging.debug(f"system - conn id {connection.id} started send_sequence")

    # spawn a new thread to send heartbeats to the client
    heartbeat_thread = threading.Thread(target=send_heartbeat, args=(connection,))
    heartbeat_thread.start()

    # log starting thread
    logging.debug(f"system - conn id {connection.id} started send_heartbeat")

def manage_session_store():
    """
    Function to keep session storage up to date based on each connection's
    attributes.
    """

    counter = 0

    # log starting check_session_store
    print("storage - check_session_store started")
    logging.info(f" storage - check_session_store started")

    # Continuous loop while server running checking session store
    while True:

        counter += 1

        # get current timestamp
        current_time = time.time()

        # define active connections
        local_connections = SESSION_STORAGE.store.items()

        # print(f"storage - local connections are {local_connections} for {counter}")
        logging.debug(f"storage - local connections are {local_connections} for {counter}")

        # create list for stale connections
        connection_to_remove = []

        # loop over connection objects in session store
        for _, connection_object in local_connections:

            # check if connection has already sent sequence and is ready to be removed from session store
            if connection_object.is_complete:
                
                # add connection to list for removal
                connection_to_remove.append(connection_object)

                # log connection finished
                print(f"storage - adding {connection_object.id} to connection removal list, as connection state marked as completed")
                logging.info(f" storage - adding {connection_object.id} to connection removal list, as connection state marked as completed")

                # remove connection id from redis
                REDIS_STORAGE.delete(f'client_session_state:{connection_object.client_id}:{connection_object.id}')

                # log connection removed from redis
                print(f"storage - removed connection {connection_object.id} from redis")
                logging.info(f" storage - removed connection {connection_object.id} from redis")

            # check if connection has already sent sequence and is ready to be removed from session store
            elif connection_object.state == "recovered":
                
                # add connection to list for removal
                connection_to_remove.append(connection_object)

                # log connection finished
                print(f"storage - adding {connection_object.id} to connection removal list, as connection state marked as recovered")
                logging.info(f" storage - adding {connection_object.id} to connection removal list, as connection state marked as recovered")

                # remove former stored_connection_object id from redis
                REDIS_STORAGE.delete(f'client_session_state:{connection_object.client_id}:{connection_object.id}')

                # add updated connection id info to redis
                redis_set_store(REDIS_STORAGE, connection_object.client_id, connection_object.replacement_connection_id, connection_object.all_uint32_numbers)

                # log redis updates
                print(f"reconnection - updated client-connection key in redis for this sequence from connection id {connection_object.id} to {connection_object.replacement_connection_id}")
                logging.info(f" reconnection - updated client-connection key in redis for this sequence from connection id {connection_object.id} to {connection_object.replacement_connection_id}")

            # check heartbeats for stale connection entries
            elif current_time - connection_object.last_heartbeat_ack > RECONNECT_WINDOW:
                
                # add stale connections to list for removal if missing heartbeat acks
                connection_to_remove.append(connection_object)

                # log new stale connection
                print(f"storage - adding {connection_object.id} to connection removal list, no new heartbeats_acks over that connection's socket within RECONNECT_WINDOW")
                logging.info(f" storage - adding {connection_object.id} to connection removal list, no new heartbeats_acks over that connection's socket within RECONNECT_WINDOW")

        # loop over stale connection
        for connection_object in connection_to_remove:

            # remove the connection from session storage
            SESSION_STORAGE.delete(connection_object.id)

            # log removal of connection from session storage
            print(f"storage - removed connection {connection_object.id} from session_store")
            logging.info(f" storage - removed connection {connection_object.id} from session_store")

        # print(f"storage - local connections are {local_connections} for {counter}")
        logging.debug(f"storage - local connections are {local_connections} for {counter}")
        
        # sleep thread checking for stale connections
        time.sleep(1)

def main():
    """
    main function for server
    """

    # define server address
    host = '127.0.0.1'

    # set default port (server port)
    port = SERVER_DEFAULT_PORT

    # handle optional input paramater for port
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    # start thread to manage server session storage
    check_session_store_thread = threading.Thread(target=manage_session_store, args=())
    check_session_store_thread.start()

    # log starting server session storage
    logging.debug(f"storage - started check_session_store_thread")

    # create server socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

        # start server
        try:
            # Inform OS to allow socket to use a given local address even if its in use by another program
            # s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            s.listen(5)

            # log starting server
            print(f"system - listening on localhost:{port} ...")
            logging.info(f" system - listening on localhost:{port} ...")
        
        except OSError:

            # log error
            print(f"system - socket port has not been closed by OS yet. port: {port}")
            logging.error(f"system - socket port has not been closed by OS yet. port: {port}")

        # handle inbound connection attempts
        try:

            # listen for new connections
            while True:
                conn, addr = s.accept()

                # log new connection
                print(f"system - recieved connection on:{addr} ...")
                logging.info(f" system - recieved connection on:{addr} ...")

                # instantiate new connection object
                connection = Connection(conn, addr)

                # log new connection object
                logging.debug(f"system - assigned conn id {connection.id} to connection over {addr}")

                # add new connection to connections list
                SESSION_STORAGE.set(connection.id, connection)

                # handle each client in a separate thread
                client_thread = threading.Thread(target=client_handler, args=(connection,))
                client_thread.start()

                # log starting new client_handler thread
                logging.debug(f"system - started client_handler thread for conn id {connection.id} ...")

        except KeyboardInterrupt:

            # log keyboard interrupt
            print(f"system - stopped due to keyboard interrupt")
            logging.info(f" system - stopped due to keyboard interrupt")

            # check for connections
            if len(SESSION_STORAGE.store) >= 1:

                # close all sockets and stop threads for each connection
                for _, connection_object in SESSION_STORAGE.store.items():

                    # end connection
                    end_connection(connection_object)

        except OSError as error:

            # operating system is preventing the socket from accepting connections.
            if error.errno == 22:

                # log error
                print(f"system - OS is preventing the socket from accepting new connections.")
                logging.error(f"system - OS is preventing the socket from accepting new connections.")

                # close program
                sys.exit()

if __name__ == "__main__":

    # Configure logging
    logging.basicConfig(
    level=LOG_LEVEL,
    filename=LOG_FILE_PATH,
    format=f'[%(asctime)s] - Server - {SERVER_NAME} - %(levelname)s - %(message)s',
    datefmt='%m-%d %H:%M:%S')

    # log server starting
    print("===== Server - starting %s =====", SERVER_NAME)
    logging.info("===== Server - starting %s =====", SERVER_NAME)

    # start server
    main()
