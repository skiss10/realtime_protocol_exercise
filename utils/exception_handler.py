"""
Exception Handling module
"""

import sys

def exception_handler(func):
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except OSError:
            print(" ==== Socket Stopped from OS Error =====")
            sys.exit()
            return
        except KeyboardInterrupt:
            print(" Socket Stopped from Keyboard Interrupt")
            sys.exit()
    return wrapper
