#!./py2/bin/python
"""
baseK encoding tools

The encoding is based on limited set of latin characters and numeral digits to the reduce chance of
 a faulty reading and writing in both typing and hand writing.

   Encoding is made to upper case chars.
   Decoding is case insensitive.
   Hand writing should be done with upper case, but since this can't be enforced some additional characters
   were removed.

   Unused characters
   0 O o Q and q
   I i L and l (1 is used)
   U and u (V is used)

   To consider:
   6 ang G can look similar when hand writen.
"""

alphabet = '123456789ABCDEFGHJKMNPRSTVWXYZ'


def baseKinfo():
    """print info about the decoder."""
    print "baseK info:\n--------------"
    print "alphabet used:", alphabet
    print "characters", len(alphabet)
    print "scale:"
    for i in range(1, 10): print "possible numbers for %d character: %d" % (i, len(alphabet) ** i)


def baseKencode(number):  #TODO add call signs param
    """Converts positive integer or long to a baseK string."""
    if not isinstance(number, (int, long)):
        raise TypeError('number must be an integer or long')

    base = ''

    if number < 0:
        raise TypeError('number must be positive')

    if number < len(alphabet):
        return alphabet[number]

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base = alphabet[i] + base

    return base


def baseKdecode(val):
    """Decode a baseK string. Case insensitive."""
    num = 0;
    if not isinstance(val, basestring):
        raise ValueError(str(val) + " is not a valid string")
    val = val.upper()
    for c in val:
        num *= len(alphabet)
        try:
            num += alphabet.index(c)
        except ValueError:
            raise ValueError('character \'%s\' is not a valid baseK string' % (c,))
    return num


def baseKrc(val):
    """Return single character for redundancy check."""
    if isinstance(val, basestring):
        return str(baseKdecode(val))[-1]
    elif isinstance(val, (int, long)):
        return str(val)[-1]
    else:
        raise ValueError("baseKrc must receive either a number or a string")


def baseKencodeRC(number):
    """Return baseKencode string including redundancy check."""
    return baseKencode(number) + baseKrc(number)


if __name__ == '__main__':
    import random

    baseKinfo()

    print "\ncheck encoding and decoding for random numbers"

    v = 0
    for i in range(0, 20):
        encode = baseKencode(v)
        print v, "==>", encode, "==>", baseKdecode(encode), baseKencodeRC(v), type(v)
        if v != baseKdecode(encode):
            raise ValueError('encoder and decoder do not match!')
        v += random.randint(1, 1 + v * 50)  # this grows rapidly!

    print "check encoding (some may fail)"
    all = alphabet * 3 + "abcdefghijklmnopqrstuvwxy0123456789*"
    for i in range(30):
        s = ""
        length = random.randint(1, 5)
        for c in range(0, length):
            s += all[random.randint(0, len(all)) - 1]

        # s = s.upper()

        try:
            print i, s, "=>", baseKdecode(s), "rc:", baseKrc(s)
        except ValueError, e:
            print "got", e

