import os
from setuptools import setup
import sys


# pip workaround
os.chdir(os.path.abspath(os.path.dirname(__file__)))


with open('README.rst') as fp:
    description = fp.read()
req = []
if sys.version_info < (2, 7):
    req.append('argparse')
setup(name='tej-python',
      version='0.1',
      packages=['tej'],
      entry_points={
          'console_scripts': [
              'tej = tej.main:main']},
      install_requires=req,
      description="Trivial Extensible Job-submission system",
      author="Remi Rampin",
      author_email='remirampin@gmail.com',
      maintainer="Remi Rampin",
      maintainer_email='remirampin@gmail.com',
      url='https://github.com/remram44/tej',
      long_description=description,
      license='BSD',
      keywords=['tej', 'job', 'submission', 'batch', 'ssh', 'server'],
      classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'Environment :: Console',
          'Intended Audience :: Information Technology',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: BSD License',
          'Operating System :: POSIX',
          'Topic :: Internet',
          'Topic :: Scientific/Engineering',
          'Topic :: System :: Distributed Computing',
          'Topic :: System :: Shells',
          'Topic :: Utilities'])
