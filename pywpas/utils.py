def safe_decode(b):
    try:
        return b.decode('utf-8')
    except AttributeError:
        return b
