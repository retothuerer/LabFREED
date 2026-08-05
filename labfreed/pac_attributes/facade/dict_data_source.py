from deprecated import deprecated

from labfreed.pac_attributes.facade.attributes import Attributes
from labfreed.pac_attributes.server.attribute_data_sources import Spec_Dict_DataSource


class Dict_DataSource(Spec_Dict_DataSource):
    def __init__(self, data:dict[str, Attributes], *args, **kwargs):
        if not all([isinstance(e, Attributes) for e in data.values()]):
            raise ValueError('Invalid data')
        d = {k: v.to_payload_attributes() for k,v in data.items()}
        super().__init__(data=d, *args, **kwargs)


@deprecated("Use Dict_DataSource. Deprecated since v1.0, will be removed in v2.0.")
class pyDict_DataSource(Dict_DataSource):
    '''Deprecated alias for Dict_DataSource - kept for backward compatibility.'''
