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

from tej.utils import string_types, iteritems, irange


__all__ = ['DEFAULT_TEJ_DIR',
           'Error', 'InvalidDestionation', 'QueueDoesntExist',
           'QueueLinkBroken', 'QueueExists', 'JobAlreadyExists', 'JobNotFound',
           'JobStillRunning'
           'parse_ssh_destination', 'destination_as_string', 'RemoteQueue']


DEFAULT_TEJ_DIR = '~/.tej'


class Error(Exception):
    """Base class for exceptions.
    """


class InvalidDestionation(Error):
    """Invalid SSH destination.
    """
    def __init__(self, msg="Invalid destination"):
        super(InvalidDestionation, self).__init__(msg)


class QueueDoesntExist(Error):
    """Queue doesn't exist on the server.

    `submit` and `setup` will create a queue on the server, but other commands
    like `status` and `kill` expect it to be there.
    """
    def __init__(self, msg="Queue doesn't exist on the server"):
        super(QueueDoesntExist, self).__init__(msg)


class QueueLinkBroken(QueueDoesntExist):
    """The chain of links is broken.

    There is a link file on the server that doesn't point to anything.
    """
    def __init__(self, msg="Queue link chain is broken"):
        super(QueueLinkBroken, self).__init__(msg)


class QueueExists(Error):
    """The queue whose creation was requested already exists.

    A `force` argument (``--force``) is provided to replace it anyway.
    """
    def __init__(self, msg="Queue already exists"):
        super(QueueExists, self).__init__(msg)


class JobAlreadyExists(Error):
    """A job with this name already exists on the server; submission failed.
    """
    def __init__(self, msg="Job already exists"):
        super(JobAlreadyExists, self).__init__(msg)


class JobNotFound(Error):
    """A job with this name wasn't found on the server.
    """
    def __init__(self, msg="Job not found"):
        super(JobNotFound, self).__init__(msg)


class JobStillRunning(Error):
    """An operation failed because the target job is still running.
    """
    def __init__(self, msg="Job is still running"):
        super(JobStillRunning, self).__init__(msg)


logger = logging.getLogger('tej')


if hasattr(sys.stderr, 'buffer') and hasattr(sys.stderr.buffer, 'write'):
    stderr_bytes = sys.stderr.buffer
else:
    stderr_bytes = sys.stderr


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
        raise InvalidDestionation("Invalid destination: %s" % destination)
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


def destination_as_string(destination):
    if destination.get('port', 22) != 22:
        return 'ssh://%s@%s:%d' % (destination['username'],
                                   destination['hostname'],
                                   destination['port'])
    else:
        return 'ssh://%s@%s' % (destination['username'],
                                destination['hostname'])


class RemoteQueue(object):
    JOB_DONE = 0
    JOB_RUNNING = 2

    def __init__(self, destination, queue):
        if isinstance(destination, string_types):
            try:
                self.destination = parse_ssh_destination(destination)
            except ValueError as e:
                raise InvalidDestionation("Can't parse SSH destination %s" %
                                          destination)
        else:
            if 'hostname' not in destination:
                raise InvalidDestionation("destination dictionary is missing "
                                          "hostname")
            self.destination = destination
        self.queue = PosixPath(queue)
        self.ssh = None
        self._connect()

    @property
    def destination_string(self):
        return destination_as_string(self.destination)

    def _connect(self):
        """Connects via SSH.
        """
        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
        logger.debug("Connecting with %s",
                     ', '.join('%s=%r' % i
                               for i in iteritems(self.destination)))
        self.ssh.connect(**self.destination)
        logger.debug("Connected to %s", self.destination['hostname'])

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
                            stderr_bytes.write(data)
                            stderr_bytes.flush()
                    if chan.recv_ready():
                        data = chan.recv(1024)
                        if get_output:
                            output += data
            output = output.rstrip(b'\r\n')
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
        logger.debug("Server returned %r", answer)
        raise RuntimeError("Remote command failed in unexpected way")

    def _get_queue(self):
        """Gets the actual location of the queue, or None.
        """
        queue, depth = self._resolve_queue(self.queue)
        if queue is None and depth > 0:
            raise QueueLinkBroken
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
                    raise QueueExists("Queue already exists (links to %s)\n"
                                      "Use --force to replace" % queue)
                elif depth > 0:
                    raise QueueExists("Broken link exists\n"
                                      "Use --force to replace")
                else:
                    raise QueueExists("Queue already exists\n"
                                      "Use --force to replace")

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
                                   self.destination['username'],
                                   make_unique_name())

        if script is None:
            script = 'start.sh'

        # Create directory
        ret, target = self._call('%s %s' % (
                                 queue / 'commands' / 'new_job',
                                 job_id),
                                 True)
        if ret == 4:
            raise JobAlreadyExists
        elif ret != 0:
            raise JobNotFound("Couldn't create job")
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
            raise QueueDoesntExist

        ret, output = self._call('%s %s' % (queue / 'commands' / 'status',
                                            job_id),
                                 True)
        if ret == 0:
            directory, result = output.split('\n')[:2]
            return RemoteQueue.JOB_DONE, PosixPath(directory), result
        elif ret == 2:
            directory = output.split('\n')[0]
            return RemoteQueue.JOB_RUNNING, PosixPath(directory), None
        elif ret == 3:
            raise JobNotFound
        else:
            raise RuntimeError("Remote script returned unexpected error code "
                               "%d" % ret)

    def download(self, job_id, files, **kwargs):
        """Downloads files from server.
        """
        if not files:
            return
        if isinstance(files, string_types):
            files = [files]
        directory = False
        recursive = kwargs.pop('recursive', True)

        if 'destination' in kwargs and 'directory' in kwargs:
            raise TypeError("Only use one of 'destination' or 'directory'")
        elif 'destination' in kwargs:
            destination = Path(kwargs.pop('destination'))
            if len(files) != 1:
                raise ValueError("'destination' specified but multiple files "
                                 "given; did you mean to use 'directory'?")
        elif 'directory' in kwargs:
            destination = Path(kwargs.pop('directory'))
            directory = True
        if kwargs:
            raise TypeError("Got unexpected keyword arguments")

        # Might raise JobNotFound
        status, target, result = self.status(job_id)

        scp_client = scp.SCPClient(self.ssh.get_transport())
        for filename in files:
            logger.info("Downloading %s", target / filename)
            if directory:
                scp_client.get(str(target / filename),
                               str(destination / filename),
                               recursive=recursive)
            else:
                scp_client.get(str(target / filename),
                               str(destination),
                               recursive=recursive)

    def kill(self, job_id):
        """Kills a job on the server.
        """
        queue = self._get_queue()
        if queue is None:
            raise QueueDoesntExist

        ret, output = self._call('%s %s' % (queue / 'commands' / 'kill',
                                            job_id),
                                 False)
        if ret == 3:
            raise JobNotFound
        elif ret != 0:
            raise RuntimeError("Remote script returned unexpected error code "
                               "%d" % ret)

    def delete(self, job_id):
        """Deletes a job from the server.
        """
        queue = self._get_queue()
        if queue is None:
            raise QueueDoesntExist

        ret, output = self._call('%s %s' % (queue / 'commands' / 'delete',
                                            job_id),
                                 False)
        if ret == 3:
            raise JobNotFound
        elif ret == 2:
            raise JobStillRunning
        elif ret != 0:
            raise RuntimeError("Remote script returned unexpected error code "
                               "%d" % ret)

    # TODO : list
