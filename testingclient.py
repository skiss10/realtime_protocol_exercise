import socket
import threading
import time
import sys

from utils.exception_handler import exception_handler

LAST_HEARTBEAT = time.time()

def receive_message(conn, host, port, stop_threads):
    lock = threading.Lock()
    heartbeat_thread = threading.Thread(target=receive_heartbeat, args=(conn, lock, stop_threads,))
    disconnect_thread = threading.Thread(target=check_heartbeat, args=(conn, lock, host, port, stop_threads,))
    heartbeat_thread.start()
    disconnect_thread.start()
    heartbeat_thread.join()
    disconnect_thread.join()


def receive_heartbeat(conn, lock, stop_threads):
    global LAST_HEARTBEAT
    while not stop_threads.is_set():
        try:
            data = conn.recv(1024)
            if data.decode('utf-8') == "Heartbeat":
                print(f"Received heartbeat at {time.time()}")
                conn.send(b"Heartbeat_ack")
                with lock:
                    LAST_HEARTBEAT = time.time()
        except OSError:
            print("Error reading from Socket")
    print("recieved heartbeats stopped")

def attempt_reconnection(host,port):
    try:
        server_handler(host, port)
    except OSError:
        print("unable to reconnect to server, trying again in 10 seconds...")
        time.sleep(10)
        attempt_reconnection(host,port)

def check_heartbeat(conn, lock, host, port, stop_threads):
    global LAST_HEARTBEAT
    disconnect_flag = False
    while True:
        if disconnect_flag:
            conn.close()
            stop_threads.set()
            attempt_reconnection(host,port)
            break
        with lock:
            current_time = time.time()
            if current_time - LAST_HEARTBEAT > 15:
                print("Heartbeat not received within 15 seconds. Disconnecting...")
                disconnect_flag = True
        time.sleep(1)

def send_message(conn, stop_threads):
    conn.send(b"Greetings from the client!")
    print("Begin typing your messages to the server!")
    while not stop_threads.is_set():
        try:
            message = input("Enter message to send: ")
            conn.send(message.encode('utf-8'))
        except OSError:
            print("Unable to send messages over the socket")
    print('Message Sender Stopped')

def server_handler(host, port):
        stop_threads = threading.Event()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            print("Connected to server")

            # spawn a new thread to receive heartbeats from the server
            heartbeat_thread = threading.Thread(target=receive_message, args=(s,host,port,stop_threads,))
            heartbeat_thread.start()

            # spawn a new thread to send messages to the server
            message_thread = threading.Thread(target=send_message, args=(s,stop_threads,))
            message_thread.start()

            heartbeat_thread.join()
            message_thread.join()

def main():
    HOST = 'localhost'  # The server's hostname or IP address
    PORT = 12331  # The port used by the server

    try:
        server_handler(HOST, PORT)
    except OSError:
        print("Unable to connect to server.")

if __name__ == "__main__":
    main()