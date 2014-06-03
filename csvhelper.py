#!./py2/bin/python
# -*- coding: utf-8 -*-

from router import Router

def getlatlng(address):
    latlngs = Router.getgeocode(address)
    if len(latlngs) > 0:
        return (latlngs[0][u'lat'], latlngs[0][u'lon'])
    words = address.split(' ')[1:]
    if len(words) < 3:
        raise Exception('invalid address')
    return getlatlng(' '.join(words))

def gettraveltime(address):
    try:
        dst = getlatlng(address)
    except Exception as e:
        if 'invalid address' == str(e):
            return
        else:
            raise
    return Router(src, dst, 'bicycle').getTravelTimeMin()

if __name__ == '__main__':
    from sys import argv, stdout
    src = getlatlng(' '.join(argv[2:]))
    print(argv[1])
    with open(argv[1]) as f:
        from csv import writer, reader
        out = writer(stdout)
        for row in reader(f):
            out.writerow(row + [gettraveltime(row[4])])
