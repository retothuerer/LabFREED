## Materials
from abc import ABC, abstractproperty
from pydantic import Field, PrivateAttr, computed_field, model_validator

from labfreed.labfreed_infrastructure import ValidationMsgLevel
from labfreed.pac_cat.category_base import Category, CategorySegment
from labfreed.pac_id.id_segment import IDSegment

class PredefinedCategory(Category, ABC):
    '''@private
    Base for Predefined catergories
    '''
    additional_segments: list[CategorySegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''

    _segment_bindings: list[tuple[CategorySegment, str | None]] | None = PrivateAttr(default=None)
    ''' @private (segment, field_alias) pairs in original parse order, set whenever parsed
    from an existing PAC-ID (regardless of whether a derivation marker is present).
    `PAC_CAT._resolve_identifier_for_notation` uses this - across *all* categories - to
    rebuild forced-notation output by walking `PAC_CAT.identifier` directly instead of
    concatenating each category's own segments, which would risk moving a category
    relative to another one. See `_use_position_preserving_segments` for the (separate)
    decision of whether `.segments` itself presents in this order or canonically.'''

    _use_position_preserving_segments: bool = PrivateAttr(default=False)
    ''' @private Whether the public `.segments` view preserves original order (only
    needed when a derivation marker is involved - see `PAC_CAT._cat_from_cat_segments`)
    instead of the long-standing canonical ordering (known fields in schema order, then
    custom segments) that existing consumers rely on when there's no marker to protect.'''

    @computed_field
    @property
    def segments(self) -> list[CategorySegment]:
        if self._use_position_preserving_segments:
            # The marker segment itself is hidden from this public view - once every
            # segment is tagged with `derivation_namespace`, it's redundant.
            return [s for s in self._get_segments_from_bindings(use_short_notation=False) if not s.is_derivation_namespace]
        return self._get_segments_canonical(use_short_notation=False)

    @abstractproperty
    def is_serialized(self) -> bool:
        pass

    def _get_segments_canonical(self, use_short_notation=False) -> list[CategorySegment]:
        ''' Known fields in schema order, then any custom segments - the long-standing
        reconstruction used when no derivation marker is involved (see
        `_use_position_preserving_segments`).'''
        segments = []
        can_omit_keys = use_short_notation # keeps track of whether keys can still be omitted. That is the case when the segment recommendation is followed
        for field_name, field_info in self.model_fields.items():
            if field_name in ['key', 'additional_segments']:
                continue
            if value := getattr(self, field_name):
                if can_omit_keys:
                    key = None
                else:
                    key = field_info.alias
                segments.append(CategorySegment(key= key, value= value)  )
            else:
                can_omit_keys = False
        if self.additional_segments:
            segments.extend(self.additional_segments)
        return segments

    def _get_segments_from_bindings(self, use_short_notation) -> list[CategorySegment]:
        ''' Re-emits the originally parsed segments in their original order, only
        adjusting whether known fields carry an explicit key - so custom segments and
        derivation namespace markers stay exactly where they were, instead of being
        moved after all known fields.'''
        omit_key_for_alias = self._omit_key_for_alias(use_short_notation)

        segments = []
        for seg, alias in self._segment_bindings:
            if alias is None:
                segments.append(seg)
            else:
                key = None if omit_key_for_alias.get(alias) else alias
                segments.append(CategorySegment(key=key, value=seg.value, derivation_namespace=seg.derivation_namespace))
        return segments

    def _omit_key_for_alias(self, use_short_notation) -> dict:
        ''' @private For each known field (by its GS1 alias), whether its key can be
        omitted under `use_short_notation` - true only while every preceding field in
        schema order is also present, per the "short notation" rule in the PAC-CAT spec.
        Used both for `.segments`/`_get_segments_from_bindings` and for resolving
        forced-notation key presence directly on `PAC_CAT.identifier`
        (`PAC_CAT._resolve_identifier_for_notation`). '''
        can_omit_keys = use_short_notation
        omit_key_for_alias = {}
        for field_name, field_info in self.model_fields.items():
            if field_name in ['key', 'additional_segments']:
                continue
            if getattr(self, field_name):
                omit_key_for_alias[field_info.alias] = can_omit_keys
            else:
                can_omit_keys = False
        return omit_key_for_alias

    model_config = {
        "populate_by_name": True
    }
    ''' @private Pydantic tweak to allows model fields to be populated using their Python name, even if they have an alias defined.
        The alias we need to use the GS1 code in serialization
    '''



class Material_Device(PredefinedCategory):
    '''Represents the -MD category'''
    key: str =         Field(default='-MD', frozen=True)
    model_number: str|None =         Field(              alias='240')
    serial_number: str|None =        Field(              alias='21')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    @model_validator(mode='after')
    def _validate_mandatory_fields(self):
        if not self.model_number:
            self._add_validation_message(
                    source=f"Category {self.key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f'Category key {self.key} is missing mandatory field Model Number',
                    highlight_pattern = f"{self.key}"
            )
        if not self.serial_number:
            self._add_validation_message(
                    source=f"Category {self.key}",
                    level = ValidationMsgLevel.WARNING,
                    msg=f'Category key {self.key} is missing field Serial Number. Check that you are indeed to a product and not a specific device.',
                    highlight_pattern = f"{self.key}"
            )
        return self
    
    @property
    def is_serialized(self) -> bool:
        return bool(self.serial_number)
    
    
class Material_Substance(PredefinedCategory):
    '''Represents the -MS category'''
    key: str =         Field(default='-MS', frozen=True)
    product_number:str|None =    Field(              alias='240')
    batch_number:str|None =     Field(default=None, alias='10')
    container_size:str|None =   Field(default=None, alias='20')
    container_number:str|None = Field(default=None, alias='21')
    aliquot:str|None =          Field(default=None, alias='250')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    @model_validator(mode='after')
    def _validate_mandatory_fields(self):
        if not self.product_number:
            self._add_validation_message(
                    source=f"Category {self.key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f'Category key {self.key} is missing mandatory field Product Number',
                    highlight_pattern = f"{self.key}"
            )
        return self
    
    @property
    def is_serialized(self) -> bool:
        return bool(self.batch_number or self.container_number or self.aliquot)
    
    
class Material_Consumable(PredefinedCategory):
    '''Represents the -MC category'''
    key: str = Field(default='-MC', frozen=True)
    product_number:str|None =   Field(              alias='240')
    batch_number:str|None =     Field(default=None, alias='10')
    packaging_size:str|None =     Field(default=None, alias='20')
    serial_number:str|None =    Field(default=None, alias='21')
    aliquot:str|None =          Field(default=None, alias='250')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    @model_validator(mode='after')
    def _validate_mandatory_fields(self):
        if not self.product_number:
            self._add_validation_message(
                    source=f"Category {self.key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f"Category key {self.key} is missing mandatory field 'Product Number'",
                    highlight_pattern = f"{self.key}"
            )
        return self
    
    @property
    def is_serialized(self) -> bool:
        return bool(self.batch_number or self.serial_number or self.aliquot)
    
    
class Material_Misc(Material_Consumable):
    '''Represents the -MX category'''
    # same fields as Consumable
    key: str = Field(default='-MX', frozen=True)
    product_number:str|None =   Field(              alias='240')
    batch_number:str|None =     Field(default=None, alias='10')
    packaging_size:str|None =     Field(default=None, alias='20')
    serial_number:str|None =    Field(default=None, alias='21')
    aliquot:str|None =          Field(default=None, alias='250')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    

    


## Data
class Data_Abstract(PredefinedCategory, ABC):
    '''@private'''
    key: str
    id:str|None =                    Field(              alias='21')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    @model_validator(mode='after')
    def _validate_mandatory_fields(self):
        if not self.id:
            self._add_validation_message(
                    source=f"Category {self.key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f"Category key {self.key} is missing mandatory field 'ID'",
                    highlight_pattern = f"{self.key}"
            )
        return self
    
    @property
    def is_serialized(self) -> bool:
        return True
    

class Data_Result(Data_Abstract):
    '''Represents the -DR category'''
    key: str = Field(default='-DR', frozen=True)
    id:str|None =                    Field(              alias='21')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    
class Data_Method(Data_Abstract):
    '''Represents the -DM category'''
    key: str = Field(default='-DM', frozen=True)
    id:str|None =                    Field(              alias='21')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    
class Data_Calibration(Data_Abstract):
    '''Represents the -DC category'''
    key: str = Field(default='-DC', frozen=True)
    id:str|None =                    Field(              alias='21')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    
class Data_Progress(Data_Abstract):
    '''Represents the -DP category'''
    key: str = Field(default='-DP', frozen=True)
    id:str|None =                    Field(              alias='21')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    
class Data_Static(Data_Abstract):
    '''Represents the -DS category'''
    key: str = Field(default='-DS', frozen=True)
    id:str|None =                    Field(              alias='21')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
class Data_Misc(Data_Abstract):
    '''Represents the -DX category'''
    key: str = Field(default='-DX', frozen=True)
    id:str|None =                    Field(              alias='21')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    



class Processor_Abstract(PredefinedCategory, ABC):
    '''@private'''
    key: str
    processor_instance:str|None =                    Field(              alias='21')
    processor_code:str|None =                        Field(              alias='240')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    @model_validator(mode='after')
    def _validate_mandatory_fields(self):
        if not self.processor_instance:
            self._add_validation_message(
                    source=f"Category {self.key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f"Category key {self.key} is missing mandatory field 'processor instance'",
                    highlight_pattern = f"{self.key}"
            )
        return self
    
    @property
    def is_serialized(self) -> bool:
        return bool(self.processor_instance)
    

class Processor_Software(Processor_Abstract):
    '''Represents the -PS category'''
    key: str = Field(default='-PS', frozen=True)
    processor_instance:str|None =                    Field(              alias='21')
    processor_code:str|None =                        Field(              alias='240')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''

class Processor_Misc(Processor_Abstract):
    '''Represents the -PX category'''
    key: str = Field(default='-PX', frozen=True)
    processor_instance:str|None =                    Field(              alias='21')
    processor_code:str|None =                        Field(              alias='240')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    
    
class Misc(PredefinedCategory, ABC):
    '''@private'''
    key: str = Field(default='-X', frozen=True)
    id:str|None =                    Field(              alias='21')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    @model_validator(mode='after')
    def _validate_mandatory_fields(self):
        if not self.id:
            self._add_validation_message(
                    source=f"Category {self.key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f"Category key {self.key} is missing mandatory field 'ID'",
                    highlight_pattern = f"{self.key}"
            )
        return self
    
    @property
    def is_serialized(self) -> bool:
        return bool(self.id)
    
    
    
category_key_to_class_map  = {
        '-MD': Material_Device,
        '-MS': Material_Substance,
        '-MC': Material_Consumable,
        '-MX': Material_Misc,
        '-DM': Data_Method,
        '-DR': Data_Result,
        '-DC': Data_Calibration,
        '-DP': Data_Progress,
        '-DS': Data_Static,
        '-DX': Data_Misc,
        '-PS': Processor_Software,
        '-PX': Processor_Misc,
        '-X':Misc
}