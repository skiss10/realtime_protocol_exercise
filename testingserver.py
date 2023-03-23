import socket
import threading
import time
from utils.exception_handler import exception_handler


@exception_handler
def handle_client(conn, addr):
    print(f"Connected by {addr}")
    while True:
        data = conn.recv(1024)
        if not data:
            break
        print(f"Received data from {addr}: {data.decode('utf-8')}")

@exception_handler
def send_heartbeat(conn,addr):
    while True:
        conn.send(b"Heartbeat")
        print(f"Sent Heartbeat to {addr} at {time.time()}")
        time.sleep(5)

@exception_handler
def main():
    HOST = 'localhost'  # Symbolic name meaning all available interfaces
    PORT = 12331  # Arbitrary non-privileged port

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(5)
        print("Server listening on port", PORT)
        processes = []
        while True:
            conn, addr = s.accept()
            # handle each client in a separate thread
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()

            # spawn a new process to send heartbeats to the client
            heartbeat_thread = threading.Thread(target=send_heartbeat, args=(conn,addr))
            heartbeat_thread.start()
            

if __name__ == "__main__":
    main()