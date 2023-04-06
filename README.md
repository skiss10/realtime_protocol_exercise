Client-Server Protocol

    This project is a client-server protocol that enables a stateful connection between a client and a server. The primary responsibility of the client is to connect to the server and receive an ordered sequence of numbers, even in the presence of intermittent disconnections. The server sends discrete sequence messages at a regular interval of one second.

Client Description

    One or more clients can connect to the server and receive a complete sequence of numbers. Individual clients can either be started with an optional argument that specifies the number n of messages to receive or the sequence legnth can be choosen randomly for you. More info on starting these clients below. 

    The client's job is to receive the sequence, calculate the checksum, and compare it with the checksum value supplied by the server. Once the checksums have been calculated, the client will close the connection and notify the user of success via stdout.

    If the client's connection drops at any point during the sequence transfer, it supplies the server with re-connection parameters that allow the server to continue sequence delivery. The client will indefinitely attempt to reconnect to the server in the event of a disconnection.

Server Description

    The server receives the connection requests from clients and randomly initializes a PRNG, which generates a unique set of uint32 numbers the each client. The server sends this designated sequence to the client in a stream of discrete messages with a 1-second interval. The server maintains session state for each client for up to 30s during periods of disconnection.

    If a client fails to reconnect within 30s, the server discards the state, and any subsequent reconnection attempts for that sequence from the client will be rejected. The session state for a given client / sequence is discarded after the whole sequence is sent

Installing Dependencies

    To install the necessary dependencies for this project, it is recommended that you use a virtual environment.

    Once the virtual environment is activated, you can install the required dependencies using the following command:
    pip install -r requirements.txt

Archive

    During the development of this project, my initial focus was on ensuring the ordered sequence of messages was delivered from the server to clients, despite any disconnections. After experimenting with different approaches, it was decided that the server and client should only be considered disconnected if heartbeats were not received. This required the use of concurrency to keep track of heartbeats. 
    
    As this was the first project involving concurrency, I experimented with asyncio and multithreading. After becoming more comfortable with multithreading through a tutorial, I decided to use it exclusively. Testing files were created to set up the desired concurrency behavior and, once this was achieved, the original code was ported to these test files and became the main server.py and client.py files. The original files were archived for reference.

Constants

    The constants.py file contains several important global variables for the server and client applications. 
    
    The LOG_LEVEL variable determines the level of detail to be logged and can be set to either DEBUG or INFO. 
    
    The LOG_FILE_PATH variable sets the path for the log file. 
    
    The HEARTBEAT_INTERVAL variable sets the interval for the heartbeat message to be sent from the client to the server. 
    
    Finally, the RECONNECT_WINDOW variable determines the time window in seconds within which the server will accept reconnection attempts from a disconnected client. After the RECONNECT_WINDOW time window expires, the server will reject reconnection attempts and remove the client's connection information from the session storage.

TODO

    This project includes a TODO file that outlines several tasks for future development of the project. 


Implementation

    Setup

        After cloning the repo locally, each terminal you use will require you to navigate to the root directory of this project and activate your virtual enviornment with depencies installed from this project's requirements.txt.

        The first terminal will run server.py. The default port (in constants.py) is 49155 on localhost but can be specified with a commandline arguement.

            python -B server.py

            -or-

            python -B server.py <server_port>

        If you wish to simulate disconnections between the server and client, a second terminal will run proxy.py. The proxy basically acts as another server that relays all ingress and egress traffic for clients to the server and vice versa. If the proxy is stopped with a keyboard interrupt, the messages forwarding stops. The default proxy port (in constants.py) is 49156 and the default server port (also in constants.py) is 49155. These can be changed with commandline arguements:

            python -B proxy.py

            -or-

            python -B proxy.py <proxy_port> <server_port>

        NOTE: if the server is not using the default port, the proxy commandline arguements must be used. 

        Next, use another terminal to run client.py. You will be required to point client.py to either the proxy port (if you wish to simulate disconnections) or the server port. There is a second, optional parameter to send the server the length of the sequence that you would like the client to recieve. If the optional length is not provided, a random length will be determined for you between 1 and 65535. You can spin up as many clients as you would like (see Limitations in README).

            python -B client.py <server_port / proxy_port>

            -or-

            python -B client.py <server_port / proxy_port> <sequence length>

        Once the sequence transfer begins, if you wish to sumulate the disconnections between the server and client, keyboard interrupt the proxy application. If you restart the proxy within 30 seconds, the sequence will continue (depending on when the last heartbeat was recieved by the client / last heartbeat_ack was recieved by the server). If wait more than 30 seconds to restart the proxy, the server will remove the session information for the client and automatic reconnection attempts from the client through the proxy will be rejected.

        Once the sequence is completed, both app.log in the logs directory and the clients' stout will display "system - SUCCESS! local checksum and server checksum are equal". 

Limitations:

    This has been tested with up to 15 concurrent clients on a MacBook Pro with an Apple M1 pro chip. 