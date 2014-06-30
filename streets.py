#!./py2/bin/python
# -*- coding: utf-8 -*-
import httplib

import json
from pprint import pprint
import urllib


def streetsfromjson(jsondata):
    streets = {}
    for element in jsondata['elements']:
        try:
            tags = element['tags']
            if 'name' not in tags:
                continue
            if 'highway' not in tags:
                continue
            if tags['highway'] in ('bus_stop'):
                continue
        except KeyError:
            continue
        streetname = tags['name']
        streets[streetname] = {'name':streetname}
        # print "name: %s" % (streetname,)
        for tag, val in tags.items():
            if tag.startswith('name:'):
                nametype = tag.split(':')[1]
                # print "  - %s: %s" % (nametype, val)
                streets[streetname][nametype] = val

    return streets


def getstreetsfromfile(jsonfilename):
    json_data = open(jsonfilename)
    data = json.load(json_data)
    json_data.close()
    return streetsfromjson(data)


def getcities(jsonfilename):
    json_data = open(jsonfilename)
    data = json.load(json_data)
    json_data.close()
    for element in data['elements']:
        if 'tags' in element:
            print element['id']
            print element['tags']['name'], element['tags'].keys()


""" get ways in area
<osm-script output="json" timeout="15">
    <area-query ref="3601382460"/>
    <recurse type="node-way"/>
    <print mode="body"/>
</osm-script>
[out:json][timeout:15];node(area:3601382460);way(bn);out body;;
http://overpass-api.de/api/interpreter?data=%5Bout%3Ajson%5D%5Btimeout%3A15%5D%3Bnode%28area%3A3601382460%29%3Bway%28bn%29%3Bout%20body%3B

ways in holon: http://overpass-api.de/api/interpreter?data=%5Bout%3Ajson%5D%3B%28node%28area%3A3601382460%29%3Bway%28bn%29%3B%29%3Bout%20body%3B
"""

"""
[out:json];area["name"="מדינת ישראל"];(relation["admin_level"~"8"](area););out body;;
http://overpass-api.de/api/interpreter?data=%5Bout%3Ajson%5D%3Barea%5B%22name%22%3D%22%D7%9E%D7%93%D7%99%D7%A0%D7%AA%20%D7%99%D7%A9%D7%A8%D7%90%D7%9C%22%5D%3B%28relation%5B%22admin%5Flevel%22%7E%228%22%5D%28area%29%3B%29%3Bout%20body%3B
"""


def getcityfromOSM(relationcode):
    conn = httplib.HTTPConnection("overpass-api.de")
    areacode = str(3600000000 + relationcode)
    params = 'data=%5Bout%3Ajson%5D%3B%28node%28area%3A' + areacode + '%29%3Bway%28bn%29%3B%29%3Bout%20body%3B'
    try:
        conn.request("GET", "/api/interpreter?" + params)
    except IOError as IOe:
        print("connection to server failed: " + str(IOe))
    response = conn.getresponse()
    d1 = response.read()
    conn.close()
    jsondata = json.loads(d1.decode('utf8'))
    return jsondata


def getstreetsofcity(relationcode):
    import os.path

    relationcodefilename = 'area%s.json' % (relationcode,)
    if not os.path.isfile(relationcodefilename):
        print 'file %s not found. getting from server.' % (relationcodefilename,)
        jsondata = getcityfromOSM(relationcode)
        print "writing file %s" % (relationcodefilename,)
        with open(relationcodefilename, 'w') as outfile:
            json.dump(jsondata, outfile)

    return getstreetsfromfile(relationcodefilename)


def getcitiesfromfile(citiesfilename):
    json_data = open(citiesfilename)
    data = json.load(json_data)
    json_data.close()
    cities = []
    for element in data['elements']:
        if 'tags' in element:
            try:
                name = element['tags']['name']
            except:
                name = element['tags']['name:he']

            cities += (name, element['id']),
    return cities


def getcities():
    import os.path

    citiesfilename = 'cities.json'
    if not os.path.isfile(citiesfilename):
        print 'file %s not found. getting from server.' % (citiesfilename,)
        jsondata = getcitiesfromOSM()
        print "writing file %s" % (citiesfilename,)
        with open(citiesfilename, 'w') as outfile:
            json.dump(jsondata, outfile)

    return getcitiesfromfile(citiesfilename)


def getcitiesfromOSM():
    conn = httplib.HTTPConnection("overpass-api.de")
    params = 'data=%5Bout%3Ajson%5D%3Barea%5B%22name%22%3D%22%D7%9E%D7%93%D7%99%D7%A0%D7%AA%20%D7%99%D7%A9%D7%A8%D7%90%D7%9C%22%5D%3B%28relation%5B%22admin%5Flevel%22%7E%228%22%5D%28area%29%3B%29%3Bout%20body%3B'
    try:
        conn.request("GET", "/api/interpreter?" + params)
    except IOError as IOe:
        print("connection to server failed: " + str(IOe))
    response = conn.getresponse()
    d1 = response.read()
    conn.close()
    jsondata = json.loads(d1.decode('utf8'))
    return jsondata


if __name__ == '__main__':
    # getstreetsfromfile('area1382460.json')
    # getstreetsofarea(1382460) # holon
    # getcities('city areas around center.json')

    # getstreetsofarea(1382821) # ramat hasharon

    cities = getcities()
    print "get streets for %d cities!\n----------------------\n" % (len(cities),)
    c = 0
    for name, id in cities:
        c += 1
        print "(%d/%d) GETTING STREETS FOR: %s(%d)" % (c, len(cities), name, id)
        streets = getstreetsofcity(id)
        print "got %s streets in %s" % (len(streets), name)
        # for k,v in streets.items():
        #     print k,v
        print
