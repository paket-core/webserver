#!./py2/bin/python

alphabet='123456789ABCDEFGHJKMNPRSTVWXYZ'

def baseKencode(number):
    """Converts an integer or long to a baseK string."""
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
    num = 0;
    for c in val:
        num *= len(alphabet)
        try:
            num += alphabet.index(c)
        except ValueError:
            raise ValueError('character \'%s\' is not a valid baseK string' % (c,))
    return num


if __name__=='__main__':
    import random
    v = 0
    for i in range(0,130):
        encode = baseKencode(v)
        print v, encode, baseKdecode(encode), type(v)
        if v != baseKdecode(encode):
            raise ValueError('encoder and decoder do not match!')
        v += random.randint(1,1+v)

