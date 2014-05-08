#!/usr/bin/python3

import http.client, urllib.parse
import json

# TODO: Make a class
 
"""Returns a rout between to points on a map

fromLatLng - from tuple of (latitude, longitude)    
toLatLng - to tuple of (latitude, longitude)    
transport - the type of transport, possible options are: motorcar, bicycle or foot. Default is: motorcar.
"""
def getRoute(fromLatLng, toLatLng, transport='motorcar'):
    conn = http.client.HTTPConnection("www.yournavigation.org")
    params = urllib.parse.urlencode({'format':'geojson', 
                                     'flon':fromLatLng[1], 'flat':fromLatLng[0], 
                                     'tlon':toLatLng[1], 'tlat':toLatLng[0], 
                                     'v': transport, 'fast':'1', 
                                     'layer':'mapnik', 'instructions':1})
    
    headers = {"Content-type":"application/x-www-form-urlencoded", 
               "Accept":"text/html", 
               "X-Yours-client": "oren@orengampel.com  testing"}
    print(params)
    try:
        conn.request("GET", "/api/1.0/gosmore.php?" + params)
    except IOError as IOe:
        return "connection to server failed: " + str(IOe)
     
    response = conn.getresponse()
    print(response.status, response.reason)
    d1 = response.read()
    j1 = json.loads(d1.decode('utf8'))
    conn.close()
    return j1



# Run a demo
if __name__ == '__main__':
    print("DEMO!!\n" + "-"*6)

    routeJ = getRoute(('32.0678','34.7647'),('32.0231', '34.7503'), 'motorcar') 
    print("on car: distance: %s time: %s" %(routeJ['properties']['distance'], routeJ['properties']['traveltime']))
    routeJ = getRoute(('32.0678','34.7647'),('32.0231', '34.7503'), 'bicycle') 
    print("on bicycle: distance: %s time: %s" %(routeJ['properties']['distance'], routeJ['properties']['traveltime']))
    routeJ = getRoute(('32.0678','34.7647'),('32.0231', '34.7503'), 'foot') 
    print("on foot: distance: %s time: %s" %(routeJ['properties']['distance'], routeJ['properties']['traveltime']))
    
    #from pprint import pprint
    #pprint(routeJ['properties']['distance'])
    