"""Print nicely formatted columns."""


def align_cell(fmt, elem, width):
    """Returns an aligned element."""
    if fmt == "<":
        return elem + ' ' * (width - len(elem))
    if fmt == ">":
        return ' ' * (width - len(elem)) + elem
    return elem


def default_print(line):
    """Print routine used if none is supplied."""
    print(line)


def column_print(fmt, rows, print_func=None):
    """Prints a formatted list, adjusting the width so everything fits.
    fmt contains a single character for each column. < indicates that the
    column should be left justified, > indicates that the column should
    be right justified. The last column may be a space which imples left
    justification and no padding.

    """
    if print_func is None:
        print_func = default_print
    # Figure out the max width of each column
    num_cols = len(fmt)
    width = [max(0 if isinstance(row, str) else len(row[i]) for row in rows)
             for i in range(num_cols)]
    for row in rows:
        if isinstance(row, str):
            # Print a seperator line
            print_func(' '.join([row * width[i] for i in range(num_cols)]))
        else:
            print_func(' '.join([align_cell(fmt[i], row[i], width[i])
                                 for i in range(num_cols)]))

if __name__ == "__main__":
    FMT = '<> '
    ROWS = [['A', 'BBBBB', 'CC'],
            '-',
            ['12', 'a', 'Description'],
            ['1',  'abc', ''],
            '=',
            ['123', 'abcdef', 'WooHoo']]
    column_print(FMT, ROWS)
