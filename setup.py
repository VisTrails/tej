import os
from setuptools import setup
import sys


# pip workaround
os.chdir(os.path.abspath(os.path.dirname(__file__)))


def list_files(d, root):
    files = []
    for e in os.listdir(os.path.join(root, d)):
        if os.path.isdir(os.path.join(root, d, e)):
            files.extend(list_files('%s/%s' % (d, e), root))
        elif not e.endswith('.pyc'):
            files.append('%s/%s' % (d, e))
    return files


with open('README.rst') as fp:
    description = fp.read()
req = ['paramiko', 'rpaths', 'scp']
if sys.version_info < (2, 7):
    req.append('argparse')
setup(name='tej',
      version='0.5',
      packages=['tej'],
      package_data={'tej': list_files('remotes', 'tej')},
      entry_points={
          'console_scripts': [
              'tej = tej.main:main']},
      install_requires=req,
      description="Trivial Extensible Job-submission system",
      author="Remi Rampin",
      author_email='remirampin@gmail.com',
      maintainer="Remi Rampin",
      maintainer_email='remirampin@gmail.com',
      url='https://github.com/VisTrails/tej',
      long_description=description,
      license='BSD',
      keywords=['tej', 'job', 'submission', 'queue', 'batch', 'ssh', 'server',
                'pbs', 'qsub'],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: Information Technology',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 3',
          'Topic :: Internet',
          'Topic :: Scientific/Engineering',
          'Topic :: System :: Distributed Computing',
          'Topic :: System :: Shells',
          'Topic :: Utilities'])
