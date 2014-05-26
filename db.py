#!./py2/bin/python

# This module, oddly enough, takes care of all the database related shite.

# Init DB
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
engine = create_engine('sqlite:///tavili.db')
session = scoped_session(sessionmaker(
    autocommit = False,
    autoflush = False,
    bind = engine
))

# Tables
Base = declarative_base()
Base.query = session.query_property()
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(80))
    email = Column(String(200))
    openid = Column(String(200))
    def __init__(self, name, email, openid):
        self.name, self.email, self.openid = name, email, openid
    def __repr__(self):
        return '<User %i %r %r %r>' % (self.id, self.name, self.email, self.openid)

# Functions
def init_db():
    Base.metadata.create_all(bind=engine)

# Leftovers from no DB version, which should be modified TODO

# A Parcel has info about the physical package and an unlimited number of attribute.
class Parcel(object):
    def __init__(self, encumbrance=0):
        self.encumbrance = encumbrance
        # Place holder
        self.attributes = {}

# A location in the world, with a lazily fetched address
from router import Router
class Location(object):
    def __init__(self, latlng, acc=None, address=None):
        self.latlng = latlng
        self.accuracy = acc
        if not address is None: self.address = address
    def __getattr__(self, name):
        if 'address' == name:
            self.address = Router.addresslookup(self.latlng)['display_name']
            return self.address
    def __str__(self, *args, **kwargs):
        return "<Location in %s>" % (self.latlng,)
    def distance(self, latlng):
        return sum((self.latlng[i] - latlng[i]) ** 2 for i in (0, 1)) ** .5
    def routeDistance(self, location):
        r = Router(self.latlng,location.latlng, 'bicycle')
        return r.getDistance()
    def routeTimeMin(self, location):
        r = Router(self.latlng,location.latlng, 'bicycle')
        return r.getTravelTimeMin()

# An Address is a fixed Location with a helpful description on how to get to it.
class Address(Location):
    def __init__(self, latlng, desc=''):
        Location.__init__(self, latlng, acc=1)
        self.desc = desc

# A Delivery is the taking of a Parcel from one Address to another.
class Delivery(object):
    STATUSES = {
        'CREATED': 'created',
        'OPEN': 'open',
        'COMMITTED': 'committed',
        'ENROUTE': 'enroute',
        'RECEIVED': 'received'
    }
    def __init__(self, parcel, source, destination):
        self.parcel = parcel
        self.source = source
        self.destination = destination
        self.status = self.STATUSES['CREATED']
    def open(self, pickup):
        self.pickup = pickup
        self.status = self.STATUSES['OPEN']
        return self
    def commit(self, courier):
        self.courier = courier
        self.status = self.STATUSES['COMMITTED']
        return self
    def pickup(self, deposit):
        self.deposit = deposit
        self.status = self.STATUSES['ENROUTE']
        return self
    def receive(self):
        self.status = self.STATUSES['RECEIVED']
        return self
    # Lazy routing initialization
    def __getattr__(self, name):
        if 'router' == name:
            self.router = Router(self.source.latlng, self.destination.latlng, 'bicycle')
            return self.router
        if 'path' == name:
            self.path = self.router.getPath()
            return self.path
        if 'time' == name:
            self.time = self.router.getTravelTimeMin()
            return self.time
    def data(self):
        try: return {
            'fromLatlng': self.source.latlng,
            'toLatlng': self.destination.latlng,
            'time': self.time,
            'path': self.path,
            'address': self.source.address
        }
        except AttributeError:
            self.__initdata()
            return self.data()

# Generate deliveries
from random import uniform
from time import time
deliveries = {
        str(i): Delivery(
            Parcel(),
            Location((uniform(31.95, 32.15), uniform(34.70, 34.90))),
            Location((uniform(31.95, 32.15), uniform(34.70, 34.90))),
        ).open(None) for i in range(20)
}

if __name__ == '__main__':
    init_db()
