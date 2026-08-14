from typing import Literal, Self

from pydantic import computed_field 
from labfreed.labfreed_infrastructure import LabFREED_BaseModel
from labfreed.pac_id.extension import ExtensionBase
from labfreed.pac_id.keyed_values import KeyedValue, ExtensionOrigin, TrexTableOrigin
from labfreed.trex.trex import Spec_T_REX
from labfreed.trex.table_segment import TableSegment
from labfreed.trex.facade.t_rex import _trex_segment_to_python_type


class TREX_Extension(ExtensionBase, LabFREED_BaseModel):
    name:str
    type:Literal['TREX'] = 'TREX'
    trex:Spec_T_REX

    @computed_field
    @property
    def data(self)->str:
        trex_str = self.trex.serialize()
        return trex_str

    @staticmethod
    def from_extension(ext:ExtensionBase) -> Self:
        return TREX_Extension.create(name=ext.name,
                                    type=ext.type,
                                    data=ext.data)

    @staticmethod
    def create(*, name, data, type='TREX'):
        trex_extension = TREX_Extension(name= name, trex = Spec_T_REX.deserialize(data))
        return trex_extension

    def values_for_key(self, key: str) -> list[KeyedValue]:
        '''Overrides the ExtensionBase default to search this extension's own
        Spec_T_REX segments *and* every TableSegment's columns - required by the
        T-REX spec's own example (ENV/PH/CONDUCTIVITY tables each with a TEMP
        column): "TEMP" is a repeated column key across three separate top-level
        table segments, never a top-level segment key itself, so
        Spec_T_REX.get_segment() alone would find nothing. Values are decoded via
        the same conversion T_REX.from_trex() already uses (Quantity for numeric,
        including unitless - see CLAUDE.md "LabFREED has no unitless numbers"),
        not the raw wire string.'''
        results = []
        for seg in self.trex.segments:
            if isinstance(seg, TableSegment):
                if key in seg.column_names:
                    table = _trex_segment_to_python_type(seg)
                    results.append(KeyedValue(
                        value=table.get_column(key),
                        origin=TrexTableOrigin(extension_name=self.name, table_key=seg.key),
                    ))
            elif seg.key == key:
                results.append(KeyedValue(
                    value=[_trex_segment_to_python_type(seg)],
                    origin=ExtensionOrigin(extension_name=self.name),
                ))
        return results

