import socket
import threading

def proxy(client_socket, server_socket):

    client_router = threading.Thread(target=route_messages, args=(client_socket, server_socket))
    server_router = threading.Thread(target=route_messages, args=(server_socket, client_socket))

    client_router.start()
    server_router.start()
    
def route_messages(source_socket, destination_socket):

    while True:
        source_data = source_socket.recv(4096)
        if not source_data:
            break
        destination_socket.sendall(source_data)
        
def main():

    proxy_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_server_address = ('localhost', 12332)
    proxy_server_socket.bind(proxy_server_address)
    proxy_server_socket.listen(5)
    print(f'Proxy Server started on {proxy_server_address[0]}:{proxy_server_address[1]}')


    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address= ('localhost', 12331)
    server_socket.connect(server_address)
    print(f'Conected to server {server_address[0]}:{server_address[1]}')


    while True:
        client_socket, client_address = proxy_server_socket.accept()
        print(f'Client connected: {client_address[0]}:{client_address[1]}')
        message_router = threading.Thread(target=proxy, args=(client_socket, server_socket))
        message_router.start()

if __name__ == '__main__':
    main()