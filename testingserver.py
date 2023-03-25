import socket
import threading
import time
import uuid
import pickle

from utils.message_sender import send_message

SERVER_NAME = str(uuid.uuid4())

def handle_client(conn, addr):
    print(f"Connected by {addr}")
    while True:
        data = conn.recv(1024)
        if not data:
            break
        unserialized_data = pickle.loads(data)
        print(f"Received message type {unserialized_data.name} from {addr} with data: {unserialized_data.data} ")

def send_heartbeat(conn,addr):
    while True:
        try:
            send_message(conn, "Heartbeat" , "", SERVER_NAME)
            print(f"Sent Heartbeat to {addr} at {time.time()}")
            time.sleep(5)
        except OSError:
            print("Socket Broken. Closing Connection")
            conn.close()
            break

def main():
    HOST = 'localhost'  # Symbolic name meaning all available interfaces
    PORT = 12331  # Arbitrary non-privileged port

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(5)
        print("Server listening on port", PORT)

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