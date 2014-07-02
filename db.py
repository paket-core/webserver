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

# TODO Pickup windows and all that shit should be in DB as well.

# An indexed table of delivery pull relationships.
class Pulls(Base):
    __tablename__ = 'pulls'
    pullerid = Column(Integer, ForeignKey('deliveries.id'), primary_key=True)
    pulleeid = Column(Integer, ForeignKey('deliveries.id'), index=True)
    def __init__(self, puller, pullee):
        self.pullerid, self.pulleeid = puller.id, pullee.id
    @reconstructor
    def reconstruct(self):
        self.puller = Delivery.query.filter_by(id=self.pullerid).one()
        self.pullee = Delivery.query.filter_by(id=self.pulleeid).one()

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

    courierid = Column(Integer, ForeignKey('users.id'))
    proof = Column(LargeBinary)

    status = Column(Integer)
    STATUSES = {
        'CREATED': 0,
        'TAKEN': 1,
        'RECEIVED': 2,
        'CANCELED': 3
    }

    ERRORS = {
        'NOTFOUND': 'Delivery not found',
        'AUTH': 'User unauthorized to view delivery',
        'FUNDS': 'User has insufficient funds'
    }

    def __init__(
        self, sender, parcel, from_, to_, reward, penalty
    ):
        if reward > sender.balance: raise ValueError(Delivery.ERRORS['FUNDS'])
        sender.balance -= reward
        session.add(sender)
        session.commit()

        self.senderid, self.parcelid = sender.id, parcel.id
        self.fromid, self.toid = from_.id, to_.id
        self.reward, self.penalty = reward, penalty
        self.status = Delivery.STATUSES['CREATED']

    @reconstructor
    def reconstruct(self):
        # FIXME This should be done with relationship, I think
        self.from_ = Location.query.filter_by(id=self.fromid).one()
        self.to_ = Location.query.filter_by(id=self.toid).one()
        self.sender = User.query.filter_by(id=self.senderid).one()
        self.parcel = Parcel.query.filter_by(id=self.parcelid).one()
        if self.courierid:
            self.courier = User.query.filter_by(id=self.courierid).one()

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

    @staticmethod
    def Create(sender, parcel, from_, to_, reward, penalty):
        from_ = Location(address=from_)
        to_ = Location(address=to_)

        if parcel is None:
            parcel = Parcel()

        delivery = Delivery(sender, parcel, from_, to_, reward, penalty)
        session.commit()

        return delivery

    @staticmethod
    def Get(deliveryid):
        try: return Delivery.query.filter_by(id=deliveryid).one()
        except exc.SQLAlchemyError:
            raise ValueError(Delivery.ERRORS['NOTFOUND'])

    # Get list of pullers
    def pullers(self):
        return(
            pull.puller
            for pull in Pulls.query.filter_by(pulleeid=self.id).all()
        )

    # Get pullee, or None
    def pullee(self):
        try: return Pulls.query.filter_by(pullerid=self.id).one().pullee
        except exc.SQLAlchemyError: return None

    # Give user appropriate delivery data and recommend possible operation.
    def show(self, user):
        if self.status == Delivery.STATUSES['CREATED']:
            if user is not self.sender: op = 'take'
            else: op = 'cancel'
        elif user is self.courier:
            if self.status == Delivery.STATUSES['TAKEN']:
                # If self has a TAKEN puller, it can't be dropped
                for puller in self.pullers():
                    if puller.status == Delivery.STATUSES['TAKEN']:
                        return None, self
                op = 'drop'
        elif user is not self.sender:
            raise ValueError(Delivery.ERRORS['AUTH'])
        try: return op, self
        except UnboundLocalError: return None, self

    # Create a delivery that will bring self to you.
    def pull(self, courier, to_, reward, addedpenalty):
        if self.status != Delivery.STATUSES['CREATED']:
            raise ValueError(Delivery.ERRORS['AUTH'])

        to_ = Location(address=to_)

        delivery = Delivery(
                courier,
                self.parcel,
                self.from_,
                to_,
                reward,
                self.penalty + addedpenalty,
                )
        Pulls(delivery, self)
        session.commit()

    # Take a delivery from a location.
    def take(self, courier, proxy=None):
        if self.status != Delivery.STATUSES['CREATED']:
            raise ValueError(Delivery.ERRORS['AUTH'])
        if self.penalty > courier.balance:
            raise ValueError(Delivery.ERRORS['FUNDS'])

        courier.balance -= self.penalty
        session.add(courier)

        self.courier = courier
        self.courierid = courier.id
        self.status = Delivery.STATUSES['TAKEN']
        session.add(self)

        # If self has a pullee, take it.
        try: self.pullee().take(self.sender, courier)
        except AttributeError: pass

        # Cancel open deliveries that pull self.
        for puller in self.pullers():
            if puller.status == Delivery.STATUSES['CREATED']:
                puller.cancel()

        session.commit()
        return self

    # Drop a delivery at a location.
    def drop(self, courier, proof):
        if(
            self.status != Delivery.STATUSES['TAKEN'] or
            self.courier != courier
        ): raise ValueError(Delivery.ERRORS['AUTH'])

        # If self has a TAKEN puller, it can't be dropped
        for puller in self.pullers():
            if puller.status == Delivery.STATUSES['TAKEN']:
                raise ValueError(Delivery.ERRORS['AUTH'])

        self.proof = proof
        self.status = Delivery.STATUSES['RECEIVED']
        session.add(self)

        courier.balance += self.penalty + self.reward
        session.add(courier)

        session.commit()

    # Cancel a delivery.
    def cancel(self):
        if self.status != Delivery.STATUSES['CREATED']:
            raise ValueError(Delivery.ERRORS['AUTH'])

        # Cancel pullers.
        for puller in self.pullers():
            puller.cancel()

        self.sender.balance += self.reward
        session.add(self.sender)

        self.status = Delivery.STATUSES['CANCELED']
        session.add(self)

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

    if isfile('me.sql'):
        from subprocess import call
        call(['sqlite3', '-init', 'me.sql', 'tavili.db', '.exit'])

    from random import sample, randrange
    locations = [
        Location(address=u'ביצרון 8, תל אביב'),
        Location(address=u'מגדלי עזריאלי'),
        Location(address=u'רבי נחמן מברסלב 6, יפו'),
        Location(address=u'הרב אלנקווה 6, תל אביב'),
        Location(address=u'הברזל 32, תל אביב')
    ]

    sender = User.query.first()
    if sender is None:
        sender = User('stam', 'stam@blam', '111', 'none')
        sender.balance = 10000

    for parcel in [Parcel() for i in range(10)]:
        from_, to_ = sample(locations, 2)
        Delivery(
            sender,
            parcel,
            from_,
            to_,
            randrange(5, 50),
            randrange(100, 200)
        )
    session.commit()

if __name__ == '__main__':
    #test()
    init_db()
