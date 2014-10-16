"""Entry point for the tej utility.
"""

from __future__ import unicode_literals

import argparse
import codecs
import getpass
import locale
import logging
import paramiko
import re
import sys

from . import __version__ as tej_version


_re_ssh = re.compile(r'^'
                     r'(?:ssh://)?'              # 'ssh://' prefix
                     r'(?:([a-zA-Z0-9_.-]+)@)?'  # 'user@'
                     r'([a-zA-Z0-9_.-]+)'        # 'host'
                     r'(?::([0-9]+))?'           # ':port'
                     r'$')

def parse_ssh_destination(destination):
    match = _re_ssh.match(destination)
    if not match:
        raise ValueError("Invalid destination: %s" % destination)
    user, host, port = match.groups()
    info = {}
    if user:
        info['username'] = user
    if port:
        try:
            info['port'] = int(port)
        except ValueError:
            raise ValueError("Invalid port number: %s" % port)
    info['hostname'] = host

    return info


def _connect(func):
    def wrapper(args):
        try:
            info = parse_ssh_destination(args.destination)
        except ValueError, e:
            logging.critical(e)
            sys.exit(1)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
        ssh.connect(**info)

        try:
            return func(args, ssh)
        finally:
            ssh.close()
    return wrapper


@_connect
def _setup(args, ssh):
    pass


@_connect
def _submit(args, ssh):
    pass


@_connect
def _status(args, ssh):
    pass


@_connect
def _kill(args, ssh):
    pass


@_connect
def _download(args, ssh):
    pass


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
                         version="gitobox version %s" % tej_version)
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

    # Setup options; shared between 'setup' and 'submit'
    options_setup = argparse.ArgumentParser(add_help=False)
    options_setup.add_argument('--queue', action='store',
                               default=DEFAULT_TEJ_DIR,
                               help="Directory for tej's files")

    # Setup action
    parser_setup = subparsers.add_parser(
            'setup', parents=[options, options_setup],
            help="Sets up tej on a remote machine")
    parser_setup.add_argument('--make-link', action='append',
                              dest='make_link')
    parser_setup.add_argument('--make-default-link', action='append_const',
                              dest='make_link', const=DEFAULT_TEJ_DIR)
    parser_setup.set_defaults(_setup)

    # Submit action
    parser_submit = subparsers.add_parser(
            'submit', parents=[options, options_setup],
            help="Submits a job to a remote machine")
    parser_submit.set_defaults(_submit)

    # Status action
    parser_status = subparsers.add_parser(
            'status', parents=[options],
            help="Gets the status of a job")
    parser_status.set_defaults(_status)

    # Kill action
    parser_kill = subparsers.add_parser(
            'status', parents=[options],
            help="Kills a running job")
    parser_kill.set_defaults(_kill)

    # Download action
    parser_download = subparsers.add_parser(
            'download', parents=[options],
            help="Downloads files from finished job")
    parser_download.set_defaults(_download)

    args = parser.parse_args()
    setup_logging(args.verbosity)

    args.func(args)
    sys.exit(0)


if __name__ == '__main__':
    main()
