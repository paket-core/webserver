from setuptools import setup

setup(name='webserver',
      description='Web server for PaKeT project',
      version='1.0.0',
      url='https://github.com/paket-core/webserver',
      license='GNU GPL',
      packages=['webserver'],
      install_requires=[
          'coloredlogs==9.3.1',
          'flasgger==0.8.3',
          'Flask==1.0',
          'Flask-Limiter==1.0.1',
          'stellar-base==0.1.8.1',
      ],
      tests_require=[
          'requests'
      ],
      test_suite='tests',
      zip_safe=False)
