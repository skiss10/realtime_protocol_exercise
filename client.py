import socket
import sys
import uuid
import random
import logging
import constants

def connect_to_server(host_ip, port, client_id, n):
    # create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # connect to the server
    logging.debug("Client - attempting to connect to server")
    client_socket.connect((host_ip, port))

    # send a message to the server
    logging.debug("Client - sending initial payload to server")
    client_socket.sendall("{} {}".format(client_id, n).encode())

    return client_socket

def main():
    # Configure logging
    logging.basicConfig(
        level=constants.LOG_LEVEL,
        filename=constants.LOG_FILE_PATH,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%m-%d %H:%M:%S'
        )
    logging.debug("===== Client - starting client.py =====")

    # get the port number and number of messages from command line
    port = int(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else random.randint(1, 0xffff)

    # generate a random uuid client identifier
    client_id = str(uuid.uuid4())

    # define server ip
    host_ip = 'localhost'

    # connect to server
    client_socket = connect_to_server(host_ip, port, client_id, n)

    while True:
        # receive data from the client
        data = client_socket.recv(1024) #write test for data recieved from server format

        logging.debug("Client - data recieved: %s", data)

        # # close the connection
        # logging.debug("Client - closing connection")
        # client_socket.close()

if __name__ == '__main__':
    main()