Trivial Extensible Job-submission system
========================================

Clusters typically come with job-submission and queueing systems. These systems
handle a queue of jobs, which might spawn multiple nodes, have a priorities,
dependencies, expected runtimes, deadlines...

Tej doesn't aim at doing any of that. It just allows you to submit a job to a
single server, that will run it immediately, and allow you to check its status
and get its results later on.

Of course, tej is extensible, which allows you to add some queueing and
scheduling abilities should you want to.

The goal of tej is to be usable without having to configure the server
beforehand; it will setup the structure it needs on the server on the first run
if necessary (in its simplest form, a ~/.tej directory on the server, that will
contain the jobs).

Usage (projected)
-----------------

Sets up tej on the server (optional, else it gets setup on the first run, with
default options)::

    $ tej setup user@server.hostna.me \
        --queue /scratch/tejqueue \
        --make-link ~/.tej \
        --plugin=default

This takes a destination to SSH into, the location of tej's directory (there
can be several on a server; by default, ``~/.tej`` is used), ``--make-link``
creates a link so that future invocations will be redirected to
``/scract/tejqueue``, and ``--plugin`` selects which plugins to setup on the
server (since tej is extensible, other scheduling/running subsystems might be
written).

Submit a simple job::

    $ tej submit user@server.hostna.me myjobdir
    Job submitted as:
    myjobdir_user_123456

Here myjobdir is assumed to have the default layout, and no metadata is added.
The directory will be uploaded in its entirety, and ``start.sh`` will be run.

The optional JSON file ``tej.json`` can contain metadata, such as maximum run
time, what to do with the standard/error outputs, when to run the job, and
email addresses or webhook to notify on completion.

Submit a job explicitely::

    $ tej submit user@server.hostna.me --queue=/scratch/tejqueue \
        --id example_job \
        --directory myjobdir \
        --script bin/jobinit
    Job submitted as:
    example_job

In this form, additional metadata is provided on the command-line; it is used
to override the default directory structure and metadata.

Of course none of this is implemented yet, so it's all subject to change. Feel
free to give me your opinion on these or direct me your feature requests.

Name
----

"tej" is French slang for throwing/casting. It's intended here to be used as a
verb ("let me tej it to the server...", "Is it done yet? I tej'd that
yesterday!").
