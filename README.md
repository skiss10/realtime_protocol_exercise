## Client-Server Protocol

This project is a client-server protocol that enables a stateful connection between a client and a server. The primary responsibility of the client is to connect to the server and receive an ordered sequence of numbers, even in the presence of intermittent disconnections. The server sends discrete sequence messages at a regular interval of one second.

## Client Description

One or more clients can connect to the server and receive a complete sequence of numbers. Individual clients can either be started with an optional argument that specifies the number n of messages to receive or the sequence legnth can be choosen randomly for you. More info on starting these clients below. 

The client's job is to receive the sequence, calculate the checksum, and compare it with the checksum value supplied by the server. Once the checksums have been calculated, the client will close the connection and notify the user of success via stdout.

 If the client's connection drops at any point during the sequence transfer, it supplies the server with re-connection parameters that allow the server to continue sequence delivery. The client will indefinitely attempt to reconnect to the server in the event of a disconnection.

## Server Description

The server receives the connection requests from clients and randomly initializes a PRNG, which generates a unique set of uint32 numbers the each client. The server sends this designated sequence to the client in a stream of discrete messages with a 1-second interval. The server maintains session state for each client for up to 30s during periods of disconnection.

If a client fails to reconnect within 30s, the server discards the state, and any subsequent reconnection attempts for that sequence from the client will be rejected. The session state for a given client / sequence is discarded after the whole sequence is sent

## Installing Dependencies

To install the necessary dependencies for this project, it is recommended that you use a virtual environment.

Once the virtual environment is activated, you can install the required dependencies with requirements.txt

## Archive

During the development of this project, my initial focus was on ensuring the ordered sequence of messages was delivered from the server to clients, despite any disconnections. After experimenting with different approaches, it was decided that the server and client should only be considered disconnected if heartbeats were not received. This required the use of concurrency to keep track of heartbeats. 
    
As this was the first project involving concurrency, I experimented with asyncio and multithreading. After becoming more comfortable with multithreading through a tutorial, I decided to use it exclusively. Testing files were created to set up the desired concurrency behavior and, once this was achieved, the original code was ported to these test files and became the main server.py and client.py files. The original files were archived for reference.

## Constants
The constants.py file contains several important global variables for the server and client applications. 

The LOG_LEVEL variable determines the level of detail to be logged and can be set to either DEBUG or INFO. 
    
The LOG_FILE_PATH variable sets the path for the log file. 
    
The HEARTBEAT_INTERVAL variable sets the interval for the heartbeat message to be sent from the client to the server. 
    
Finally, the RECONNECT_WINDOW variable determines the time window in seconds within which the server will accept reconnection attempts from a disconnected client. After the RECONNECT_WINDOW time window expires, the server will reject reconnection attempts and remove the client's connection information from the session storage.

## TODO

This project includes a TODO file that outlines several tasks for future development of the project. 


## Implementation

### Setup

1. Clone the repository to your local machine.
2. Navigate to the root directory of the project and activate the virtual environment with dependencies installed from the `requirements.txt` file.

    ```sh
    $ cd /path/to/project/root
    $ source venv/bin/activate
    $ pip install -r requirements.txt
    ```

3. Start the server in the first terminal. The default port is 49155 on localhost, but you can specify a different port with a command-line argument.

    ```sh
    $ python -B server.py
    ```
    
    or
    
    ```sh
    $ python -B server.py <server_port>
    ```

4. If you want to simulate disconnections between the server and client, start the proxy in a second terminal. The proxy acts as another server that relays all ingress and egress traffic for clients to the server and vice versa. If you stop the proxy with a keyboard interrupt, the message forwarding stops (simulating a disconnection). The default proxy port is 49156, and the default server port is 49155. You can change these with command-line arguments:

    ```sh
    $ python -B proxy.py
    ```

    or

    ```sh
    $ python -B proxy.py <proxy_port> <server_port>
    ```

    **Note:** If the server is not using the default port, you must use the proxy command-line arguments.

5. Use a third terminal to run the client. You must point `client.py` to either the proxy port (if you want to simulate disconnections) or the server port. There is an optional second parameter to send the server the length of the sequence that you would like the client to receive. If you don't provide this optional length, a random length will be determined for you between 1 and 65535. You can spin up as many clients as you like (see Limitations in README).

    ```sh
    $ python -B client.py <server_port/proxy_port>
    ```

    or

    ```sh
    $ python -B client.py <server_port/proxy_port> <sequence_length>
    ```

6. Once the sequence transfer begins, if you want to simulate disconnections between the server and client, interrupt the proxy application with a keyboard interrupt. If you restart the proxy within 30 seconds, the sequence will continue (depending on when the last heartbeat was received by the client/last heartbeat_ack was received by the server). If you wait more than 30 seconds to restart the proxy, the server will remove the session information for the client, and automatic reconnection attempts from the client through the proxy will be rejected.

7. Once the sequence is completed, both `app.log` in the `logs` directory and the clients' stdout will display "system - SUCCESS! local checksum and server checksum are equal".

## Limitations:

This has been tested with up to 15 concurrent clients on a MacBook Pro with an Apple M1 pro chip. 

## Sequence Diagram

I've added a sequence diagram to show the behavior of this client-server protocol when there are no disconnections. The sequences with dotted lines indicate a function or service that runs continuously thoughout the life of the program / connection.