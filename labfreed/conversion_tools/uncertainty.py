from math import floor, log10, pow

def to_significant_digits_str(x:int|float, uncertainty:float|int) -> str:
    if uncertainty == None:
        if isinstance(x, float):
            Warning(f'Uncertainty was given as none. Returning unrounded number')
            return str(x)
        else:
            uncertainty = 1

    
    log_least_significant_digit = floor(log10(uncertainty))
    digits = -log_least_significant_digit
    
    x_significant = round(x, digits)
    
    if digits <= 0:
        return str(int(x_significant))
    else:
        return str(x_significant)
        


if __name__ == "__main__":
    print(to_significant_digits_str(111111.1111111, 1000))
    print(to_significant_digits_str(111111.1111111, 100))
    print(to_significant_digits_str(111111.1111111, 10))
    print(to_significant_digits_str(111111.1111111, 1))
    print(to_significant_digits_str(111111.1111111, 0.1))
    print(to_significant_digits_str(111111.1111111, 0.01))
    print(to_significant_digits_str(111111.1111111, 0.001))
    print(to_significant_digits_str(111111.1111111, 0.0001))
