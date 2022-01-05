import os
import tempfile
import stat

from functools import wraps
from os.path import dirname, join as pathjoin


def safe_decode(b):
    try:
        return b.decode('utf-8')
    except AttributeError:
        return b


def tempnam(dir: str, prefix: str='') -> str:
    """
    Utility function.

    Creates a temporary file, but removes and closes the file. In effect
    it creates a temporary path (that does not exist). For use as a socket
    address.
    """
    fd, path = tempfile.mkstemp(dir=dir, prefix=prefix)
    os.close(fd)
    os.remove(path)
    return path


def is_sock(path):
    return stat.S_ISSOCK(os.stat(path).st_mode)


def find_sockets(dir):
    return [path for path in os.listdir(dir) if is_sock(pathjoin(dir, path))]
