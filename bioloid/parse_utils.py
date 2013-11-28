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
        val = int(string, 0)
    except ValueError:
        if label:
            raise ValueError("Expecting an integer %s. Found '%s'"
                             % (label, string))
        raise ValueError("Expecting an integer. Found '%s'" % string)
    return val


def parse_int(string, label=None):
    """Convert a string into an integer.

    Raises a ValueError exception if the conversion fails.

    """
    try:
        val = int(string, 0)
    except ValueError:
        if label:
            raise ValueError("Expecting an integer %s. Found '%s'"
                             % (label, string))
        raise ValueError("Expecting an integer. Found '%s'" % string)
    return val
