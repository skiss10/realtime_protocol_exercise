import socket
import sys
import logging
import struct
import hashlib
from _thread import start_new_thread
import constants

def calculate_checksum(uint32_numbers):
    """
    Input: list of uint32 numbers of arbitrary length

    Output: MD5 checksum
    """
    # concatenate all values in the list
    numbers = "".join(str(i) for i in uint32_numbers)

    # create md5 hash object
    md5 = hashlib.md5()

    # update the hash object with the data
    md5.update(numbers.encode())

    # get the hexadecimal representation of the md5 hash
    checksum = md5.hexdigest()

    # return checksum
    logging.debug("Server - hash of uint32 numbers: %s", checksum)
    return checksum

def client_thread(client_socket, client_address):
    """
    client_thread handles all logic needed on a per
    client basis. 

    Input: client socket and client address
    """
    logging.debug("Server - Connection from: %s", client_address)

    # receive data from the client
    data = client_socket.recv(1024) #write test for data format (num bytes and format)
    logging.debug("Server - data recieved: %s", data)

    # make incrementing uint34 list of messages
    sequence_length = int(data.decode().split(" ")[1])
    uint32_numbers = [struct.pack('>I', num) for num in range(1, sequence_length+1)]
    logging.debug("Server - list of uint32 numbers: %s", uint32_numbers)

    # get the hexadecimal representation of the md5 hash
    checksum = calculate_checksum(uint32_numbers)

    # send a message to the server
    logging.debug("Server - sending checksum payload to client")
    client_socket.sendall("{}".format(checksum).encode())

    # # close the connection
    # logging.debug("Server - closing connection")
    # client_socket.close()
    # logging.debug("Server - connection closed")

def start_server(port):
    """
    This function initates the server socket and sets
    it to listen on the local host at a given port

    Input: port number for local host

    Output: socket object
    """
    # create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # bind the socket to a specific address and port
    server_socket.bind(('localhost', port))

    # listen for incoming connections
    server_socket.listen(1)
    logging.debug("Listening on localhost:{%s} ...", port)

    return server_socket

def main():
    # Configure logging
    logging.basicConfig(
        level=constants.LOG_LEVEL,
        filename=constants.LOG_FILE_PATH,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%m-%d %H:%M:%S'
        )
    logging.debug("===== Server - starting server.py =====")

    # get the port number
    port = int(sys.argv[1])

    # start the server
    server_socket = start_server(port)

    while True:
        # establish a connection
        client_socket, client_address = server_socket.accept()

        # Start a new thread for each client
        start_new_thread(client_thread, (client_socket, client_address))

if __name__ == '__main__':
    main()
