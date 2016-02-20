What is this?
-------------

tej is an easy-to-use job-submission system. It allows you to start scripts or program on remote machine while keeping track of their status and results.

It is a good replacement for running scripts inside `screen(1) <https://www.gnu.org/software/screen/manual/screen.html>`__ sessions via SSH for example, and can integrate with many backends easily (such as PBS).

It is meant to be easy to use from scripts, both batch or Python, and will run fine on Windows client.

What does it do?
----------------

Clusters typically come with job-submission and queueing systems. These systems handle a queue of jobs, which might spawn multiple nodes, have a priorities, dependencies, expected runtimes, deadlines...

Tej doesn't aim at doing any of that. It just allows you to submit a job to a single server, and allow you to check its status and get its results later on. The default runtime simply starts running jobs as soon as they are submitted; if PBS is available on the server, then tej will use that to run the jobs.

Of course, tej is extensible, which allows you to add some queueing and scheduling abilities should you want to (by writing a 'runtime' with more capabilities').

The goal of tej is to be usable without having to configure the server beforehand; it will setup the structure it needs on the server on the first run if necessary (in its simplest form, a ~/.tej directory on the server, that will contain the jobs).

tej is used by the VisTrails scientific workflow management system to run remote jobs. A VisTrails module signature is mapped to a tej job name, so that the job can be started if it doesn't exist, waited on if it's running, and its results simply retrieved when it's done (from any client's machine).

Command-line usage
------------------

Sets up tej on the server (optional, else it gets setup on the first run, with default options)::

    $ tej setup user@server.hostna.me \
        --queue /scratch/tejqueue \
        --make-link ~/.tej \
        --runtime default

This takes a destination to SSH into, the location of tej's directory (there can be several on a server; by default, ``~/.tej`` is used), ``--make-link`` creates a link so that the default ``/.tej`` redirects to ``/scratch/tejqueue``, and ``--runtime`` selects which runtime to setup on the server (``default`` starts submitted jobs right away using nohup, ``pbs`` hands them to ``qsub``, ...).

Submit a simple job::

    $ tej submit user@server.hostna.me myjobdir
    Job submitted as:
    myjobdir_user_123456

Here `myjobdir` is assumed to have the default layout, and no metadata is added. The directory will be uploaded in its entirety, and ``start.sh`` will be run.

Submit a job explicitely::

    $ tej submit user@server.hostna.me --queue=/scratch/tejqueue \
        --id example_job \
        --script bin/jobinit \
        myjobdir
    Job submitted as:
    example_job

Get the status of a job::

    $ tej status user@server.hostna.me --id myjobdir_user_123456
    Job is still running (1:28:57)
    $ tej status user@server.hostna.me --queue=/scratch/tejqueue \
        --id example_job
    Job is finished (1:30:01)
    $ tej status user@server.hostna.me --id myjobdir_user_567890
    No job 'myjobdir_user_567890'

Download the output from a finished job::

    $ tej download user@server.hostna.me --id myjobdir_user_123456 \
        output/log.txt
    $ tej download user@server.hostna.me --id myjobdir_user_123456 \
        results.csv view.png input.bin

Note that there is no need for the file to be an *output*. The files are downloaded to the current directory.

Kill a running job::

    $ tej kill user@server.hostna.me --id example_job
    Job 'example_job' has already completed
    $ tej kill user@server.hostna.me --id myjobdir_user_123456
    Job 'myjobdir_user_123456' killed
    $ tej kill user@server.hostna.me --id myjobdir_user_567890
    No job 'myjobdir_user_567890'

Cleanup a finished job::

    $ tej delete user@server.hostna.me --id example_job
    Deleted job 'example_job'

Name
----

"tej" stands for Trivial Extensible Job-submission system.

"tej" ``/tɛʒ/`` is also French slang for throwing/casting. It's intended here to be used as a verb ("let me tej it to the server...", "Is it done yet? I tej'd that yesterday!").

Probably not the best name, but it wasn't taken, and it's short.

Disclaimer
----------

Note that this software is still beta. While it is already in use by VisTrails, it is still likely to evolve. Feel free to give me your opinion, use cases, or address me your feature requests/patches on Github.
