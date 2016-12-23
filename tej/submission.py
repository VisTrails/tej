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
import socket

from tej.utils import unicode_, string_types, iteritems, irange


__all__ = ['DEFAULT_TEJ_DIR',
           'Error', 'InvalidDestination', 'QueueDoesntExist',
           'QueueLinkBroken', 'QueueExists', 'JobAlreadyExists', 'JobNotFound',
           'JobStillRunning', 'RemoteCommandFailure',
           'parse_ssh_destination', 'destination_as_string',
           'ServerLogger', 'RemoteQueue']


DEFAULT_TEJ_DIR = '~/.tej'


class Error(Exception):
    """Base class for exceptions.
    """


class InvalidDestination(Error):
    """Invalid SSH destination.
    """
    def __init__(self, msg="Invalid destination"):
        super(InvalidDestination, self).__init__(msg)


# Backward compatibility
InvalidDestionation = InvalidDestination


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


class RemoteCommandFailure(Exception):
    """A failure that happened on the server.
    """
    def __init__(self, msg=None, command=None, ret=None):
        if msg is None:
            msg = "Command %r failed with status %d" % (command, ret)
        super(RemoteCommandFailure, self).__init__(msg)
        self.command = command
        self.ret = ret


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


safe_shell_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                       "abcdefghijklmnopqrstuvwxyz"
                       "0123456789"
                       "-+=/:.,%_")


def shell_escape(s):
    r"""Given bl"a, returns "bl\\"a".
    """
    if isinstance(s, PosixPath):
        s = unicode_(s)
    elif isinstance(s, bytes):
        s = s.decode('utf-8')
    if not s or any(c not in safe_shell_chars for c in s):
        return '"%s"' % (s.replace('\\', '\\\\')
                          .replace('"', '\\"')
                          .replace('$', '\\$'))
    else:
        return s


def escape_queue(s):
    """Escapes the path to a queue, e.g. preserves ~ at the begining.
    """
    if isinstance(s, PosixPath):
        s = unicode_(s)
    elif isinstance(s, bytes):
        s = s.decode('utf-8')
    if s.startswith('~/'):
        return '~/' + shell_escape(s[2:])
    else:
        return shell_escape(s)


_re_ssh = re.compile(r'^'
                     r'(?:ssh://)?'              # 'ssh://' prefix
                     r'(?:([a-zA-Z0-9_.-]+)'     # 'user@'
                     r'(?::([^ @]+))?'           # ':password'
                     r'@)?'                      # '@'
                     r'([a-zA-Z0-9_.-]+)'        # 'host'
                     r'(?::([0-9]+))?'           # ':port'
                     r'$')


def parse_ssh_destination(destination):
    """Parses the SSH destination argument.
    """
    match = _re_ssh.match(destination)
    if not match:
        raise InvalidDestination("Invalid destination: %s" % destination)
    user, password, host, port = match.groups()
    info = {}
    if user:
        info['username'] = user
    else:
        info['username'] = getpass.getuser()
    if password:
        info['password'] = password
    if port:
        info['port'] = int(port)
    info['hostname'] = host

    return info


def destination_as_string(destination):
    if 'password' in destination:
        user = '%s:%s' % (destination['username'], destination['password'])
    else:
        user = destination['username']

    if destination.get('port', 22) != 22:
        return 'ssh://%s@%s:%d' % (user,
                                   destination['hostname'],
                                   destination['port'])
    else:
        return 'ssh://%s@%s' % (user,
                                destination['hostname'])


class ServerLogger(object):
    """Adapter getting bytes from the server's output and handing them to log.
    """
    logger = logging.getLogger('tej.server')

    def __init__(self):
        self.data = []

    def append(self, data):
        self.data.append(data)

    def done(self):
        if self.data:
            data = b''.join(self.data)
            data = data.decode('utf-8', 'replace')
            data = data.rstrip()
            self.message(data)
            self.data = []

    def message(self, data):
        self.logger.info(data)


JOB_ID_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" \
               "abcdefghijklmnopqrstuvwxyz" \
               "0123456789_-+=@%:.,"


def check_jobid(job_id):
    if not all(c in JOB_ID_CHARS for c in job_id):
        raise ValueError("Invalid job identifier")


class RemoteQueue(object):
    JOB_DONE = 'finished'
    JOB_RUNNING = 'running'
    JOB_INCOMPLETE = 'incomplete'
    JOB_CREATED = 'created'

    PROTOCOL_VERSION = 0, 2

    def __init__(self, destination, queue,
                 setup_runtime=None, need_runtime=None):
        """Creates a queue object, that represents a job queue on a server.

        :param destination: The address of the server, used to SSH into it.
        :param queue: The pathname of the queue on the remote server. Something
        like "~/.tej" is usually adequate. This will contain both the job info
        and files, and the scripts used to manage it on the server side.
        :param setup_runtime: The name of the runtime to deploy on the server
        if the queue doesn't already exist. If None (default), it will
        auto-detect what is appropriate (currently, `pbs` if the ``qsub``
        command is available), and fallback on `default`. If `need_runtime` is
        set, this should be one of the accepted values.
        :param need_runtime: A list of runtime names that are acceptable. If
        the queue already exists on the server and this argument is not None,
        the installed runtime will be matched against it, and a failure will be
        reported if it is not one of the provided values.
        """
        if isinstance(destination, string_types):
            self.destination = parse_ssh_destination(destination)
        else:
            if 'hostname' not in destination:
                raise InvalidDestination("destination dictionary is missing "
                                         "hostname")
            self.destination = destination
        if setup_runtime not in (None, 'default', 'pbs'):
            raise ValueError("Selected runtime %r is unknown" % setup_runtime)
        self.setup_runtime = setup_runtime
        if need_runtime is not None:
            self.need_runtime = set(need_runtime)
        else:
            self.need_runtime = None
        self.queue = PosixPath(queue)
        self._ssh = None
        self._connect()

    def server_logger(self):
        """Handles messages from the server.

        By default, uses getLogger('tej.server').warning(). Override this in
        subclasses to provide your own mechanism.
        """
        return ServerLogger()

    @property
    def destination_string(self):
        return destination_as_string(self.destination)

    def _ssh_client(self):
        """Gets an SSH client to connect with.
        """
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
        return ssh

    def _connect(self):
        """Connects via SSH.
        """
        ssh = self._ssh_client()
        logger.debug("Connecting with %s",
                     ', '.join('%s=%r' % (k, v if k != "password" else "***")
                               for k, v in iteritems(self.destination)))
        ssh.connect(**self.destination)
        logger.debug("Connected to %s", self.destination['hostname'])
        self._ssh = ssh

    def get_client(self):
        """Gets the SSH client.

        This will check that the connection is still alive first, and reconnect
        if necessary.
        """
        if self._ssh is None:
            self._connect()
            return self._ssh
        else:
            try:
                chan = self._ssh.get_transport().open_session()
            except (socket.error, paramiko.SSHException):
                logger.warning("Lost connection, reconnecting...")
                self._ssh.close()
                self._connect()
            else:
                chan.close()
            return self._ssh

    def get_scp_client(self):
        return scp.SCPClient(self.get_client().get_transport())

    def _call(self, cmd, get_output):
        """Calls a command through the SSH connection.

        Remote stderr gets printed to this program's stderr. Output is captured
        and may be returned.
        """
        server_err = self.server_logger()

        chan = self.get_client().get_transport().open_session()
        try:
            logger.debug("Invoking %r%s",
                         cmd, " (stdout)" if get_output else "")
            chan.exec_command('/bin/sh -c %s' % shell_escape(cmd))
            output = b''
            while True:
                r, w, e = select.select([chan], [], [])
                if chan not in r:
                    continue  # pragma: no cover
                recvd = False
                while chan.recv_stderr_ready():
                    data = chan.recv_stderr(1024)
                    server_err.append(data)
                    recvd = True
                while chan.recv_ready():
                    data = chan.recv(1024)
                    if get_output:
                        output += data
                    recvd = True
                if not recvd and chan.exit_status_ready():
                    break
            output = output.rstrip(b'\r\n')
            return chan.recv_exit_status(), output
        finally:
            server_err.done()
            chan.close()

    def check_call(self, cmd):
        """Calls a command through SSH.
        """
        ret, _ = self._call(cmd, False)
        if ret != 0:  # pragma: no cover
            raise RemoteCommandFailure(command=cmd, ret=ret)

    def check_output(self, cmd):
        """Calls a command through SSH and returns its output.
        """
        ret, output = self._call(cmd, True)
        if ret != 0:  # pragma: no cover
            raise RemoteCommandFailure(command=cmd, ret=ret)
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
            '    cd %(queue)s; echo "dir"; cat version; pwd; '
            'elif [ -f %(queue)s ]; then '
            '    cat %(queue)s; '
            'else '
            '    echo no; '
            'fi' % {
                'queue': escape_queue(queue)})
        if answer == b'no':
            if depth > 0:
                logger.debug("Broken link at depth=%d", depth)
            else:
                logger.debug("Path doesn't exist")
            return None, depth
        elif answer.startswith(b'dir\n'):
            version, runtime, path = answer[4:].split(b'\n', 2)
            try:
                version = tuple(int(e)
                                for e in version.decode('ascii', 'ignore')
                                                .split('.'))
            except ValueError:
                version = 0, 0
            if version[:2] != self.PROTOCOL_VERSION:
                raise QueueExists(
                    msg="Queue exists and is using incompatible protocol "
                        "version %s" % '.'.join('%s' % e for e in version))
            path = PosixPath(path)
            runtime = runtime.decode('ascii', 'replace')
            if self.need_runtime is not None:
                if (self.need_runtime is not None and
                        runtime not in self.need_runtime):
                    raise QueueExists(
                        msg="Queue exists and is using explicitely disallowed "
                            "runtime %s" % runtime)
            logger.debug("Found directory at %s, depth=%d, runtime=%s",
                         path, depth, runtime)
            return path, depth
        elif answer.startswith(b'tejdir: '):
            new = queue.parent / answer[8:]
            logger.debug("Found link to %s, recursing", new)
            return self._resolve_queue(new, depth + 1)
        else:  # pragma: no cover
            logger.debug("Server returned %r", answer)
            raise RemoteCommandFailure(msg="Remote command failed in "
                                           "unexpected way")

    def _get_queue(self):
        """Gets the actual location of the queue, or None.
        """
        queue, depth = self._resolve_queue(self.queue)
        if queue is None and depth > 0:
            raise QueueLinkBroken
        logger.debug("get_queue = %s", queue)
        return queue

    def setup(self, links=None, force=False, only_links=False):
        """Installs the runtime at the target location.

        This will not replace an existing installation, unless `force` is True.

        After installation, creates links to this installation at the specified
        locations.
        """
        if not links:
            links = []

        if only_links:
            logger.info("Only creating links")
            for link in links:
                self.check_call('echo "tejdir:" %(queue)s > %(link)s' % {
                                'queue': escape_queue(self.queue),
                                'link': escape_queue(link)})
            return

        queue, depth = self._resolve_queue(self.queue)
        if queue is not None or depth > 0:
            if force:
                if queue is None:
                    logger.info("Replacing broken link")
                elif depth > 0:
                    logger.info("Replacing link to %s...", queue)
                else:
                    logger.info("Replacing existing queue...")
                self.check_call('rm -Rf %s' % escape_queue(self.queue))
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
                'queue': escape_queue(queue),
                'link': escape_queue(link)})

    def _setup(self):
        """Actually installs the runtime.
        """
        # Expands ~user in queue
        if self.queue.path[0:1] == b'/':
            queue = self.queue
        else:
            if self.queue.path[0:1] == b'~':
                output = self.check_output('echo %s' %
                                           escape_queue(self.queue))
                queue = PosixPath(output.rstrip(b'\r\n'))
            else:
                output = self.check_output('pwd')
                queue = PosixPath(output.rstrip(b'\r\n')) / self.queue
            logger.debug("Resolved to %s", queue)

        # Select runtime
        if not self.setup_runtime:
            # Autoselect
            if self._call('which qsub', False)[0] == 0:
                logger.debug("qsub is available, using runtime 'pbs'")
                runtime = 'pbs'
            else:
                logger.debug("qsub not found, using runtime 'default'")
                runtime = 'default'
        else:
            runtime = self.setup_runtime

        if self.need_runtime is not None and runtime not in self.need_runtime:
            raise ValueError("About to setup runtime %s but that wouldn't "
                             "match explicitely allowed runtimes" % runtime)

        logger.info("Installing runtime %s%s at %s",
                    runtime,
                    "" if self.setup_runtime else " (auto)",
                    self.queue)

        # Uploads runtime
        scp_client = self.get_scp_client()
        filename = pkg_resources.resource_filename('tej',
                                                   'remotes/%s' % runtime)
        scp_client.put(filename, str(queue), recursive=True)
        logger.debug("Files uploaded")

        # Runs post-setup script
        self.check_call('/bin/sh %s' % shell_escape(queue / 'commands/setup'))
        logger.debug("Post-setup script done")

        return queue

    def submit(self, job_id, directory, script=None):
        """Submits a job to the queue.

        If the runtime is not there, it will be installed. If it is a broken
        chain of links, error.
        """
        if job_id is None:
            job_id = '%s_%s_%s' % (Path(directory).unicodename,
                                   self.destination['username'],
                                   make_unique_name())
        else:
            check_jobid(job_id)

        queue = self._get_queue()
        if queue is None:
            queue = self._setup()

        if script is None:
            script = 'start.sh'

        # Create directory
        ret, target = self._call('%s %s' % (
                                 shell_escape(queue / 'commands/new_job'),
                                 job_id),
                                 True)
        if ret == 4:
            raise JobAlreadyExists
        elif ret != 0:
            raise JobNotFound("Couldn't create job")
        target = PosixPath(target)
        logger.debug("Server created directory %s", target)

        # Upload to directory
        try:
            scp_client = self.get_scp_client()
            scp_client.put(str(Path(directory)),
                           str(target),
                           recursive=True)
        except BaseException as e:
            try:
                self.delete(job_id)
            except:
                raise e
            raise
        logger.debug("Files uploaded")

        # Submit job
        self.check_call('%s %s %s %s' % (
                        shell_escape(queue / 'commands/submit'),
                        job_id, shell_escape(target),
                        shell_escape(script)))
        logger.info("Submitted job %s", job_id)
        return job_id

    def status(self, job_id):
        """Gets the status of a previously-submitted job.
        """
        check_jobid(job_id)

        queue = self._get_queue()
        if queue is None:
            raise QueueDoesntExist

        ret, output = self._call('%s %s' % (
                                 shell_escape(queue / 'commands/status'),
                                 job_id),
                                 True)
        if ret == 0:
            directory, result = output.splitlines()
            result = result.decode('utf-8')
            return RemoteQueue.JOB_DONE, PosixPath(directory), result
        elif ret == 2:
            directory = output.splitlines()[0]
            return RemoteQueue.JOB_RUNNING, PosixPath(directory), None
        elif ret == 3:
            raise JobNotFound
        else:
            raise RemoteCommandFailure(command="commands/status",
                                       ret=ret)

    def download(self, job_id, files, **kwargs):
        """Downloads files from server.
        """
        check_jobid(job_id)

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

        scp_client = self.get_scp_client()
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
        check_jobid(job_id)

        queue = self._get_queue()
        if queue is None:
            raise QueueDoesntExist

        ret, output = self._call('%s %s' % (
                                 shell_escape(queue / 'commands/kill'),
                                 job_id),
                                 False)
        if ret == 3:
            raise JobNotFound
        elif ret != 0:
            raise RemoteCommandFailure(command='commands/kill',
                                       ret=ret)

    def delete(self, job_id):
        """Deletes a job from the server.
        """
        check_jobid(job_id)

        queue = self._get_queue()
        if queue is None:
            raise QueueDoesntExist

        ret, output = self._call('%s %s' % (
                                 shell_escape(queue / 'commands/delete'),
                                 job_id),
                                 False)
        if ret == 3:
            raise JobNotFound
        elif ret == 2:
            raise JobStillRunning
        elif ret != 0:
            raise RemoteCommandFailure(command='commands/delete',
                                       ret=ret)

    def list(self):
        """Lists the jobs on the server.
        """
        queue = self._get_queue()
        if queue is None:
            raise QueueDoesntExist

        output = self.check_output('%s' %
                                   shell_escape(queue / 'commands/list'))

        job_id, info = None, None
        for line in output.splitlines():
            line = line.decode('utf-8')
            if line.startswith('    '):
                key, value = line[4:].split(': ', 1)
                info[key] = value
            else:
                if job_id is not None:
                    yield job_id, info
                job_id = line
                info = {}
        if job_id is not None:
            yield job_id, info
