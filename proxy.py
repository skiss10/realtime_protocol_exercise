"""
Proxy server to sit between server and clients for
simulated disconnections.

Author: Stephen Kiss (stephenkiss986@gmail.com)
Date: 01/23/2023
"""

import socket
import threading
import sys

from utils.connection import Connection
from constants import SERVER_DEFAULT_PORT, PROXY_DEFAULT_PORT

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

def message_router(connection_pair):
    """
    Function to route messages accordingly
    """

    # decouple pair
    client_connection = connection_pair[0]
    server_connection = connection_pair[1]

    # start separate threads to handle inbound and outbound message routing for each connection in pair
    client_message_router = threading.Thread(target=client_router, args=(client_connection, server_connection))
    server_message_router = threading.Thread(target=server_router, args=(client_connection, server_connection))

    # start threads
    client_message_router.start()
    server_message_router.start()
    
def client_router(client_connection, server_connection):
    """
    Function to route messages from client
    """

    # loop while threads for client connection are active
    while not client_connection.connection_thread_stopper.is_set():
       
        # read socket messages from client socket
        try:
            source_data = client_connection.conn.recv(4096)

        # handle errors for connection reset by client
        except ConnectionResetError:
            print("Connection terminated unexpectedly. Suspending client_router")
            end_connection(client_connection)
            break

        except OSError:
            print("Connection terminated unexpectedly. Suspending client_router")
            end_connection(client_connection)
            break
        
        # send messages from client socket to server socket
        try:
            server_connection.conn.sendall(source_data)

        # handle os errors on socket server
        except OSError:
            print("Issues with Server Socket. Suspending client_router")
            end_connection(server_connection)
            break

def server_router(client_connection, server_connection):
    """
    Function to route messages from server
    """

    # loop while threads for client connection are active
    while not server_connection.connection_thread_stopper.is_set():
       
        # read socket messages from client socket
        try:
            source_data = server_connection.conn.recv(4096)
        
        # handle errors for connection reset by client
        except ConnectionResetError:
            print("Connection terminated unexpectedly. Suspending server_router")
            end_connection(server_connection)
            break

        except OSError:
            print("Connection terminated unexpectedly. Suspending client_router")
            end_connection(server_connection)
            break
        
        # send messages from client socket to server socket
        try:
            client_connection.conn.sendall(source_data)

        # handle os errors on socket server
        except OSError:
            print("Issues with client Socket. Suspending server_router")
            end_connection(client_connection)
            break
        
def main():
    """
    Main function to handle proxy connections
    """

    # set default port (proxy port)
    proxy_port = PROXY_DEFAULT_PORT

    # handle optional input paramater for port
    if len(sys.argv) > 1:
        proxy_port = int(sys.argv[1])

    # set default port (server port)
    server_port = SERVER_DEFAULT_PORT

    # handle optional input paramater for port
    if len(sys.argv) > 2:
        server_port = int(sys.argv[2])

    # create server socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as proxy_server_socket:

        try:

            # Inform OS to allow socket to use a given local address even if its in use by another program
            proxy_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # define the address to use
            proxy_server_address = ('localhost', proxy_port)

            # bind the socket to that address and start listening for connections
            proxy_server_socket.bind(proxy_server_address)
            proxy_server_socket.listen(5)
            print(f'Proxy Server started on {proxy_server_address[0]}:{proxy_server_address[1]}')

            # create a list of tuples representing connection pairs: (client, server)
            connection_pair_list = []

            # create connection counter
            connection_pair_counter = 0
        
        except OSError as error:
            if error.errno == 48:
                print("Hitting interrupt for proxy")
                proxy_server_socket.close()

        try:

            # continuosly listen for new client connections
            while True:

                # assign variable to new socket connections
                client_socket, client_address = proxy_server_socket.accept()
                print(f'Client connected: {client_address[0]}:{client_address[1]}')

                # increment connection counter
                connection_pair_counter += 1

                # Set up another connection to the real server
                server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_address= ('localhost', server_port)
                server_socket.connect(server_address)
                print(f'Conected to server {server_address[0]}:{server_address[1]}')

                # create server connection object
                server_connection = Connection(server_socket, server_address)
                server_connection.addr = server_address
                server_connection.connection_thread_stopper = threading.Event()
                server_connection.id = f"server-{connection_pair_counter}"

                # create client_connection object
                client_connection = Connection(proxy_server_socket, proxy_server_address)
                client_connection.conn = client_socket
                client_connection.addr = client_address
                client_connection.connection_thread_stopper = threading.Event()
                client_connection.id = f"client-{connection_pair_counter}"

                # create connection pair
                connection_pair = (client_connection, server_connection)

                # add client connection object to connection list
                connection_pair_list.append(connection_pair)

                # start thread to route messages from client socket to server socket
                message_router_thread = threading.Thread(target=message_router, args=(connection_pair,))
                message_router_thread.start()

        except OSError as error:
            if error.errno == 48:
                # print("Address for server is in use or not available. Please check server is running or wait a few more seconds")
                print(error)

        except KeyboardInterrupt:
            print("hitting interrupt with new connections")
            print("Server stopped listening for new connections")

            # close and unbind address from socket
            proxy_server_socket.close()

            # check for connection pair
            if len(connection_pair_list) >= 1:

                # close sockets and stop threads for each connection
                for connection_pair in connection_pair_list:
                    end_connection(connection_pair[0])
                    end_connection(connection_pair[1])
                    print(f"All connection sockets closed and threads stopped for {connection_pair[0].id} and {connection_pair[1].id}")

                # close program
                sys.exit()

if __name__ == '__main__':
    main()
