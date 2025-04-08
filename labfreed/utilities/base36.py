import re
import string

from pydantic import field_validator, RootModel

class base36(RootModel[str]):
    @field_validator('root')
    @classmethod
    def validate_format(cls, v: str) -> str:
        if not re.fullmatch(r'[A-Z0-9]*', v):
            raise ValueError("Value must only contain uppercase letters and digits (A-Z, 0-9)")
        return v
    

def to_base36(s:str) -> base36:
    """Takes a string, encodes it in UTF-8 and then as base36 string."""
    utf8_encoded = s.encode('utf-8')
    num = int.from_bytes(utf8_encoded, byteorder='big', signed=False)
    
    # note: this cannot be arbitrarily chosen. The choice here corresponds to what pythons int(s:str, base:int=10) function used.
    base36_chars = _alphabet(base=36)
    if num == 0:
        return base36_chars[0]
    base_36 = []
    _num = num
    while _num:
        _num, i = divmod(_num, 36)
        base_36.append(base36_chars[i])
    b36_str = ''.join(reversed(base_36))
    b36_str = base36(b36_str)
    return b36_str


def from_base36(s36:base36) -> str:
    """inverse of to_base36"""
    # this built in function interprets each character as number in a base represented by the standartd alphabet [0-9 (A-Z|a-z)][0:base] it is case INsensitive.
    num = int(s36, 36)
    num_bytes = (num.bit_length() + 7) // 8
    _bytes = num.to_bytes(num_bytes, byteorder='big')
    s = _bytes.decode('utf-8')
    return s


def _alphabet(base):
    """ returns an alphabet, which corresponds to what pythons int(s:str, base:int=10) function used.
    """
    if base < 2 or base > 36:
        ValueError('base can only be between 2 and 36')    
    alphabet = (string.digits + string.ascii_uppercase)[0:base]
    return alphabet


if __name__ == "__main__":
    ss = ["A",
      "B-500 B",
      "B-500 Ba",
      "B-500 Bal",
      "B-500 Bala",
      "B-500 Balanc",
      "B-500 Balance",
      "B-500 D",
      "Mini Spray Dryer S-300", 
      "w3ApashAt!!£NAGDSAF*ç%&/()",
      "HELLOWORLD", 
      "Helloworld",
      "$£äö!'?^{]<@#¦&¬|¢)&§°😀你好🌍🏯😇🎵🔥你👻🐉😀你好🌍🏯😇🎵🔥你👻🐉😀你好🌍🏯😇🎵🔥你👻🐉😀你好🌍🏯😇🎵🔥你👻🐉😀你好🌍🏯😇🎵🔥你👻🐉😀你好🌍🏯😇🎵🔥你👻🐉😀你好🌍🏯😇🎵🔥你👻🐉",
      "往跟住！師立甲錯什正再圓身升因月室",
      "Balance BAL500 @☣️Lab",
      "BAL500 @☣️Lab",
      "BAL-CLEAN",
      "Smørrebrød µ-Nutrients",
      "Demo Result from R-300",
      "Rotavapor R-300",
      "Rotavapor R-250",
      "Rotavapor R-220",
      "SyncorePlus"
      ]
    for s in ss:
        s36 = to_base36(s)
        s_back = from_base36(s36)
        identical = (s == s_back)
        print(f'{s} >> {s36} >> {s_back}: match:{identical}')
