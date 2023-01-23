import socket
import sys
import uuid
import random

# get the port number and number of messages from command line
port = int(sys.argv[1])
n = int(sys.argv[2]) if len(sys.argv) > 2 else random.randint(1, 0xffff)

# generate a random uuid client identifier
client_id = str(uuid.uuid4())

# create a socket object
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# connect to the server
client_socket.connect(('localhost', port))

# send a message to the server
client_socket.sendall("{} {}".format(client_id, n).encode())

# close the connection
client_socket.close()
