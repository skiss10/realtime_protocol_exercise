import socket
import sys
import logging
import constants

# Configure logging
logging.basicConfig(level=constants.LOG_LEVEL, filename=constants.LOG_FILE_PATH,format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%m-%d %H:%M:%S')
logging.debug("===== Server - starting server.py =====")

# get the port number from command line
port = int(sys.argv[1])

# create a socket object
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# bind the socket to a specific address and port
s.bind(('localhost', port))

# listen for incoming connections
s.listen(1)

print(f"Listening on localhost:{port}...")

while True:
    # establish a connection
    conn, addr = s.accept()
    print(f"Connected by {addr}")

    # receive data from the client
    data = conn.recv(1024)
    logging.debug("Server - data recieved: %s" % data)

    # # send data back to the client
    # conn.sendall(data)

    # close the connection
    logging.debug("Server - closing connection")
    conn.close()
    logging.debug("Server - connection closed")


