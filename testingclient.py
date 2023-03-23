import socket
import threading
import time
import sys

from utils.exception_handler import exception_handler

@exception_handler
def receive_message(conn):
    while True:
        data = conn.recv(1024)
        if data.decode('utf-8') == "Heartbeat":
            print(f"Received heartbeat at {time.time()}")
            conn.send(b"Heartbeat_ack")

@exception_handler
def send_message(conn):
    while True:
        message = input("Enter message to send: ")
        conn.send(message.encode('utf-8'))

@exception_handler
def disconnect(conn, host, port):

    time_until_disconnect = None if len(sys.argv) < 2 else int(sys.argv[1])
    disconnect_duration = None if len(sys.argv) < 2 else int(sys.argv[2])

    if time_until_disconnect is not None:
        time.sleep(time_until_disconnect)
        conn.close()
        time.sleep(disconnect_duration)
        server_handler(host, port, False)
    else:
        pass

def server_handler(host, port, sim_discconect = True):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            print("Connected to server")

            # spawn a new thread to receive heartbeats from the server
            heartbeat_thread = threading.Thread(target=receive_message, args=(s,))
            heartbeat_thread.start()

            # spawn a new thread to send messages to the server
            message_thread = threading.Thread(target=send_message, args=(s,))
            message_thread.start()

            if sim_discconect:
                # spawn a new thread to disconnect from to the server
                disconnect_thread = threading.Thread(target=disconnect, args=(s, host, port))
                disconnect_thread.start()
                disconnect_thread.join()

            heartbeat_thread.join()
            message_thread.join()

@exception_handler
def main():
    HOST = 'localhost'  # The server's hostname or IP address
    PORT = 12331  # The port used by the server

    server_handler(HOST, PORT)

if __name__ == "__main__":
    main()