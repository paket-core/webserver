#!./py2/bin/python
# -*- coding: utf-8 -*-
import httplib

import json
from pprint import pprint
import os.path


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


def streetsfromjson(jsondata, limit=None):
    streets_dict = {}
    for element in jsondata['elements']:
        try:
            tags = element['tags']
            if 'name' not in tags:
                continue
            if 'highway' not in tags:
                continue
            if tags['highway'] in ('bus_stop',):
                continue
        except KeyError:
            continue
        streetname = tags['name']
        streets_dict[streetname] = {'name': streetname}
        # print "name: %s" % (streetname,)
        for tag, val in tags.items():
            if tag.startswith('name:'):
                nametype = tag.split(':')[1]
                # print "  - %s: %s" % (nametype, val)
                streets_dict[streetname][nametype] = val
        if limit is not None and limit <= len(streets_dict):
            break

    return streets_dict


def getstreetsfromfile(jsonfilename, limit=None):
    json_data = open(jsonfilename)
    data = json.load(json_data)
    json_data.close()
    return streetsfromjson(data, limit)


def getstreetsofcity(relationcode, limit=None):
    ensurefolderready('cache')
    relationcodefilename = 'cache/area%s.json' % (relationcode,)
    if not os.path.isfile(relationcodefilename):
        print 'file %s not found. getting from server.' % (relationcodefilename,)
        jsondata = getcityfromOSM(relationcode)
        print "writing file %s" % (relationcodefilename,)
        with open(relationcodefilename, 'w') as outfile:
            json.dump(jsondata, outfile)

    return getstreetsfromfile(relationcodefilename, limit)


def getcitiesfromfile(citiesfilename):
    """ Return list of city tuples (name, id). """
    json_data = open(citiesfilename)
    data = json.load(json_data)
    json_data.close()
    cities_list = []
    for element in data['elements']:
        if 'tags' in element:
            element_id = element['id']
            try:
                name = element['tags']['name']
            except KeyError:
                print 'NO NAME!', element_id
                name = element['tags']['name:he']  # use hebrew name if name don't exist

            cities_list += (name, element_id),
    return cities_list


def getcities():
    """get cities from cache if available. If not get data from OSM and create cache."""
    ensurefolderready('cache')
    citiesfilename = 'cache/cities.json'
    if not os.path.isfile(citiesfilename):
        print 'file %s not found. getting from server.' % (citiesfilename,)
        jsondata = getcitiesfromOSM()
        print "writing file %s" % (citiesfilename,)
        with open(citiesfilename, 'w') as outfile:
            json.dump(jsondata, outfile)

    return getcitiesfromfile(citiesfilename)


def getOSMdata(params):
    print "getting:", params
    conn = httplib.HTTPConnection("overpass-api.de")
    try:
        conn.request("GET", "/api/interpreter?" + params)
    except IOError as IOe:
        print("connection to server failed: " + str(IOe))
    response = conn.getresponse()
    d1 = response.read()
    conn.close()
    jsondata = json.loads(d1.decode('utf8'))
    return jsondata


def getcityfromOSM(relationcode):
    areacode = str(3600000000 + relationcode)  # trick to make an area from a relation
    params = 'data=%5Bout%3Ajson%5D%3B%28node%28area%3A' + areacode + '%29%3Bway%28bn%29%3B%29%3Bout%20body%3B'
    return getOSMdata(params)


def getcitiesfromOSM():
    params = 'data=%5Bout%3Ajson%5D%3Barea%5B%22name%22%3D%22%D7%9E%D7%93%D7%99%D7%A0%D7%AA%20%D7%99%D7%A9%D7%A8%D7%90%D7%9C%22%5D%3B%28relation%5B%22admin%5Flevel%22%7E%228%22%5D%28area%29%3B%29%3Bout%20body%3B'
    return getOSMdata(params)


def ensurefolderready(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


if __name__ == '__main__':

    cities = getcities()

    print "get streets for %d cities!\n----------------------\n" % (len(cities),)
    c = 0
    city_size = {}
    for cityname, city_id in cities:
        c += 1
        # if c > 10: break
        if city_id == 1381350:
            print '*' * 40
        print cityname, city_id
        # print "(%d/%d) GETTING STREETS FOR: %s -%d-" % (c, len(cities), cityname, city_id)
        streets = getstreetsofcity(city_id, limit=None)
        city_size[cityname] = len(streets)
        print "got %s streets in %s" % (len(streets), cityname)
        # for k,v in streets.items():
        #     print k,v
        print

    for n, s in sorted(city_size.items(), key=lambda x: x[1]):
        print s, n

    print "JERUSALEM is NOT included!"