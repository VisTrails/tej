"""Entry point for the tej utility.
"""

from __future__ import unicode_literals

import argparse
import codecs
import locale
import logging
import sys

from tej import __version__ as tej_version

from tej.submission import RemoteQueue


def _setup(args):
    RemoteQueue(args.destination, args.queue).setup(args.make_link, args.force)


def _submit(args):
    RemoteQueue(args.destination, args.queue).submit(
            args.id, args.directory, args.script)


def _status(args):
    RemoteQueue(args.destination, args.queue).status(args.id)


def _download(args):
    RemoteQueue(args.destination, args.queue).kill(args.files)


def _kill(args):
    RemoteQueue(args.destination, args.queue).kill(args.id)


def _delete(args):
    RemoteQueue(args.destination, args.queue).delete(args.id)


def setup_logging(verbosity):
    levels = [logging.CRITICAL, logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(verbosity, 3)]

    fmt = "%(asctime)s %(levelname)s: %(message)s"
    formatter = logging.Formatter(fmt)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logging.getLogger().addHandler(handler)
    logging.getLogger('tej').setLevel(level)


DEFAULT_TEJ_DIR = '~/.tej'


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
                         version="tej version %s" % tej_version)
    options.add_argument('-v', '--verbose', action='count', default=1,
                         dest='verbosity',
                         help="augments verbosity level")

    # Root parser
    parser = argparse.ArgumentParser(
            description="Trivial Extensible Job-submission",
            parents=[options])
    subparsers = parser.add_subparsers(title='commands', metavar='')

    # Destination selection
    options_dest = argparse.ArgumentParser(add_help=False)
    options_dest.add_argument('destination', action='store',
                              help="Machine to SSH into; [user@]host[:port]")
    options_dest.add_argument('--queue', action='store',
                               default=DEFAULT_TEJ_DIR,
                               help="Directory for tej's files")

    # Setup action
    parser_setup = subparsers.add_parser(
            'setup', parents=[options, options_dest],
            help="Sets up tej on a remote machine")
    parser_setup.add_argument('--make-link', action='append',
                              dest='make_link')
    parser_setup.add_argument('--make-default-link', action='append_const',
                              dest='make_link', const=DEFAULT_TEJ_DIR)
    parser_setup.add_argument('--force', action='store_true')
    parser_setup.set_defaults(func=_setup)

    # Submit action
    parser_submit = subparsers.add_parser(
            'submit', parents=[options, options_dest],
            help="Submits a job to a remote machine")
    parser_submit.add_argument('--id', action='store',
                               help="Identifier for the new job")
    parser_submit.add_argument('--script', action='store',
                               help="Relative name of the script in the "
                                    "directory")
    parser_submit.add_argument('directory', action='store',
                               help="Job directory to upload")
    parser_submit.set_defaults(func=_submit)

    # Status action
    parser_status = subparsers.add_parser(
            'status', parents=[options, options_dest],
            help="Gets the status of a job")
    parser_status.add_argument('--id', action='store',
                               help="Identifier of the running job")
    parser_status.set_defaults(func=_status)

    # Download action
    parser_download = subparsers.add_parser(
            'download', parents=[options, options_dest],
            help="Downloads files from finished job")
    parser_download.add_argument('--id', action='store',
                                 help="Identifier of the job")
    parser_download.add_argument('file', action='store',
                                 nargs=argparse.ONE_OR_MORE,
                                 help="Files to download")
    parser_download.set_defaults(func=_download)

    # Kill action
    parser_kill = subparsers.add_parser(
            'status', parents=[options, options_dest],
            help="Kills a running job")
    parser_kill.add_argument('--id', action='store',
                               help="Identifier of the running job")
    parser_kill.set_defaults(func=_kill)

    # Delete action
    parser_delete = subparsers.add_parser(
            'delete', parents=[options, options_dest],
            help="Deletes a finished job")
    parser_delete.add_argument('--id', action='store',
                               help="Identifier of the finished job")
    parser_delete.set_defaults(func=_delete)

    args = parser.parse_args()
    setup_logging(args.verbosity)

    args.func(args)
    sys.exit(0)


if __name__ == '__main__':
    main()
