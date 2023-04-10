import multiprocessing
import logging
import sys
import os

from constants import LOG_FILE_PATH, LOG_LEVEL

NAME = "SERVER CONTROLLER"
SERVER_PORT_START = 12331

def start_server(port):
    """
    Function to start a single server process on the specified port
    """
    cmd = f"python -B server.py {port}"
    os.system(cmd)

def main():
    """
    Main function for start_server.py
    """

    num_servers = int(sys.argv[1])
    logging.info("Starting %s server instances", num_servers)

    # Create a list of server ports to use
    server_ports = list(range(SERVER_PORT_START, SERVER_PORT_START + num_servers))

    # Start a separate process for each server
    processes = []
    for port in server_ports:
        process = multiprocessing.Process(target=start_server, args=(port,))
        processes.append(process)
        process.start()

    # Wait for all processes to finish
    for process in processes:
        process.join()

if __name__=="__main__":
    # Configure logging
    logging.basicConfig(
    level=LOG_LEVEL,
    filename=LOG_FILE_PATH,
    format=f'[%(asctime)s] - Server - {NAME} - %(levelname)s - %(message)s',
    datefmt='%m-%d %H:%M:%S')

    # log server starting
    logging.info(f"===== Server - starting {NAME} =====")

    # run main
    main()