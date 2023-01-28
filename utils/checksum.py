"""
Checksum module
"""

import hashlib
import logging

def calculate_checksum(uint32_numbers):
    """
    Input: list of uint32 numbers of arbitrary length

    Output: MD5 checksum
    """
    # concatenate all values in the list
    numbers = "".join(str(i) for i in uint32_numbers)

    # create md5 hash object
    md5 = hashlib.md5()

    # update the hash object with the data
    md5.update(numbers.encode())

    # get the hexadecimal representation of the md5 hash
    checksum = md5.hexdigest()

    # return checksum
    logging.debug("Server - hash of uint32 numbers: %s", checksum)
    return checksum