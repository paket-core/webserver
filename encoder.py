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


def str2phonetic(src, useLAPD=False):
    NATO_phonetic_alphabet = \
        {"a": "alpha", "b": "bravo", "c": "charlie", "d": "delta", "e": "echo", "f": "foxtrot", "g": "golf",
         "h": "hotel", "i": "india", "j": "juliett", "k": "kilo", "l": "lima", "m": "mike", "n": "november",
         "o": "oscar", "p": "papa", "q": "quebec", "r": "romeo", "s": "sierra", "t": "tango", "u": "uniform",
         "v": "victor", "w": "whiskey", "x": "x-ray", "y": "yankee", "z": "zulu", "-": "dash", "0": "Zero", "1": "One",
         "2": "Two", "3": "Three", "4": "Four", "5": "Five", "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine"}
    NATO_phonetic_alphabet = dict((k.upper(), v.upper()) for k, v in NATO_phonetic_alphabet.items())

    LAPD_phonetic_alphabet = \
        {"a": "Adam", "b": "Bravo", "c": "Charles", "d": "David", "e": "Edward", "f": "Frank", "g": "George",
         "h": "Henry", "i": "Ida", "j": "John", "k": "Karen", "l": "Lincoln", "m": "Mary", "n": "Nancy", "o": "Ocean",
         "p": "Paul", "q": "Queen", "r": "Robert", "s": "Sam", "t": "Tom", "u": "Union", "v": "Victor", "w": "William",
         "x": "X-ray", "y": "Young", "z": "Zebra", "-": "dash", "0": "Zero", "1": "One", "2": "Two", "3": "Three",
         "4": "Four", "5": "Five", "6": "Six", "7": "Seven", "8": "Eight", "9": "Niner"}
    LAPD_phonetic_alphabet = dict((k.upper(), v) for k, v in LAPD_phonetic_alphabet.items())

    HEBREW_phonetic_alphabet = \
        {"a": "Aba", "b": "Banana", "c": "Cigarya", "d": "David", "e": "Erez", "f": "Feya", "g": "Ginger",
         "h": "Hertzel", "i": "Igloo", "j": "John", "k": "Kelev", "l": "Layla", "m": "Matos", "n": "Na'al", "o": "Oren",
         "p": "Pilpel", "q": "Queen", "r": "Arnak", "s": "Sigal", "t": "Tisan", "u": "Yulia", "v": "Virus", "w": "William",
         "x": "Extra", "y": "Yosi", "z": "Zebra", "-": "Makaf", "0": "Effes", "1": "Ahat", "2": "Shtayim", "3": "Shalosh",
         "4": "Arba", "5": "Hamesh", "6": "Shesh", "7": "Sheva", "8": "Shmoneh", "9": "Tesha"}
    HEBREW_phonetic_alphabet = dict((k.upper(), v) for k, v in HEBREW_phonetic_alphabet.items())

    srcStr = str(src).upper()
    if useLAPD:
        d = LAPD_phonetic_alphabet
    else:
        d = HEBREW_phonetic_alphabet

    try:
        return ', '.join(d[ch] for ch in srcStr)
    except KeyError:
        return '"' + src + '"'


def baseKinfo():
    """print info about the decoder."""
    print("baseK info:\n-----------")
    print("characters used:", alphabet)
    print("characters", len(alphabet))
    print("scale:")
    for i in range(1, 10): print("possible numbers for %d character: %u" % (i, len(alphabet) ** i))


def baseKencode(number, phonetic=False):
    """Converts positive integer to a baseK string."""
    if not isinstance(number, int):
        raise TypeError('number must be an integer')

    base = ''

    if number < 0:
        raise TypeError('number must be positive')

    if number < len(alphabet):
        if phonetic:
            return str2phonetic(alphabet[number])
        else:
            return alphabet[number]

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base = alphabet[i] + base

    if phonetic:
        return str2phonetic(base)
    else:
        return base


def baseKdecode(val):
    """Decode a baseK string. Case insensitive."""
    num = 0;
    if not isinstance(val, str):
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
    if isinstance(val, str):
        return str(baseKdecode(val))[-1]
    elif isinstance(val, int):
        return str(val)[-1]
    else:
        raise ValueError("baseKrc must receive either a number or a string")


def baseKencodeRC(number):
    """Return baseKencode string including redundancy check."""
    return baseKencode(number) + baseKrc(number)


if __name__ == '__main__':
    import random

    print('\n' * 2)
    baseKinfo()

    print("\ncheck encoding and decoding for random numbers\n" + "-" * 47)

    v = 0
    for i in range(0, 20):
        encode = baseKencode(v)
        print(v, "==>", encode, "==>", baseKdecode(encode), baseKencodeRC(v), type(v))
        if v != baseKdecode(encode):
            raise ValueError('encoder and decoder do not match!')
        v += random.randint(1, 1 + v * 50)  # this grows rapidly!

    print("\ncheck encoding (some may fail)\n" + "-" * 30)
    all = alphabet * 3 + "abcdefghijklmnopqrstuvwxy0123456789*"
    for i in range(30):
        s = ''
        length = random.randint(1, 5)
        for c in range(0, length):
            s += all[random.randint(0, len(all)) - 1]

        try:
            print(i, s, "=>", baseKdecode(s), "rc:", baseKrc(s), "[%s]" % (str2phonetic(s),))
        except ValueError as e:
            print("got", e)

    print("\ncheck phonetic\n" + "-" * 15)
    print("unknown chars:", str2phonetic("234@#"))
    print("shalom:", str2phonetic("shalom"))
    print("shalom:", str2phonetic("shalom", useLAPD=True))
    print("12**4=", str2phonetic(12 ** 4, useLAPD=True))
