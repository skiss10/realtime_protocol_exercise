import socket
import threading
import time

def receive_message(conn):
    while True:
        data = conn.recv(1024)
        if data.decode('utf-8') == "Heartbeat":
            print(f"Received heartbeat at {time.time()}")
            conn.send(b"Heartbeat_ack")


def send_message(conn):
    while True:
        message = input("Enter message to send: ")
        conn.send(message.encode('utf-8'))

if __name__ == "__main__":
    HOST = 'localhost'  # The server's hostname or IP address
    PORT = 12331  # The port used by the server

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print("Connected to server")

        # spawn a new thread to receive heartbeats from the server
        heartbeat_thread = threading.Thread(target=receive_message, args=(s,))
        heartbeat_thread.start()

        # spawn a new thread to send messages to the server
        message_thread = threading.Thread(target=send_message, args=(s,))
        message_thread.start()

        heartbeat_thread.join()
        message_thread.join()