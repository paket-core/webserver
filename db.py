#!./py2/bin/python
# -*- coding: utf-8 -*-

# This module, oddly enough, takes care of all the database related shite.

dbfilename = 'tavili.db'
dbscheme = 'sqlite'

from sqlalchemy import(
    Column, create_engine, event, exc, ForeignKey, Integer, String
)
from sqlalchemy.types import PickleType, Float, LargeBinary
from sqlalchemy.orm import scoped_session, sessionmaker, mapper, reconstructor
from sqlalchemy.ext.declarative import declarative_base
engine = create_engine("%s:///%s" % (dbscheme, dbfilename))
session = scoped_session(sessionmaker(
    autocommit = False,
    autoflush = False,
    bind = engine
))

@event.listens_for(mapper, 'init')
def auto_add(target, args, kwargs):
    session.add(target)

# Tables
Base = declarative_base()
Base.query = session.query_property()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(80))
    email = Column(String(200))
    phone = Column(String(20))
    openid = Column(String(200))
    balance = Column(Integer)
    def __init__(self, name, email, phone, openid):
        self.name, self.email, self.phone, self.openid = (
            name, email, phone, openid
        )
        self.balance = 100

# A Location is just that, but in the future it will have hierarchy as well
from router import Router, getlatlng
class Location(Base):
    __tablename__ = 'locations'
    id = Column(Integer, primary_key=True)
    lat = Column(Float)
    lng = Column(Float)
    address = Column(String(200))
    accuracy = Column(Float)
    description = Column(String(200))
    name = Column(String(200))
    parentid = Column(Integer, ForeignKey('locations.id'))
    def __init__(self, **kwargs):
        if 'latlng' in kwargs:
            self.lat, self.lng = self.latlng = kwargs['latlng']
        elif 'address' in kwargs:
            self.lat, self.lng = self.latlng = getlatlng(kwargs['address'])[1]
            self.address = kwargs['address']
        else:
            raise ValueError('Can\'t create location without latlng or address')
        for name in 'accuracy', 'description', 'name', 'parentid':
            if name in kwargs: self.accuracy = getattr(kwargs, name)
    @reconstructor
    def reconstruct(self):
        self.latlng = self.lat, self.lng
        if self.parentid:
            self.parent = Location.query.filter_by(id=self.parentid).one()
    def __getattr__(self, name):
        if 'address' == name:
            self.address = Router.addresslookup(self.latlng)['display_name']
            return self.address
        return Base.__getattr__(self, key)
    def __repr__(self):
        return "<Location in %s>" % (self.latlng,)
    def distance(self, latlng):
        return sum(
            (float(self.latlng[i]) - float(latlng[i])) ** 2 for i in (0, 1)
        ) ** .5
    def routeDistance(self, location, means='bicycle'):
        r = Router(self.latlng, location.latlng, means)
        return r.getDistance()
    def routeTimeMin(self, location, means='bicycle'):
        r = Router(self.latlng, location.latlng, means)
        return r.getTravelTimeMin()

# Alternative place names.
class names(Base):
    __tablename__ = 'names'
    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    locationid = Column(Integer, ForeignKey('locations.id'))
    def __init__(self, name, location):
        self.name = name
        self.locationid = location.id

# A physical package
class Parcel(Base):
    __tablename__ = 'parcels'
    id = Column(Integer, primary_key=True)
    def __init__(self, encumbrance=0):
        self.encumbrance = encumbrance
        # Place holder. TODO add encoder and QR and shit.
        self.attributes = {}
    @reconstructor
    def reconstruct(self):
        self.location = Location.query.filter_by(id=self.locationid).one()

# TODO Pickup windows and all that shit should be in DB as well.

# A Delivery is the taking of a Parcel from one Location to another.
class Delivery(Base):
    __tablename__ = 'deliveries'
    id = Column(Integer, primary_key=True)

    senderid = Column(Integer, ForeignKey('users.id'))
    parcelid = Column(Integer, ForeignKey('parcels.id'))
    toid = Column(Integer, ForeignKey('locations.id'))
    fromid = Column(Integer, ForeignKey('locations.id'))
    reward = Column(Integer, default=0)
    penalty = Column(Integer, default=0)
    masterid = Column(Integer, ForeignKey('deliveries.id'))

    courierid = Column(Integer, ForeignKey('users.id'))
    proof = Column(LargeBinary)

    status = Column(Integer)
    STATUSES = {
        'CREATED': 0,
        'TAKEN': 1,
        'RECEIVED': 2
    }

    ERRORS = {
        'NOTFOUND': 'Delivery not found',
        'AUTH': 'User unauthorized to view delivery',
        'FUNDS': 'User has insufficient funds to take delivery'
    }

    @staticmethod
    def Get(deliveryid):
        try: return Delivery.query.filter_by(id=deliveryid).one()
        except exc.SQLAlchemyError:
            raise ValueError(Delivery.ERRORS['NOTFOUND'])

    def __init__(
        self, sender, parcel, from_, to_, reward, penalty, master=None
    ):
        self.senderid, self.parcelid = sender.id, parcel.id
        self.fromid, self.toid = from_.id, to_.id
        self.reward, self.penalty = reward, penalty
        self.status = Delivery.STATUSES['CREATED']
        if master is not None: self.masterid = master.id

    @reconstructor
    def reconstruct(self):
        # FIXME This should be done with relationship, I think
        self.from_ = Location.query.filter_by(id=self.fromid).one()
        self.to_ = Location.query.filter_by(id=self.toid).one()
        self.sender = User.query.filter_by(id=self.senderid).one()
        if self.courierid:
            self.courier = User.query.filter_by(id=self.courierid).one()
        if self.masterid:
            self.master = Delivery.query.filter_by(id=self.masterid).one()

        self.jsonable = {
            'status': self.status,
            'fromlatlng': self.from_.latlng,
            'tolatlng': self.to_.latlng,
            'fromaddress': self.from_.address,
            'toaddress': self.to_.address,
            'time': self.time,
            'path': self.path,
            'reward': self.reward,
            'penalty': self.penalty
        }

    # Lazy routing initialization
    def __getattr__(self, name):
        if 'router' == name:
            self.router = Router(self.from_.latlng, self.to_.latlng, 'bicycle')
            return self.router
        if 'path' == name:
            self.path = self.router.getPath()
            return self.path
        if 'time' == name:
            self.time = self.router.getTravelTimeMin()
            return self.time
        return Base.__getattr__(self, key)

    # Give user appropriate delivery data and recommend possible operation.
    def show(self, user):
        if self.status == Delivery.STATUSES['CREATED']:
            if user is not self.sender: op = 'take'
            else: op = 'cancel'
        elif user is self.courier: op = 'drop'
        elif user is not self.sender:
            raise ValueError(Delivery.ERRORS['AUTH'])
        return op, self

    # Create a delivery that will bring self to you.
    def pull(self, courier, to_, reward, addedpenalty):
        if self.status != Delivery.STATUSES['CREATED']:
            raise ValueError(Delivery.ERRORS['AUTH'])
        Delivery(
            courier,
            self.parcel,
            self.from_,
            to_,
            reward,
            self.penalty + addedpenalty,
            self
        )
        session.commit()

    # Take a delivery from a location.
    def take(self, courier):
        if self.status != Delivery.STATUSES['CREATED']:
            raise ValueError(Delivery.ERRORS['AUTH'])
        if self.penalty > courier.balance:
            raise ValueError(Delivery.ERRORS['FUNDS'])

        courier.balance -= self.penalty
        session.add(courier)

        try:
            self.master.courier = self.sender
            self.master.courierid = self.senderid
            self.master.status = Delivery.STATUSES['TAKEN']
            session.add(self.master)
        except AttributeError: pass

        self.courier = courier
        self.courierid = courier.id
        self.status = Delivery.STATUSES['TAKEN']
        session.add(self)

        session.commit()
        return self

    # Drop a delivery at a location.
    def drop(self, courier, proof):
        if(
            self.status != Delivery.STATUSES['TAKEN'] or
            self.courier != courier
        ): raise ValueError(Delivery.ERRORS['AUTH'])

        try:
            self.sender.balance -= self.master.penalty
            session.add(self.sender)
        except AttributeError: pass

        self.proof = proof
        self.status = Delivery.STATUSES['RECEIVED']
        session.add(self)

        courier.balance += self.penalty + self.reward
        session.add(courier)

        session.commit()

def init_db():
    from os.path import isfile
    if isfile(dbfilename):
        if 'y' != raw_input('Delete database and create a new one? (y/N): '):
            from sys import exit
            exit(0)
        from os import remove
        remove(dbfilename)

    Base.metadata.create_all(bind=engine)

    from random import uniform, sample
    locations = [
        Location(address=u'ביצרון 8, תל אביב'),
        Location(address=u'מגדלי עזריאלי'),
        Location(address=u'רבי נחמן מברסלב 6, יפו'),
        Location(address=u'הרב אלנקווה 6, תל אביב'),
        Location(address=u'הברזל 32, תל אביב'),
    ]
    parcels = [Parcel() for i in range(10)]
    session.commit()
    deliveries = []
    for parcel in parcels:
        from_, to_ = sample(locations, 2)
        deliveries.append(Delivery(
            type('mockuser', (object,), {'id': 1})(),
            parcel,
            from_,
            to_,
            uniform(5, 50),
            uniform(100, 1000)
        ))
    session.commit()

    if isfile('me.sql'):
        from subprocess import call
        call(['sqlite3', '-init', 'me.sql', 'tavili.db', '.exit'])

if __name__ == '__main__':
    init_db()
