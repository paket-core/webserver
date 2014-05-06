#!/usr/bin/python3

# A parcel has info about the physical package and an unlimited number of attribute
class Parcel(object):
    def __init__(self, encumbrance):
        self.encumbrance = encumbrance
        self.attributes = {}

# A location currently only has a geo pos tuple and a distance calculator
# Any shipment is from a location and to a location
class Location(object):
    def __init__(self, geoPos):
        self.geoPos = geoPos
    def distance(self, geoPos):
        return sum((self.geoPos[i] - geoPos[i]) ** 2 for i in (0, 1)) ** .5

# An address is a fixed Location with a helpful description on how to get to it  
class Address(Location):
    def __init__(self, loc, desc = "no description provided"):
        self.loc = loc
        self.desc = desc

# A shipment is a description of a parcel, it's source and it's destination                
class Shipment(object):
    def __init__(self, parcel, sourceLoc, destLoc):
        self.sourceLoc, self.destLoc = sourceLoc, destLoc

# A transfer is the actual transference of a Shipment. It's status, and location. 
# Each Shipment is performed by a single or several Transfers. 
class Transfer(object):
    def __init__(self, shipment, status, currier, lastLocation):
        self.shipment = shipment
        self.status = status
        self.currier = currier
        self.lastLocation = lastLocation
        self.lastLocationTime = time()
        
#
class TransferOrder(object):
    def __init__(self, transfer, status, pickupWindow, currier):

# A basic package, currently only has a pos tuple and a distance calculator
class Package(object):
    def __init__(self, pos):
        self.pos = pos
    def distance(self, pos):
        return sum((self.pos[i] - pos[i]) ** 2 for i in (0, 1)) ** .5

# Generate a 1000 packages in a grid
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, HTTPServer
from json import dumps
from random import uniform
from time import time
from urllib.parse import urlparse, parse_qs


packages = {
    sha256(''.join((str(o) for o in (time(), i))).encode('UTF-8')).hexdigest():
        Package((
            uniform(31.95, 32.15),
            uniform(34.70, 34.90)
        )) for i in range(200)
}

shipments = {
             "s:"+str(i): Shipment( Parcel("env"),
                            Location((uniform(31.95, 32.15), uniform(34.70, 34.90))),
                            Location((uniform(31.95, 32.15), uniform(34.70, 34.90))) 
                            ) for i in range(20)
}

#Get packages in a radius around a center
def getpackages(center, radius):
    return [key for key, package in packages.items() if package.distance(center) < radius]

#
def getShipmentSourcesInRange(center, range):
    return [key for key, shipment in shipments.items() if shipment.sourceLoc.distance(center) < range]

# Our jsonp delivering handler
class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if '.jsonp' != url.path[-6:]: return SimpleHTTPRequestHandler.do_GET(self)
        query = parse_qs(url.query)
        if 'callback' not in query: raise Exception('No callback specified')
        callback = query['callback'][-1]

        try:
            if '/package.jsonp' == url.path: data = packages[query['id'][0]].pos
            elif '/packages.jsonp' == url.path: data = getpackages(
                [float(i) for i in query['center'][0].split(':')],
                float(query['radius'][0])
            )
            else: data = {'error': 'Did not understand ' + url.path}
        except (KeyError, ValueError): data = {'error': 'Wrong parameters', 'query': query}

        self.send_response(200)
        self.send_header('Content-type', 'application/javascript')
        self.end_headers()
        self.wfile.write(bytes(callback + '(' + dumps(data) + ');', 'UTF-8'))

# Run the server on port 8080 till keyboard interrupt
if __name__ == '__main__':
    server = HTTPServer(('localhost', 8080), Handler)
    sockname = server.socket.getsockname()
    try:
        print("\nServing HTTP on", sockname[0], "port", sockname[1], "...")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, exiting.")
        server.server_close()
        from sys import exit
        exit(0)
