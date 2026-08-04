import re
from typing import Literal, Self
from pydantic import Field, field_validator, model_validator
import yaml

from labfreed.labfreed_infrastructure import LabFREED_BaseModel, ValidationMsgLevel, _quote_texts
from labfreed.pac_id_resolver.resolver_config_common import ( ServiceType)


__all__ = [
    "ResolverConfig",
    "ResolverConfigBlock",
    "ResolverConfigEntry"
]



class ResolverConfigEntry(LabFREED_BaseModel):
    # CIT entries are meant to stay forward-compatible as the resolver config format
    # evolves (new service_type-specific fields, vendor extensions) - an unrecognized
    # field must not hard-crash resolution of an otherwise-valid PAC-ID. Overrides the
    # `extra="forbid"` inherited from LabFREED_BaseModel/PDOC_Workaround_Base, same
    # opt-in ResolverConfig itself already uses.
    model_config = {"extra": "allow"}

    service_name: str
    application_intents:list[str]
    service_type:ServiceType |str
    template_url:str
    key: str | None = Field(default=None)

    @model_validator(mode='after')
    def _validate_no_unknown_fields(self):
        for extra_key in (self.model_extra or {}):
            self._add_validation_message(
                level=ValidationMsgLevel.WARNING,
                source=f'Service {self.service_name}',
                msg=f'Unrecognized field {extra_key!r} - ignored by this version of the resolver.',
                highlight_sub=[extra_key]
            )
        return self

    @model_validator(mode='after')
    def _validate_key(self):
        # key classifies *what this entry is* (e.g. "this is a Material Safety Data
        # Sheet") via a shared, IRI-anchored vocabulary term - the same "key" concept
        # PAC-ID Attributes already uses for its own attribute keys - as opposed to
        # application_intents (a short, free-text string identifying *which use case
        # picks this entry*). The two are orthogonal, see README.md's "Key".
        if self.key is not None and not re.match(r'^[a-zA-Z][a-zA-Z0-9+.\-]*:\S+$', self.key):
            self._add_validation_message(
                level=ValidationMsgLevel.ERROR,
                source=f'Service {self.service_name}',
                msg=f'key must be an absolute IRI (e.g. "https://www.wikidata.org/wiki/Q222067" for "Safety Data Sheet", per PAC-ID Attributes\' well_known_keys.md), got {self.key!r}',
                highlight_sub=[self.key]
            )
        return self

    @model_validator(mode='after')
    def _validate_service_name(self):
        # service_name
        if not_allowed_chars := set(re.sub(r'[A-Za-z0-9\-\x20]', '', self.service_name)):
            self._add_validation_message(
                level=ValidationMsgLevel.ERROR,
                source=f'Service {self.service_name}',
                msg=f'Service name ontains invalid characters {_quote_texts(not_allowed_chars)}',
                highlight_sub=not_allowed_chars
            )
        
        if len(self.service_name) == 0 or len(self.service_name) > 255:
             self._add_validation_message(
                level=ValidationMsgLevel.ERROR,
                source=f'Service {self.service_name}',
                msg='Service name must be at least one and maximum 255 characters long'
                )
        return self
        
    
    @model_validator(mode='after')
    def _validate_application_intent(self):
        for intent in self.application_intents:
            if re.fullmatch('.*-generic$',  intent):
                self._add_validation_message(
                level=ValidationMsgLevel.ERROR,
                source=f'Application intent {intent}',
                msg="Ends with '-generic'. This is not permitted, since it is reserved for future uses'",
                highlight_sub=[intent]
                )

            if not_allowed_chars := set(re.sub(r'[A-Za-z0-9\-]', '', intent)):
                self._add_validation_message(
                    level=ValidationMsgLevel.ERROR,
                    source=f'Application intent {self.service_name}',
                    msg=f'Contains invalid characters {_quote_texts(not_allowed_chars)}',
                    highlight_sub=not_allowed_chars
                )
                
            if len(intent) == 0 or len(intent) > 255:
                self._add_validation_message(
                    level=ValidationMsgLevel.ERROR,
                    source=f'Application intent  {intent}',
                    msg='Must be at least one and maximum 255 characters long'
                    )
        return self
    
    @model_validator(mode='after')
    def _validate_service_type(self):
        allowed_types = [ServiceType.ATTRIBUTE_SERVICE_GENERIC, ServiceType.USER_HANDOVER_GENERIC, ServiceType.ACTION_GENERIC]
        service_type_value = self.service_type
        if service_type_value not in allowed_types:
            s = service_type_value
            for at in allowed_types:
                s = s.replace(at,'')
            self._add_validation_message(
                level=ValidationMsgLevel.ERROR,
                source=f'Service Type  {self.service_type}',
                msg=f'Invalid service type. Must be {_quote_texts(allowed_types)} must be at least one and maximum 255 characters long',
                highlight_sub=s
                )
        return self
    
    

class ResolverConfigBlock(LabFREED_BaseModel):
    applicable_if: str  = Field(default='True', alias='if')
    entries: list[ResolverConfigEntry]
    
    @field_validator('applicable_if', mode='before')
    @classmethod
    def _convert_if(cls, v):
        if v is None:
            return 'True'
        if isinstance(v, bool):
            return str(v)
        return v
    
    


class ResolverConfig(LabFREED_BaseModel):
    schema_version: Literal["2.0"] = Field(default='2.0')
    '''Resolver Configuration'''
    origin: str = ''
    model_config = {
        "extra": "allow"
    }
    '''@private'''
    config: list[ResolverConfigBlock] = Field(default_factory=list)
    
    @model_validator(mode='after')
    def _validate_origin(self):
        if len(self.origin) == 0:
            self._add_validation_message(level=ValidationMsgLevel.WARNING,
                                        source='ResolverConfig origin',
                                        msg='Origin should not be empty'
                                        )
        return self
    
    
    @classmethod
    def from_yaml(cls, yml:str) -> Self:
        try:
            d = yaml.safe_load(yml)
        except yaml.YAMLError as e:
            # not a valid yaml
            raise ValueError("This is not a valid yaml") from e
        return cls.model_validate(d)
    
    def __str__(self):
        yml = yaml.dump(self.model_dump()                        )
        return yml
     
    # hash and equal are only used to avoid adding the same resolver config multiple times. 
    # we can live with some instances, where it does not work 
    def __hash__(self):
        return self.model_dump_json().__hash__()
    
    def __eq__(self, other):
        if not isinstance(other, ResolverConfig):
            return False
        return self.model_dump() == other.model_dump()
    
    
    def evaluate_pac_id(self, pac, client_info: dict | None = None):
        from labfreed.pac_id_resolver.resolver_config_evaluator import ResolverConfigEvaluator
        return ResolverConfigEvaluator(self).evaluate(pac, client_info=client_info)

