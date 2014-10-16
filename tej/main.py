"""Entry point for the tej utility.
"""

from __future__ import absolute_import, print_function, unicode_literals

import argparse
import codecs
import locale
import logging
import sys

from . import __version__ as tej_version


def setup_logging(verbosity):
    levels = [logging.CRITICAL, logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(verbosity, 3)]

    fmt = "%(asctime)s %(levelname)s: %(message)s"
    formatter = logging.Formatter(fmt)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(level)
    logger.addHandler(handler)


def main():
    """Entry point when called on the command-line.
    """
    # Locale
    locale.setlocale(locale.LC_ALL, '')

    # Encoding for output streams
    if str == bytes:  # PY2
        writer = codecs.getwriter(locale.getpreferredencoding())
        o_stdout, o_stderr = sys.stdout, sys.stderr
        sys.stdout = writer(sys.stdout)
        sys.stdout.buffer = o_stdout
        sys.stderr = writer(sys.stderr)
        sys.stderr.buffer = o_stderr

    # Parses command-line

    # General options
    options = argparse.ArgumentParser(add_help=False)
    options.add_argument('--version', action='version',
                         version="gitobox version %s" % tej_version)
    options.add_argument('-v', '--verbose', action='count', default=1,
                         dest='verbosity',
                         help="augments verbosity level")

    parser = argparse.ArgumentParser(
            description="Trivial Extensible Job-submission",
            parents=[options])

    args = parser.parse_args()
    setup_logging(args.verbosity)

    logging.critical("Work in progress!")
    sys.exit(1)


if __name__ == '__main__':
    main()
