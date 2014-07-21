Running locally
===============

Before your first run (and after big updates) you should:

1. make sure you have all the requirements installed
1. initialize the local sqlite3 database

On linux it can be done like so:

```sh
apt-get install python-pip sqlite3
pip install flask-login flask-sqlalchemy
./db.py
```

To start the development server simply run `server.py` and browse to:

http://localhost:5000

Hitting Ctrl-C on the terminal that runs the server will stop it.
