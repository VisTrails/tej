from __future__ import unicode_literals

import logging
import paramiko
import re
import pkg_resources
from rpaths import PosixPath
import scp
import string
import sys


logger = logging.getLogger('tej')


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
    match = _re_ssh.match(destination)
    if not match:
        raise ValueError("Invalid destination: %s" % destination)
    user, host, port = match.groups()
    info = {}
    if user:
        info['username'] = user
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
        try:
            info = parse_ssh_destination(self.destination)
        except ValueError as e:
            logger.critical(e)
            sys.exit(1)

        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
        self.ssh.connect(**info)
        logger.debug("Connected to %s", info['hostname'])

    def _check_call(self, cmd):
        chan = self.ssh.get_transport().open_session()
        try:
            logger.debug("Invoking %r", cmd)
            chan.exec_command('/bin/sh -c %s' % shell_escape(cmd))
            assert chan.recv_exit_status() == 0
        finally:
            chan.close()

    def _check_output(self, cmd):
        chan = self.ssh.get_transport().open_session()
        try:
            logger.debug("Invoking %r (stdout)", cmd)
            chan.exec_command('/bin/sh -c %s' % shell_escape(cmd))
            output = b''
            while True:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                output += data
            output = output.rstrip(b'\r\n')
            assert chan.recv_exit_status() == 0
        finally:
            chan.close()
        logger.debug("Output: %r", output)
        return output

    def _resolve_queue(self, queue, depth=0):
        if depth == 0:
            logger.debug("resolve_queue(%s)", queue)
        answer = self._check_output(
                'if [ -d %(queue)s ]; then '
                '    cd %(queue)s; echo "dir: $(pwd)"; '
                'elif [ -f %(queue)s ]; then '
                '    cat %(queue)s; '
                'else '
                '    echo no; '
                'fi' % {
                    'queue': shell_escape(bytes(queue))})
        if answer == b'no':
            logger.debug("Broken link at depth=%d", depth)
            return None, depth
        elif answer.startswith(b'dir: '):
            new = PosixPath(answer[5:])
            logger.debug("Found directory at %s, depth=%d", new, depth)
            return new, depth
        elif answer.startswith(b'tejdir: '):
            new = queue.parent / answer[8:]
            logger.debug("Found link to %s, recursing", new)
            return self._resolve_queue(new, depth + 1)

    def _get_queue(self):
        queue, depth = self._resolve_queue(self.queue)
        if queue is None and depth > 0:
            logger.critical("Queue link chain is broken")
            sys.exit(1)
        logger.debug("get_queue = %s", queue)
        return queue

    def setup(self, links=None, force=False):
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
                self._check_call('rm -Rf %s' % shell_escape(str(self.queue)))
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
            self._check_call('echo "tejdir:" %(queue)s > %(link)s' % {
                    'queue': shell_escape(str(queue)),
                    'link': shell_escape(link)})

    def _setup(self):
        logger.debug("Installing runtime at %s", self.queue)

        # Expands ~user in queue
        output = self._check_output('echo %s' % shell_escape(str(self.queue)))
        queue = PosixPath(output.rstrip(b'\r\n'))
        logger.debug("Resolved to %s", queue)

        # Uploads runtime
        scp_client = scp.SCPClient(self.ssh.get_transport())
        filename = pkg_resources.resource_filename('tej', 'remotes/default')
        scp_client.put(filename, str(queue), recursive=True)
        logger.debug("Files uploaded")

        # Runs post-setup script
        self._check_call('/bin/sh %s' % (queue / 'commands' / 'setup'))
        logger.debug("Post-setup script done")

        return queue

    def submit(self, job_id, directory, script=None):
        queue = self._get_queue()

        if queue is None:
            queue = self._setup()

        # TODO : submit

    def status(self, job_id):
        # TODO : status
        raise NotImplementedError("status")

    def download(self, job_id, files):
        # TODO : download
        raise NotImplementedError("download")

    def kill(self, job_id):
        # TODO : kill
        raise NotImplementedError("kill")

    def delete(self, job_id):
        # TODO : delete
        raise NotImplementedError("delete")
