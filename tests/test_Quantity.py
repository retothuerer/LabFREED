from labfreed.trex.python_convenience.quantity import Quantity


def test_print_significant_digits():
    v = 111.111
    tests = [(-2, '111.11'),
             (-1, '111.1'),
             (0, '111'),
             (1, '110'), 
             (2, '100')]
    for t in tests:
        q =  Quantity(value=v, unit=None, log_least_significant_digit=t[0])
        v_rounded = q.value_as_str()
        assert  v_rounded == t[1]
        
        
        
def test_find_significant_digits():
    tests = [
            ('111.11', -2),
             ('111.1', -1),
             ('111', 0),
             ('110', 0), 
             ('100', 0),
             
             ('111.11e3', 1),
             ('111.1e3', 2),
             ('111e3', 3),
             ('110e3', 3), 
             ('100e3', 3),
             ('11e4', 4), 
             ('1e5', 5)
             ]
    for t in tests:
        log_least_significant_digit = Quantity._find_log_significant_digits(t[0])
        assert log_least_significant_digit == t[1]
    