#!/usr/bin/python3

# A basic package, currently only has a pos tuple and a distance calculator
class Package(object):
    def __init__(self, pos):
        self.pos = pos
    def distance(self, pos):
        return sum((self.pos[i] - pos[i]) ** 2 for i in (0, 1)) ** .5

# Generate a 100 packages in a grid
from hashlib import sha256
from time import time
from random import random
packages = {
    sha256(''.join((str(o) for o in (time(), lon, lat))).encode('UTF-8')).hexdigest():
        Package((lon / 100, lat / 100))
        for lon in range(3195, 3215)
        for lat in range(3470, 3490) if random() > .6
}
# for p in packages.keys():
#     if random.random() > .2: packages.pop(p)
#     print(p, random.randint(1,10))

#Get packages in a radius around a center
def getpackages(center, radius):
    return [key for key, package in packages.items() if package.distance(center) < radius]

# Our jsonp delivering handler
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from json import dumps
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
