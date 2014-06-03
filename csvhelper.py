#!./py2/bin/python
# -*- coding: utf-8 -*-

from router import Router

def getlatlng(address):
    latlngs = Router.getgeocode(address)
    if len(latlngs) > 0:
        return (address, (latlngs[0][u'lat'], latlngs[0][u'lon']))
    words = address.split(' ')[1:]
    if len(words) < 3:
        raise Exception('invalid address')
    return getlatlng(' '.join(words))

def gettraveltime(address):
    try:
        addr, dst = getlatlng(address)
#         print("got addr:%s   ll: %s" % (addr, dst))
    except Exception as e:
        if 'invalid address' == str(e):
            return ("",0)
        else:
            raise
    #     print("calculating for %s from %s to %s" % (addr, src, dst))
    return (addr, Router(src, dst, 'bicycle').getTravelTimeMin())

if __name__ == '__main__':
    from sys import argv, stdout
    _, src = getlatlng(' '.join(argv[2:]))
    with open(argv[1]) as f:
        from csv import writer, reader
        out = writer(stdout)
        for row in reader(f):
            if row[15] == '':
                r = gettraveltime(row[4])
                row[15], row[16] = r

            out.writerow(row)
