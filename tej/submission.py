from __future__ import unicode_literals

import logging
import paramiko
import re
import sys


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
        self.queue = queue
        self.ssh = None
        self._connect()

    def _connect(self):
        try:
            info = parse_ssh_destination(self.destination)
        except ValueError, e:
            logging.critical(e)
            sys.exit(1)

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
        self.ssh.connect(**info)

    def setup(self, links):
        pass

    def submit(self, job_id, directory, script=None):
        pass

    def status(self, job_id):
        pass

    def download(self, job_id, files):
        pass

    def kill(self, job_id):
        pass

    def delete(self, job_id):
        pass
