from setuptools import setup


setup(name='vistrails-tej',
      version='0.1',
      packages=['vistrailspkg', 'vistrailspkg.tej'],
      entry_points={
        'vistrails.packages': ['tej = vistrailspkg.tej']},
      namespace_packages=['vistrailspkg'],
      install_requires=['tej-python>=0.1'],
      description="VisTrails package for tej",
      zip_safe=False,
      author="Remi Rampin",
      author_email='remirampin@gmail.com',
      url='https://github.com/remram44/tej',
      license='BSD',
      keywords=['tej', 'job', 'submission', 'queue', 'batch', 'ssh', 'server',
                'vistrails', 'nyu'],
      classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'Environment :: Plugins',
          'Intended Audience :: Information Technology',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: BSD License',
          'Topic :: Internet',
          'Topic :: Scientific/Engineering',
          'Topic :: System :: Distributed Computing',
          'Topic :: System :: Shells',
          'Topic :: Utilities'])
