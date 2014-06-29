#!./py2/bin/python
# -*- coding: utf-8 -*-
import httplib

import json
from pprint import pprint
import urllib


def streetsfromjson(jsondata):
    for element in jsondata['elements']:
        try:
            tags = element['tags']
            if 'name' not in tags:
                continue
            if 'highway' not in tags:
                continue
        except KeyError:
            continue
        print "name: %s" % (tags['name'],), tags
        for tag, val in tags.items():
            if tag.startswith('name:'):
                nametype = tag.split(':')[1]
                print "  - %s: %s" % (nametype, val)


def getstreetsfromfile(jsonfilename):
    json_data = open(jsonfilename)
    data = json.load(json_data)
    json_data.close()
    streetsfromjson(data)


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
"""


def getstreetsofarea(relationcode):
    import os.path
    areacodefilename = 'area%s.json' % (relationcode,)
    if not os.path.isfile(areacodefilename):
        print 'file %s not found. getting from server.' % (areacodefilename,)
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
        print "writing file %s" % (areacodefilename,)
        with open(areacodefilename, 'w') as outfile:
            json.dump(jsondata, outfile)

    getstreetsfromfile(areacodefilename)


if __name__ == '__main__':
    # getstreetsfromfile('area1382460.json')
    # getstreetsofarea(1382460) # holon
    # getcities('city areas around center.json')

    getstreetsofarea(1382821) # ramat hasharon



