import re
from pydantic import model_validator
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, ValidationMsgLevel, _quote_texts
from labfreed.well_known_keys.labfreed.well_known_keys import WellKnownKeys


_hsegment_pattern = r"[A-Za-z0-9_\-\.~!$&'()+,:;=@]|%[0-9A-Fa-f]{2}"

class IDSegment(LabFREED_BaseModel):
    """ Represents an id segment of a PAC-ID. It can be a value or a key value pair.
    """
    key:str|None = None
    ''' The key of the segment. This is optional.'''
    value:str
    ''' The value of the segment. (mandatory)'''

    @property
    def is_derivation_namespace(self) -> bool:
        ''' Whether this segment is a derivation namespace segment (`+<namespace>`),
        introduced by a third party extending a PAC-ID. See PAC-ID spec, "Issuing derived PAC-ID"s.'''
        return self.key is None and self.value.startswith('+')

    @model_validator(mode="after")
    def _validate_segment(self):
        key = self.key or ""
        value = self.value

        # An id segment carries no information if its value is empty. This also catches
        # segments accidentally produced by a double or trailing '/' in the identifier.
        if not value:
            self._add_validation_message(
                    source="id segment",
                    level = ValidationMsgLevel.ERROR,
                    msg="id segment value must not be empty."
            )

        # MUST be a valid hsegment according to RFC 1738, but without * (see PAC-ID Extension)
        # This means it must be true for both, key and value
        if not_allowed_chars := set(re.sub(_hsegment_pattern, '', key)):
            self._add_validation_message(
                    source=f"id segment key {key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f"{_quote_texts(not_allowed_chars)} must not be used. The segment key must be a valid hsegment",
                    highlight_pattern = key,
                    highlight_sub = not_allowed_chars
            )

        if not_allowed_chars := set(re.sub(_hsegment_pattern, '', value)):
            self._add_validation_message(
                    source=f"id segment key {value}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f"{_quote_texts(not_allowed_chars)} must not be used. The segment key must be a valid hsegment",
                    highlight_pattern = value,
                    highlight_sub = not_allowed_chars
            )

        # Segment key SHOULD be limited to A-Z, 0-9, and -+..
        if not_recommended_chars := set(re.sub(r'[A-Z0-9+-]', '', key)):
            self._add_validation_message(
                    source=f"id segment key {key}",
                    level = ValidationMsgLevel.RECOMMENDATION,
                    msg=f"{_quote_texts(not_recommended_chars)} should not be used. Characters SHOULD be limited to upper case letters (A-Z), numbers (0-9), '-' and '+' ",
                    highlight_pattern = key,
                    highlight_sub = not_recommended_chars
                )

        # Segment key should be in Well know keys
        if key and key not in [k.value for k in WellKnownKeys]:
            self._add_validation_message(
                    source=f"id segment key {key}",
                    level = ValidationMsgLevel.RECOMMENDATION,
                    msg=f"{key} is not a well known segment key. It is RECOMMENDED to use well-known keys.",
                    highlight_pattern = key,
                    highlight_sub=[key]
                )


        # Segment value SHOULD be limited to A-Z, 0-9, and -+..
        if not_recommended_chars := set(re.sub(r'[A-Z0-9+-]', '', value)):
            self._add_validation_message(
                    source=f"id segment value {value}",
                    level = ValidationMsgLevel.RECOMMENDATION,
                    msg=f"Characters {_quote_texts(not_recommended_chars)} should not be used., Characters SHOULD be limited to upper case letters (A-Z), numbers (0-9), '-' and '+' ",
                    highlight_pattern = value,
                    highlight_sub = not_recommended_chars
                )

        # id segment key/value MUST NOT contain ':', since it is used to separate them.
        if ':' in key:
            self._add_validation_message(
                    source=f"id segment key {key}",
                    level = ValidationMsgLevel.ERROR,
                    msg="Character ':' must not be used in segment key, since this character is used to separate key and value.",
                    highlight_pattern = key
                )
        if ':' in value:
            self._add_validation_message(
                    source=f"id segment value {value}",
                    level = ValidationMsgLevel.ERROR,
                    msg="Character ':' must not be used in segment value, since this character is used to separate key and value.",
                    highlight_pattern = value
                )

        return self