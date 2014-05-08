#!/usr/bin/python3

import http.client, urllib.parse
import json


class Router:

    """Returns a rout between to points on a map

    fromLatLng - from tuple of (latitude, longitude)
    toLatLng - to tuple of (latitude, longitude)
    transport - the type of transport, possible options are: motorcar, bicycle or foot. Default is: motorcar.
    """
    def __init__(self, fromLatLng, toLatLng, transport='motorcar'):
        self.jsonRouteData = None
        conn = http.client.HTTPConnection("www.yournavigation.org")
        params = urllib.parse.urlencode({'format':'geojson', 
                                         'flon':fromLatLng[1], 'flat':fromLatLng[0],
                                         'tlon':toLatLng[1], 'tlat':toLatLng[0],
                                         'v': transport, 'fast':'1',
                                         'layer':'mapnik', 'instructions':1})
        
        headers = {"Content-type":"application/x-www-form-urlencoded", 
                   "Accept":"text/html", 
                   "X-Yours-client": "oren@orengampel.com  testing"}
        try:
            conn.request("GET", "/api/1.0/gosmore.php?" + params)
        except IOError as IOe:
            print("connection to server failed: " + str(IOe))
         
        response = conn.getresponse()
        print(response.status, response.reason)
        d1 = response.read()
        self.jsonRouteData = json.loads(d1.decode('utf8'))
        conn.close()

    """Return the original JSON data"""
    def getJson(self):
        return self.jsonRouteData
    
    """Return travel time"""
    def getTravelTime(self):
        if self.jsonRouteData:
            return self.jsonRouteData['properties']['traveltime']
        else:
            return

    """Return travel time in minutes"""
    def getTravelTimeMin(self):
        if self.jsonRouteData:
            return int(self.jsonRouteData['properties']['traveltime'])/60
        else:
            return

    """Return distance"""
    def getDistance(self):
        if self.jsonRouteData:
            return self.jsonRouteData['properties']['distance']
        else:
            return
        
    def getPath(self):
        if self.jsonRouteData:
            return self.jsonRouteData['coordinates']


# Run a demo
if __name__ == '__main__':
    print("DEMO!!\n" + "-"*6)
    
    print("driving, cycling and walking from Tel Aviv Port to Azrieli Center\n")

    route = Router(('32.07473','34.79153'),('32.09550', '34.77225'), 'motorcar') 
    print("on car: distance: %s time: %im" % (route.getDistance(), route.getTravelTimeMin()))
    route = Router(('32.07473','34.79153'),('32.09550', '34.77225'), 'bicycle')
    print("on bicycle: distance: %s time: %im" % (route.getDistance(), route.getTravelTimeMin()))
    route = Router(('32.07473','34.79153'),('32.09550', '34.77225'), 'foot')
    print("on foot: distance: %s time: %im" % (route.getDistance(), route.getTravelTimeMin()))
    
#     from pprint import pprint
#     pprint(route.getJson())
#     print(len(route.getPath()))
    
    
