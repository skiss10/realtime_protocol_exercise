import socket
import threading
import time
import sys

from utils.exception_handler import exception_handler

LAST_HEARTBEAT = time.time()

@exception_handler
def receive_message(conn, host, port):
    lock = threading.Lock()
    heartbeat_thread = threading.Thread(target=receive_heartbeat, args=(conn, lock))
    disconnect_thread = threading.Thread(target=check_disconnect, args=(conn, lock, host, port))
    heartbeat_thread.start()
    disconnect_thread.start()
    heartbeat_thread.join()
    disconnect_thread.join()

@exception_handler
def receive_heartbeat(conn, lock):
    global LAST_HEARTBEAT
    while True:
        data = conn.recv(1024)
        if data.decode('utf-8') == "Heartbeat":
            print(f"Received heartbeat at {time.time()}")
            conn.send(b"Heartbeat_ack")
            with lock:
                LAST_HEARTBEAT = time.time()


@exception_handler
def check_disconnect(conn, lock, host, port):
    global LAST_HEARTBEAT
    disconnect_flag = False
    while True:
        if disconnect_flag:
            disconnect(conn, host, port)
            break
        with lock:
            current_time = time.time()
            if current_time - LAST_HEARTBEAT > 15:
                print("Heartbeat not received within 15 seconds. Disconnecting...")
                disconnect_flag = True
        time.sleep(1)

@exception_handler
def send_message(conn):
    while True:
        message = input("Enter message to send: ")
        conn.send(message.encode('utf-8'))

@exception_handler
def disconnect(conn, host, port):
    conn.close()
    server_handler(host, port)

def server_handler(host, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            print("Connected to server")

            # spawn a new thread to receive heartbeats from the server
            heartbeat_thread = threading.Thread(target=receive_message, args=(s,host,port,))
            heartbeat_thread.start()

            # spawn a new thread to send messages to the server
            message_thread = threading.Thread(target=send_message, args=(s,))
            message_thread.start()

            heartbeat_thread.join()
            message_thread.join()

@exception_handler
def main():
    HOST = 'localhost'  # The server's hostname or IP address
    PORT = 12331  # The port used by the server

    server_handler(HOST, PORT)

if __name__ == "__main__":
    main()