tavili
======

IMPORTANT NOTE:

I had to downgrade us to python2, so I suggest we use a virtual python env till
we figure out what's going on.

Before your first run you should do the following:

```sh
virtualenv py2
source py2/bin/activate
pip install Flask-openID
pip install sqlalchemy
./db.py
```

I modified the shabangs to use the virtualenv, so from that poing on you can
simply run server.py and browse to:
http://localhost:8080
