import re
from typing import   Any, Self
from urllib.parse import unquote
from deprecated import deprecated
from werkzeug.datastructures import LanguageAccept
from werkzeug.http import parse_accept_header
from pydantic import AnyUrl, ConfigDict, TypeAdapter, field_validator, model_validator
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, LabFREED_ValidationError, ValidationMsgLevel
from labfreed.pac_id.pac_id import PAC_ID

ATTR_GROUPS = 'attr_grps'
ATTR_GROUPS_FWD_LKP= 'attr_fwd_lkp'
ATTR_GROUPS_DERIVATION_LKP = 'attr_deriv_lkp'


class AttributeRequestData(LabFREED_BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    subject_id: str
    language_preferences: LanguageAccept|None = None
    restrict_to_attribute_groups: list[str]|None = None
    do_forward_lookup: bool = True
    do_derivation_lookup: bool = True
    '''If subject_id is a derived PAC-ID - either a third party's derivation, marked
    with `+<namespace>`, or the issuing party's own derivation (no marker needed) -
    also include the attributes of its immediate parent PAC-ID in the response,
    under the parent's own id. See AttributeServerRequestHandler._get_derivation_parent_id().'''
    
    def as_json(self):
        return self.model_dump_json()
    
    @classmethod
    def from_json(cls, json) -> Self:
        return cls.model_validate_json(json)
    
    @classmethod
    def from_http_request(cls, id:str, params:dict, headers:dict):
        # Azure seems to meddle with double slashes in a path, even if url encoded. This is to rectify this behaviour and add back a second slash if necessary
        id = re.sub('HTTPS:/{1,2}', 'HTTPS://', id, flags=re.IGNORECASE)
        
        restrict_to_attribute_groups = params.get(ATTR_GROUPS)
        if restrict_to_attribute_groups == '':
            restrict_to_attribute_groups = None
        if restrict_to_attribute_groups:
            restrict_to_attribute_groups = restrict_to_attribute_groups.split(',')
            
        fwd_lkp = params.get(ATTR_GROUPS_FWD_LKP, True)
        if fwd_lkp is True:
            do_forward_lookup = True
        else:
            do_forward_lookup =  fwd_lkp.lower() not in ['false', 'no', '0', 'n', 'off']

        deriv_lkp = params.get(ATTR_GROUPS_DERIVATION_LKP, True)
        if deriv_lkp is True:
            do_derivation_lookup = True
        else:
            do_derivation_lookup = deriv_lkp.lower() not in ['false', 'no', '0', 'n', 'off']

        lang_hdr = headers.get('Accept-Language')
        language_preferences: LanguageAccept = parse_accept_header(lang_hdr, LanguageAccept)
        out = cls(  subject_id=id,
                    restrict_to_attribute_groups = restrict_to_attribute_groups,
                    do_forward_lookup = do_forward_lookup,
                    do_derivation_lookup = do_derivation_lookup,
                    language_preferences=language_preferences
                    )
        return out
        

    @model_validator(mode="before")
    @classmethod
    # field pac-id was renamed to subject-id. This is for backward compatibility.
    def _rename_to_subject_id(cls, d):
        if pac_id := d.pop('pac_id', None):
            d['subject_id'] = pac_id
        return d
    
    @property
    @deprecated(" field pac_id was renamed to subject_id.")
    def pac_id(self):
        # field pac_id was renamed to subject_id. This is for backward compatibility.
        return self.subject_id
        
    
    @model_validator(mode="before")
    @classmethod
    def _scalars_to_list(cls, d):
        if isinstance(lp:= d.get("language_preferences"), str):
            d["language_preferences"] = [lp]
        if isinstance(rag := d.get("restrict_to_attribute_groups"), str):
            d["restrict_to_attribute_groups"] = [rag]
        return d
    
    
    @field_validator('language_preferences', mode='before')
    @classmethod
    def convert_language_preferences(cls,lp):
        if lp is None or isinstance(lp, LanguageAccept):
            return lp
        lq = [(lng, 1-i/len(lp)) for i, lng in enumerate(lp)]
        return LanguageAccept(lq)
        
    
    @model_validator(mode="after")
    def _revert_url_encoding(self):
        self.subject_id = unquote(self.subject_id)
        if self.restrict_to_attribute_groups:
            self.restrict_to_attribute_groups = [unquote(g) for g in self.restrict_to_attribute_groups]
        return self
           
    @model_validator(mode="after")
    def _validate_subject_id(self) -> Self: 
         # validate if subject_id is un url. this approximates the requirement for it to be an IRI
        try:
            TypeAdapter(AnyUrl).validate_python(self.subject_id)
        except Exception:
            self._add_validation_message(
                    source="subject_id",
                    level = ValidationMsgLevel.ERROR,
                    msg=f'{self.subject_id} is not a valid IRI'
                )
            
        # validate the recommendation for subject_id to be a pac-id.
        # suppress_validation_errors=True so this doesn't also log an ERROR - not being a
        # valid PAC-ID is only a WARNING here, and is the expected, routine case for a
        # subject_id that's a generic IRI rather than a PAC-ID. Still need the try/except
        # around it: a subject_id that doesn't even match the "issuer/identifier" shape
        # (e.g. no '/' at all) makes PAC_ID.from_url() raise unconditionally, regardless
        # of suppress_validation_errors.
        try:
            pac_id_is_valid = PAC_ID.from_url(self.subject_id, suppress_validation_errors=True).is_valid
        except LabFREED_ValidationError:
            pac_id_is_valid = False
        if not pac_id_is_valid:
            self._add_validation_message(
                    source="subject_id",
                    level = ValidationMsgLevel.WARNING,
                    msg=f'{self.subject_id} is not a valid PAC-ID'
                )
            
       
                
        if not self.is_valid:
            raise LabFREED_ValidationError(message='Invalid request', validation_msgs=self.validation_messages())
                
        return self
    
    def language_preference_http_header(self) -> dict[str, str]:
        if not self.language_preferences:
            return {}
        headers={'Accept-Language':  LanguageAccept(self.language_preferences).to_header()}
        return headers
    
    def request_params(self) -> dict[str, Any]:
        params = {
            ATTR_GROUPS_FWD_LKP: str(self.do_forward_lookup).lower(),
            ATTR_GROUPS_DERIVATION_LKP: str(self.do_derivation_lookup).lower(),
        }
        if self.restrict_to_attribute_groups:
            params.update({ATTR_GROUPS: ','.join(self.restrict_to_attribute_groups)})
        return params
        
    
    
