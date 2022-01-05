"Utility functions"

import os
import tempfile
import stat

from os.path import join as pathjoin


def safe_decode(val):
    "Try to decode bytes to str"
    try:
        return val.decode('utf-8')
    except AttributeError:
        return val


def safe_encode(val):
    "Try to encode str to bytes"
    try:
        return val.encode('utf-8')
    except AttributeError:
        return val


def tempnam(dir: str, prefix: str='') -> str:  # pylint: disable=redefined-builtin
    """
    Utility function.

    Creates a temporary file, but removes and closes the file. In effect
    it creates a temporary path (that does not exist). For use as a socket
    address.
    """
    fd, path = tempfile.mkstemp(dir=dir, prefix=prefix)  # pylint: disable=invalid-name
    os.close(fd)
    os.remove(path)
    return path


def is_sock(path):
    "Checks if given path is a socket"
    return stat.S_ISSOCK(os.stat(path).st_mode)


def find_sockets(path):
    "Finds sockets in given directory"
    return [n for n in os.listdir(path) if is_sock(pathjoin(path, n))]
