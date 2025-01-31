import string

def alphabet(base):
    """ returns an alphabet, which corresponds to what pythons int(s:str, base:int=10) function used.
    """
    if base < 2 or base > 36:
        ValueError('base can only be between 2 and 36')    
    alphabet = (string.digits + string.ascii_uppercase)[0:base]
    return alphabet

def to_base36(s:str):
    """Takes a string, encodes it in UTF-8 and then as base36 string."""
    utf8_encoded = s.encode('utf-8')
    num = int.from_bytes(utf8_encoded, byteorder='big', signed=False)
    
    # note: this cannot be arbitrarily chosen. The choice here corresponds to what pythons int(s:str, base:int=10) function used.
    base36_chars = alphabet(base=36)
    if num == 0:
        return base36_chars[0]
    base36 = []
    _num = num
    while _num:
        _num, i = divmod(_num, 36)
        base36.append(base36_chars[i])
    return ''.join(reversed(base36))


def from_base36(s36:str):
    """inverse of to_base36"""
    # this built in function interprets each character as number in a base represented by the standartd alphabet [0-9 (A-Z|a-z)][0:base] it is case INsensitive.
    num = int(s36, 36)
    num_bytes = (num.bit_length() + 7) // 8
    _bytes = num.to_bytes(num_bytes, byteorder='big')
    s = _bytes.decode('utf-8')
    return s


ss = ["Mini Spray Dryer S-300", "w3ApashAt!!£NAGDSAF*ç%&/()"]
for s in ss:
    s36 = to_base36(s)
    s_back = from_base36(s36)
    identical = (s == s_back)
    print(f'{s} >> {s36} >> {s_back}: match:{identical}')
