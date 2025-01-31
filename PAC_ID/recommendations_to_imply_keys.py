# the conventions for default assignment of keys of category segments
from types import MappingProxyType


category_conventions = MappingProxyType(
                            {
                                '-MD': ['240', '21'],
                                '-MS': ['240', '10', '20', '21', '250'],
                                '-MC': ['240', '10', '20', '21', '250'],
                                '-MM': ['240', '10', '20', '21', '250']
                            }
                        )


extension_convention = MappingProxyType(
                                {
                                    0: { 'name': 'N', 'type': 'N'},
                                    1: { 'name': 'SUM', 'type': 'TREX'}
                                }
                            )