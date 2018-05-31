"""PaKeT logger."""
from setuptools import setup

setup(name='webserver',
      description='Web server for PaKeT project',
      version='1.0.0',
      url='https://github.com/paket-core/webserver',
      license='GNU GPL',
      packages=['webserver'],
      install_requires=[
          'flasgger==0.8.3',
          'Flask==1.0.2',
          'Flask-Limiter==1.0.1',
      ],
      test_suite='tests',
      zip_safe=False)
