#!./py2/bin/python
# -*- coding: utf-8 -*-

import json
from pprint import pprint

if __name__ == '__main__':
    json_data = open('tlv.json')

    data = json.load(json_data)
    json_data.close()
    for element in data['elements']:
        try:
            tags = element['tags']
        except KeyError:
            continue
        print "name: %s" % (tags['name'],)
        for tag,val in tags.items():
            if tag.startswith('name:'):
                nametype = tag.split(':')[1]
                print "  - %s: %s" % (nametype,val)
