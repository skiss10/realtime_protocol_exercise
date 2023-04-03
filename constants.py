"""
Module to store all constants

Author: Stephen Kiss (stephenkiss986@gmail.com)
Date: 01/23/2023
"""

# This variable is a global variable for controlling the logging level
LOG_LEVEL = 'DEBUG'

# This variable is a global variable for the path of the log file
LOG_FILE_PATH = './app.log'

# Set heartbeat interval in seconds
HEARTBEAT_INTERVAL = 5

# set reconnect window in seconds
# after which reconnection attemps are rejected and server removes connection info from session_storage
RECONNECT_WINDOW = 60

