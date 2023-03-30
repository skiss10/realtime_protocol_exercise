import socket
import threading

from utils.connection import Connection

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

def message_router(client_connection, server_connection):
    """
    Function to route messages accordingly
    """

    # start separate threads to handle inbound and outbound message routing for each socket
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

    # set up proxy server
    try:
        proxy_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        proxy_server_address = ('localhost', 12332)
        proxy_server_socket.bind(proxy_server_address)
        proxy_server_socket.listen(5)
        print(f'Proxy Server started on {proxy_server_address[0]}:{proxy_server_address[1]}')

        # connect to the real server
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address= ('localhost', 12331)
        server_socket.connect(server_address)
        print(f'Conected to server {server_address[0]}:{server_address[1]}')

        # create server connection object
        server_connection = Connection(server_socket)
        server_connection.addr = server_address
        server_connection.connection_thread_stopper = threading.Event()
        server_connection.id = "SERVER_CONNECTION_FROM_PROXY"

        # create list of connections and add server connection in there.
        connection_list = [server_connection]

        # listen for new client connections
        while True:

            # assign variable to new socket connections
            client_socket, client_address = proxy_server_socket.accept()
            print(f'Client connected: {client_address[0]}:{client_address[1]}')

            # create client_connection object
            client_connection = Connection(server_socket)
            client_connection.conn = client_socket
            client_connection.addr = client_address
            client_connection.connection_thread_stopper = threading.Event()
            client_connection.id = "A_CLIENT_CONNECTION_FROM_PROXY"

            # add client connection object to connection list
            connection_list.append(client_connection)

            # start thread to route messages from client socket to server socket
            message_router_thread = threading.Thread(target=message_router, args=(client_connection, server_connection))
            message_router_thread.start()

    except OSError as error:
        if error.errno == 48:
            print("Address for server is in use or not available. Please check server is running or wait a few more seconds")

    except KeyboardInterrupt:
        print("Server stopped listening for new connections")

        # check for connections
        if len(connection_list) >= 1:

            # close sockets and stop threads for each connection
            for connection_object in connection_list:
                end_connection(connection_object)
                print("All connection sockets closed and threads stopped for connect %s" , connection_object.id)


if __name__ == '__main__':
    main()