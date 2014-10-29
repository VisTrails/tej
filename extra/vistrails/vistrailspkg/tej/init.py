from collections import namedtuple
from tej.submission import RemoteQueue
from vistrails.core.modules.vistrails_module import Module


class Queue(Module):
    """A connection to a queue on a remote server.

    `hostname` can be a hostname or a full destination in the format:
    ``[ssh://][user@]server[:port]``, e.g. ``vistrails@nyu.edu``.
    """
    _input_ports = [('hostname', '(basic:String)'),
                    ('username', '(basic:String)',
                     {'optional': True}),
                    ('port', '(basic:Integer)',
                     {'optional': True, 'defaults': "['22']"}),
                    ('queue', '(basic:String)',
                     {'optional': True, 'defaults': "['~/.tej']"})]
    _output_ports = [('queue', '(org.vistrails.extra.tej:Queue)')]

    def compute(self):
        destination = self.get_input('hostname')
        if self.has_input('username') or self.has_input('port'):
            destination = {'hostname': destination,
                           'username': self.get_input('username'),
                           'port': self.get_input('port')}
        self.set_output('queue', RemoteQueue(destination))


JobDescr = namedtuple('JobDescr', ['queue', 'job'])


class Job(Module):
    """A reference to a job in a queue.

    You probably won't use this module directly.
    """
    _input_ports = [('id', '(basic:String)'),
                    ('queue', Queue)]
    _output_ports = [('job', '(org.vistrails.extra.tej:Job)')]

    def compute(self):
        self.set_output('job', JobDescr(queue=self.get_input('queue'),
                                        id=self.get_input('id')))


class SubmitJob(Job):
    """Starts a job on a server.

    Thanks to the suspension/job tracking mechanism, this module does much more
    than start a job. If the job is running, it will suspend again. If the job
    is finished, you can obtain files from it.
    """
    _input_ports = [('job', '(basic:Directory)'),
                    ('script', '(basic:String)',
                     {'optional': True, 'defaults': "['start.sh']"}),
                    ('id', '(basic:String)',
                     {'optional': True})]

    def update_upstream(self):
        identifier = job_from_sig OR from input_port
        check job status

    def compute(self):
        queue = self.get_input('queue')
        identifier = self.get_input('id')
        if not identifier:
            identifier = job_from_sig

        queue.submit(identifier, self.get_input('job'),
                     self.get_input('script'))


_modules = [Queue, Job, SubmitJob]
