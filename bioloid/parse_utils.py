"""Some helper functions for parsing numbers."""


def str_to_int(string):
    """Converts a string to an integer. Returns None on failure."""
    try:
        val = int(string, 0)
    except ValueError:
        return None
    return val


def str_to_float(string):
    """Converts a string to an float. Returns None on failure."""
    try:
        val = float(string)
    except ValueError:
        return None
    return val


def parse_float(string, label=None):
    """Convert a string into a float.

    Raises a ValueError exception if the conversion fails.

    """
    try:
        val = float(string)
    except ValueError:
        if label:
            raise ValueError("Expecting a float %s. Found '%s'"
                             % (label, string))
        raise ValueError("Expecting a float. Found '%s'" % string)
    return val


def parse_int(string, label=None, base=0):
    """Convert a string into an integer.

    Raises a ValueError exception if the conversion fails.

    """
    try:
        val = int(string, base)
    except ValueError:
        if label:
            raise ValueError("Expecting an integer %s. Found '%s'"
                             % (label, string))
        raise ValueError("Expecting an integer. Found '%s'" % string)
    return val


def parse_byte_array(words, base=0):
    """Parses words as an array of hex-strings and returns an array
    of bytes containing the corresponding hex values.

    """
    data = b''
    for byte_str in words:
        byte = parse_int(byte_str, "byte", base=base)
        if byte < 0 or byte > 255:
            if base == 16:
                raise ValueError("Expecting hex-byte to be in range 00-FF. " +
                                 "Found: %x" % byte)
            raise ValueError("Expecting byte to be in range 0-256. " +
                             "Found: %s" % byte_str)
        data += bytes([byte])
    return data
