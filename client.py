import socket
import sys
import uuid
import random
import logging
import constants

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

# create a socket object
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# connect to the server
logging.debug("Client - attempting to connect to server")
host_ip = 'localhost'
client_socket.connect((host_ip, port))

# send a message to the server
logging.debug("Client - sending initial payload to server")
client_socket.sendall("{} {}".format(client_id, n).encode())

# close the connection
logging.debug("Client - closing connection")
client_socket.close()
