'''if the PAC-ID has no valid categories no PAC-CAT will be created'''
from labfreed.pac_id.pac_id import PAC_ID


pac_str = 'HTTPS://PAC.METTORIUS.COM/XQ908756/bal500/@1234' # not valid PAC-CAT
pac = PAC_ID.from_url(pac_str) 

'''You can also use getattr'''
categories = getattr(pac, 'categories', None) 

''' or catch the Attribute Error'''
try:
    categories = pac.categories
except AttributeError:
    pass