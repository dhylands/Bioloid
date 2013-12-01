"""Implements a logging formatter which produces colorized output, suitable
for use on an ANSI console.

"""

import logging
import time

# Attributes
# 0	Reset all attributes
# 1	Bright
# 2	Dim
# 4	Underscore
# 5	Blink
# 7	Reverse
# 8	Hidden

LT_BLACK = "\x1b[1;30m"
LT_RED = "\x1b[1;31m"
LT_GREEN = "\x1b[1;32m"
LT_YELLOW = "\x1b[1;33m"
LT_BLUE = "\x1b[1;34m"
LT_MAGENTA = "\x1b[1;35m"
LT_CYAN = "\x1b[1;36m"
LT_WHITE = "\x1b[1;37m"

DK_BLACK = "\x1b[2;30m"
DK_RED = "\x1b[2;31m"
DK_GREEN = "\x1b[2;32m"
DK_YELLOW = "\x1b[2;33m"
DK_BLUE = "\x1b[2;34m"
DK_MAGENTA = "\x1b[2;35m"
DK_CYAN = "\x1b[2;36m"
DK_WHITE = "\x1b[2;37m"

NO_COLOR = "\x1b[0m"

# Colors to print to the console for a given warning level. %(color)s will be
# replaced with the color indicated for a given warning level.

COLORS = {
    'WARNING': LT_YELLOW,
    'INFO': "",
    'Level 21': DK_GREEN,
    'DEBUG': LT_BLUE,
    'CRITICAL': LT_RED,
    'ERROR': LT_RED
}

# Single letter code to print using %(levelchar)s

LEVELCHAR = {
    'WARNING': 'W',
    'INFO': 'I',
    'Level 21': 'G',
    'DEBUG': 'D',
    'CRITICAL': 'C',
    'ERROR': 'E'
}


class ColoredFormatter(logging.Formatter):
    """A formatter which produces colized messages (using ANSI escape
    sequences) for the console.

    """

    def __init__(self, use_color=True, *args, **kwargs):
        #if "strm" in kwargs:
        #    kwargs['stream'] = kwargs.pop("strm")
        logging.Formatter.__init__(self, *args, **kwargs)
        self.use_color = use_color

    def format(self, record):
        """Add support for %(color)s and %(nocolor)s where the color is
        determined by the logging level.

        """
        levelname = record.levelname
        record.levelchar = LEVELCHAR[levelname]
        if self.use_color:
            record.color = COLORS[levelname]
            if len(record.color) == 0:
                record.nocolor = ""
            else:
                record.nocolor = NO_COLOR
        else:
            record.color = ""
            record.nocolor = ""

        return logging.Formatter.format(self, record)

    def formatTime(self, record, datefmt=None):
        """Override the default formatTime because we don't want the
        comma before the milliseconds, and for most stuff, I really
        don't want the date.

        """
        rectime = self.converter(record.created)
        if datefmt:
            return time.strftime(datefmt, rectime)
        return "%s.%03d" % (time.strftime("%H:%M:%S", rectime), record.msecs)


def test_main():
    """Test (put into a function so that pylint doesn't complain about
    variables being constants).

    """
    import argparse
    import sys
    from bioloid.log_setup import log_setup

    parser = argparse.ArgumentParser(
        prog="log-test",
        usage="%(prog)s [options]",
        description="Testing for the loggind module"
    )
    parser.add_argument(
        "-d", "--debug",
        dest="debug",
        action="store_true",
        help="Enable debug features",
        default=False
    )
    args = parser.parse_args(sys.argv[1:])

    log_setup(cfg_path='../logging.cfg')
    log = logging.getLogger()

    if args.debug:
        log.setLevel(logging.DEBUG)

    # You can now start issuing logging statements in your code
    log.debug('debug message')  # This won't print to myapp.log
    log.info('info message')    # Neither will this.
    log.warn('Checkout this warning.')  # This will show up in the log file.
    log.error('An error goes here.')    # and so will this.
    log.critical('Something critical happened.')  # and this one too.

if __name__ == "__main__":
    test_main()
