"""Provides the dump_mem function, which dumps memory in hex/ASCII."""



def default_print(line):
    """Default print routine to use, if one wasn't provided."""
    print(line)


def dump_mem(buf, prefix="", address=0, line_width=16, show_ascii=True,
             show_addr=True, print_func=None):
    """Dumps out a hex/ASCII representation of the given buffer."""
    print('dump_mem type of buf =', type(buf))
    if line_width < 0:
        line_width = 16
    if print_func is None:
        print_func = default_print
    if len(prefix) > 0:
        prefix += ": "
    if len(buf) == 0:
        print_func(prefix + "No data")
        return
    buf_len = len(buf)
    for offset in range(0, buf_len, line_width):
        line_hex = ""
        line_ascii = ""
        for line_offset in range(0, line_width):
            ch_offset = offset + line_offset
            if ch_offset < buf_len:
                char = buf[offset + line_offset]
                line_hex += "%02x " % char
                if char < ord(' ') or char > ord('~'):
                    line_ascii += "."
                else:
                    line_ascii += "%c" % char
            else:
                if show_ascii:
                    line_hex += "   "
                else:
                    break
        out_line = prefix
        if show_addr:
            out_line += ("%04x: " % address)
        out_line += line_hex
        if show_ascii:
            out_line += line_ascii
        else:
            # Remove the trailing space after the last hex
            out_line = out_line[0:-1]
        print_func(out_line)
        address += line_width

if __name__ == "__main__":
    PREFIX = "    Prefix"
    print("Empty Buffer")
    dump_mem("", prefix=PREFIX)

    print("")
    print("Less than line")
    dump_mem("0123", prefix=PREFIX)

    print("")
    print("Exactly one line")
    dump_mem("0123456789ABCDEF", prefix=PREFIX)

    print("")
    print("A bit more than a line")
    dump_mem("0123456789ABCDEFGHI", prefix=PREFIX)

    print("")
    print("Set a prefix")
    dump_mem("0123", prefix="    Something")

    print("")
    print("Set an address and a line_width")
    dump_mem("0123456789ABCDEFGHI", address=0x2000, line_width=8,
             prefix=PREFIX)

    def my_print_func(line):
        """my_print_func."""
        print("    print_func:", line)

    print("")
    print("With a print_func")
    dump_mem("0123", print_func=my_print_func)

    DATA = "0123"
    DATA += chr(0)
    DATA += chr(0x80)
    DATA += chr(0xFF)
    print("")
    print("Check out some non-printable characters")
    dump_mem(DATA, prefix=PREFIX)

    print("")
    print("With no prefix")
    dump_mem("0123")
