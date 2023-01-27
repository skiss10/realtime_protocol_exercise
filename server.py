import socket
import sys
import logging
import struct
import hashlib
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

def start_server(port):
    """
    This function initates the socket server
    """
    # create a socket object
    tcpsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # bind the socket to a specific address and port
    tcpsocket.bind(('localhost', port))

    # listen for incoming connections
    tcpsocket.listen(1)
    logging.debug("Listening on localhost:{%s} ...", port)

    while True:
        # establish a connection
        conn, addr = tcpsocket.accept()

        # receive data from the client
        data = conn.recv(1024) #write test for data format (num bytes and format)
        logging.debug("Server - data recieved: %s", data)

        # make incrementing uint34 list of messages
        sequence_length = int(data.decode().split(" ")[1])
        uint32_numbers = [struct.pack('>I', num) for num in range(1, sequence_length+1)]
        logging.debug("Server - list of uint32 numbers: %s", uint32_numbers)

        # get the hexadecimal representation of the md5 hash
        checksum = calculate_checksum(uint32_numbers)

        # send a message to the server
        logging.debug("Server - sending checksum payload to client")
        conn.sendall("{}".format(checksum).encode())

        # close the connection
        logging.debug("Server - closing connection")
        conn.close()
        logging.debug("Server - connection closed")

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
    start_server(port)

if __name__ == '__main__':
    main()
