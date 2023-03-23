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
def disconnect(conn, time_until_disconnect, disconnect_duration, host, port):
    if time_until_disconnect is not None:
        time.sleep(time_until_disconnect)
        conn.close()
        time.sleep(disconnect_duration)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            print("reconnecting to server")

            s.send("reconnect_message".encode('utf-8'))

            # spawn a new thread to receive heartbeats from the server
            heartbeat_thread = threading.Thread(target=receive_message, args=(s,))
            heartbeat_thread.start()

            # spawn a new thread to send messages to the server
            message_thread = threading.Thread(target=send_message, args=(s,))
            message_thread.start()

            heartbeat_thread.join()
            message_thread.join()

    else:
        pass

@exception_handler
def main():
    HOST = 'localhost'  # The server's hostname or IP address
    PORT = 12331  # The port used by the server
    SECONDS_UNTIL_DISCONNECT = None if len(sys.argv) < 2 else int(sys.argv[1])
    SECONDS_OF_DISCONNECT = None if len(sys.argv) < 2 else int(sys.argv[2])

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print("Connected to server")

        # spawn a new thread to receive heartbeats from the server
        heartbeat_thread = threading.Thread(target=receive_message, args=(s,))
        heartbeat_thread.start()

        # spawn a new thread to send messages to the server
        message_thread = threading.Thread(target=send_message, args=(s,))
        message_thread.start()

        # spawn a new thread to send messages to the server
        disconnect_thread = threading.Thread(target=disconnect, args=(s,SECONDS_UNTIL_DISCONNECT,SECONDS_OF_DISCONNECT, HOST, PORT))
        disconnect_thread.start()

        heartbeat_thread.join()
        message_thread.join()
        disconnect_thread.join()

if __name__ == "__main__":
    main()