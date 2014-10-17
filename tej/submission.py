from __future__ import unicode_literals

import getpass
import logging
import paramiko
import pkg_resources
import random
import re
from rpaths import PosixPath, Path
import scp
import select
import string
import sys

from tej.utils import iteritems, irange


logger = logging.getLogger('tej')


def unique_names():
    """Generates unique sequences of bytes.
    """
    characters = ("abcdefghijklmnopqrstuvwxyz"
                  "0123456789")
    characters = [characters[i:i + 1] for i in irange(len(characters))]
    rng = random.Random()
    while True:
        letters = [rng.choice(characters) for i in irange(10)]
        yield ''.join(letters)
unique_names = unique_names()


def make_unique_name():
    """Makes a unique (random) string.
    """
    return next(unique_names)


def shell_escape(s):
    """Given bl"a, returns "bl\\"a".
    """
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    if any(c in s for c in string.whitespace + '*$\\"\''):
        return '"%s"' % (s.replace('\\', '\\\\')
                          .replace('"', '\\"')
                          .replace('$', '\\$'))
    else:
        return s


_re_ssh = re.compile(r'^'
                     r'(?:ssh://)?'              # 'ssh://' prefix
                     r'(?:([a-zA-Z0-9_.-]+)@)?'  # 'user@'
                     r'([a-zA-Z0-9_.-]+)'        # 'host'
                     r'(?::([0-9]+))?'           # ':port'
                     r'$')


def parse_ssh_destination(destination):
    """Parses the SSH destination argument.
    """
    match = _re_ssh.match(destination)
    if not match:
        raise ValueError("Invalid destination: %s" % destination)
    user, host, port = match.groups()
    info = {}
    if user:
        info['username'] = user
    else:
        info['username'] = getpass.getuser()
    if port:
        info['port'] = int(port)
    info['hostname'] = host

    return info


class RemoteQueue(object):
    def __init__(self, destination, queue):
        self.destination = destination
        self.queue = PosixPath(queue)
        self.ssh = None
        self._connect()

    def _connect(self):
        """Connects via SSH.
        """
        try:
            self.parsed_destination = parse_ssh_destination(self.destination)
        except ValueError as e:
            logger.critical(e)
            sys.exit(1)

        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
        logger.debug("Connecting with %s",
                     ', '.join('%s=%r' % i
                               for i in iteritems(self.parsed_destination)))
        self.ssh.connect(**self.parsed_destination)
        logger.debug("Connected to %s", self.parsed_destination['hostname'])

    def _call(self, cmd, get_output):
        """Calls a command through the SSH connection.

        Remote stderr gets printed to this program's stderr. Output is captured
        and may be returned.
        """
        chan = self.ssh.get_transport().open_session()
        try:
            logger.debug("Invoking %r%s",
                         cmd, " (stdout)" if get_output else "")
            chan.exec_command('/bin/sh -c %s' % shell_escape(cmd))
            output = b''
            while not chan.exit_status_ready():
                r, w, e = select.select([chan], [], [])
                if chan in r:
                    if chan.recv_stderr_ready():
                        data = chan.recv_stderr(1024)
                        if data:
                            sys.stderr.buffer.write(data)
                            sys.stderr.flush()
                    if chan.recv_ready():
                        data = chan.recv(1024)
                        if get_output:
                            output += data
            return chan.recv_exit_status(), output
        finally:
            chan.close()

    def check_call(self, cmd):
        """Calls a command through SSH.
        """
        ret, _ = self._call(cmd, False)
        assert ret == 0

    def check_output(self, cmd):
        """Calls a command through SSH and returns its output.
        """
        ret, output = self._call(cmd, True)
        assert ret == 0
        output = output.rstrip(b'\r\n')
        logger.debug("Output: %r", output)
        return output

    def _resolve_queue(self, queue, depth=0):
        """Finds the location of tej's queue directory on the server.

        The `queue` set when constructing this `RemoteQueue` might be relative
        to the home directory and might contain ``~user`` placeholders. Also,
        each queue may in fact be a link to another path (a file containing
        the string ``tejdir:``, a space, and a new pathname, relative to this
        link's location).
        """
        if depth == 0:
            logger.debug("resolve_queue(%s)", queue)
        answer = self.check_output(
                'if [ -d %(queue)s ]; then '
                '    cd %(queue)s; echo "dir: $(pwd)"; '
                'elif [ -f %(queue)s ]; then '
                '    cat %(queue)s; '
                'else '
                '    echo no; '
                'fi' % {
                    'queue': shell_escape(bytes(queue))})
        if answer == b'no':
            if depth > 0:
                logger.debug("Broken link at depth=%d", depth)
            else:
                logger.debug("Path doesn't exist")
            return None, depth
        elif answer.startswith(b'dir: '):
            new = PosixPath(answer[5:])
            logger.debug("Found directory at %s, depth=%d", new, depth)
            return new, depth
        elif answer.startswith(b'tejdir: '):
            new = queue.parent / answer[8:]
            logger.debug("Found link to %s, recursing", new)
            return self._resolve_queue(new, depth + 1)
        logging.critical("Server returned %r", answer)
        sys.exit(1)

    def _get_queue(self):
        """Gets the actual location of the queue, or None.
        """
        queue, depth = self._resolve_queue(self.queue)
        if queue is None and depth > 0:
            logger.critical("Queue link chain is broken")
            sys.exit(1)
        logger.debug("get_queue = %s", queue)
        return queue

    def setup(self, links=None, force=False):
        """Installs the runtime at the target location.

        This will not replace an existing installation, unless it is a broken
        chain of links or `force` is True.

        After installation, creates links to this installation at the specified
        locations.
        """
        if not links:
            links = []

        queue, depth = self._resolve_queue(self.queue)
        if queue is not None or depth > 0:
            if force:
                if queue is None:
                    logger.info("Replacing broken link")
                elif depth > 0:
                    logger.info("Replacing link to %s...", queue)
                else:
                    logger.info("Replacing existing queue...")
                self.check_call('rm -Rf %s' % shell_escape(str(self.queue)))
            else:
                if queue is not None and depth > 0:
                    logger.critical("Queue already exists (links to %s)\n"
                                    "Use --force to replace", queue)
                elif depth > 0:
                    logger.critical("Broken link exists\n"
                                    "Use --force to replace")
                else:
                    logger.critical("Queue already exists\n"
                                    "Use --force to replace")
                sys.exit(1)

        queue = self._setup()

        for link in links:
            self.check_call('echo "tejdir:" %(queue)s > %(link)s' % {
                    'queue': shell_escape(str(queue)),
                    'link': shell_escape(link)})

    def _setup(self):
        """Actually installs the runtime.
        """
        logger.info("Installing runtime at %s", self.queue)

        # Expands ~user in queue
        output = self.check_output('echo %s' % shell_escape(str(self.queue)))
        queue = PosixPath(output.rstrip(b'\r\n'))
        logger.debug("Resolved to %s", queue)

        # Uploads runtime
        scp_client = scp.SCPClient(self.ssh.get_transport())
        filename = pkg_resources.resource_filename('tej', 'remotes/default')
        scp_client.put(filename, str(queue), recursive=True)
        logger.debug("Files uploaded")

        # Runs post-setup script
        self.check_call('/bin/sh %s' % (queue / 'commands' / 'setup'))
        logger.debug("Post-setup script done")

        return queue

    def submit(self, job_id, directory, script=None):
        """Submits a job to the queue.

        If the runtime is not there, it will be installed. If it is a broken
        chain of links, error.
        """
        queue = self._get_queue()

        if queue is None:
            queue = self._setup()

        if job_id is None:
            job_id = '%s_%s_%s' % (Path(directory).unicodename,
                                   self.parsed_destination['username'],
                                   make_unique_name())

        if script is None:
            script = 'start.sh'

        # Create directory
        target = self.check_output('%s %s' % (
                                   queue / 'commands' / 'new_job',
                                   job_id))
        target = PosixPath(target)
        logger.debug("Server created directory %s", target)

        # Upload to directory
        scp_client = scp.SCPClient(self.ssh.get_transport())
        scp_client.put([str(p) for p in Path(directory).listdir()],
                       str(target),
                       recursive=True)
        logger.debug("Files uploaded")

        # Submit job
        self.check_call('%s %s %s %s' % (queue / 'commands' / 'submit',
                                         job_id, target,
                                         script))
        logger.info("Submitted job %s", job_id)

    def status(self, job_id):
        """Gets the status of a previously-submitted job.
        """
        queue = self._get_queue()

        if queue is None:
            logger.critical("Queue doesn't exist on the server")
            sys.exit(1)

        ret, output = self._call('%s %s' % (queue / 'commands' / 'status',
                                            job_id),
                                 True)
        if ret == 0:
            print("done")
            print(output)
        elif ret == 2:
            print("running")
        elif ret == 3:
            print("not found")
        else:
            logger.error("Error!")
            sys.exit(1)

    def download(self, job_id, files):
        # TODO : download
        raise NotImplementedError("download")

    def kill(self, job_id):
        # TODO : kill
        raise NotImplementedError("kill")

    def delete(self, job_id):
        # TODO : delete
        raise NotImplementedError("delete")

    # TODO : list
