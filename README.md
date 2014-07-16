Running locally
===============

Before your first run (and after big updates) you should:

1. make sure you have all the requirements installed
1. create a virtual python2 environment
1. activate it
1. initialize it
1. initialize the local sqlite3 database

On linux it can be done like so:

```sh
apt-get install python-virtualenv python-pip sqlite3
virtualenv py2
source py2/bin/activate
pip install -r requirements.local.txt
./db.py
```

To start the development server simply run `server.py` from the virtual
environment (the shebang will take care of this automatically in most systems).

```sh
./server.py
```

You can now access the app on:
http://localhost:5000

Hitting Ctrl-C on the terminal that runs the server will stop it.

Running locally, Heroku style
=============================

The virtual environment contains everything necessary to run the gunicorn
server from the Cedar stack. For this you will need to install Foreman, which
is part of the [Heroku toolbelt](https://toolbelt.heroku.com/).

Next, activate the virtual environment, and start Foreman.
```sh
source py2/bin/activate
foreman start
```

Again, the app will be available on:
http://localhost:5000

And again, hitting Ctrl-C on the terminal that runs the server will stop it.
