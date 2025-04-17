from enum import Enum
from functools import cache
import re
from typing import Self
from pydantic import Field, field_validator, model_validator
import yaml
import jsonpath_ng.ext as jsonpath


from labfreed.pac_id_resolver.services import Service, ServiceGroup
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, ValidationMsgLevel, _quote_texts

__all__ = [
    "CIT_v2",
    "CITBlock_v2",
    "CITEntry_v2"
]

class ServiceType(Enum):
    USER_HANDOVER_GENERIC = 'userhandover-generic'
    ATTRIBUTE_SERVICE_GENERIC = 'attributes-generic'


class CITEntry_v2(LabFREED_BaseModel):
    service_name: str
    application_intents:list[str]
    service_type:ServiceType |str
    template_url:str
    
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
        allowed_types = [ServiceType.ATTRIBUTE_SERVICE_GENERIC.value, ServiceType.USER_HANDOVER_GENERIC.value]
        if self.service_type not in allowed_types:
            if isinstance(self.service_type, ServiceType):
                s= self.service_type.value
            else:
                s= self.service_type
            for at in allowed_types:
                s = s.replace(at,'')
            self._add_validation_message(
                level=ValidationMsgLevel.ERROR,
                source=f'Service Type  {self.service_type}',
                msg=f'Invalid service type. Must be {_quote_texts(allowed_types)} must be at least one and maximum 255 characters long',
                highlight_sub=s
                )
        return self
    
    

class CITBlock_v2(LabFREED_BaseModel):
    applicable_if: str  = Field(default='True', alias='if')
    entries: list[CITEntry_v2]
    
    @field_validator('applicable_if', mode='before')
    @classmethod
    def _convert_if(cls, v):
        return v if v is not None else 'True'
    
    


class CIT_v2(LabFREED_BaseModel):
    '''Coupling Information Table (CIT)'''
    origin: str = ''
    model_config = {
        "extra": "allow"
    }
    '''@private'''
    cit: list[CITBlock_v2] = Field(default_factory=list)
    
    @model_validator(mode='after')
    def _validate_origin(self):
        if len(self.origin) == 0:
            self._add_validation_message(level=ValidationMsgLevel.WARNING,
                                        source='CIT origin',
                                        msg='Origin should not be empty'
                                        )
        return self
    
    
    @classmethod
    def from_yaml(cls, yml:str) -> Self:
        return cls.model_validate(yml)
    
    def __str__(self):
        yml = yaml.dump(self.model_dump()                        )
        return yml
    
    def evaluate_pac_id(self, pac_id_json):
        cit_evaluated = ServiceGroup(origin=self.origin)   
        for block in self.cit:
            _, is_applicable = self._evaluate_applicable_if(pac_id_json, block.applicable_if)
            if not is_applicable:
                continue

            for e in block.entries:
                url = self._eval_url_template(pac_id_json, e.template_url)
                cit_evaluated.services.append(Service(  
                                                        service_name=e.service_name,
                                                        application_intents=e.application_intents,
                                                        service_type=e.service_type,
                                                        url = url
                                    )
                              )            
        return cit_evaluated
    
    
    def _evaluate_applicable_if(self, pac_id_json:str, expression) -> tuple[str, bool]:
        expression = self._apply_convenience_substitutions(expression)
        
        tokens = self._tokenize_jsonpath_expression(expression)
        expression_for_eval = self._expression_from_tokens(pac_id_json, tokens)
        applicable = eval(expression_for_eval, {}, {})
        
        return expression_for_eval, applicable
    
    
    def _apply_convenience_substitutions(self, query):
        ''' applies a few substitutions, which enable abbreviated syntax.'''
        
        # allow access to array elements by key
        q_mod = re.sub(r"\[('.+?')\]", r"[?(@.key == \1)]", query )
        
        # allow shorter path
        # substitutions = [
        #     (r'(?<=^)id', 'pac.id'),
        #     (r'(?<=^)cat', 'pac.id.cat'),
        #     (r'(?<=\.)id(?=\.)', 'identifier'),
        #     (r'(?<=\.)cat$', 'categories'),
        #     (r'(?<=\.)cat(?=\[)', 'categories'),
        #     (r'(?<=\.)seg$', 'segments'),
        #     (r'(?<=\.)seg(?=\[)', 'segments'),
        #     (r'(?<=^)isu', 'pac.isu'),
        #     (r'(?<=\.)isu', 'issuer'),
        #     (r'(?<=^)ext', 'pac.ext'),
        #     (r'(?<=\.)ext(?=$)', 'extensions'),
        #     (r'(?<=\.)ext(?=\[)', 'extensions'),
        # ]
        # for sub in substitutions:
        #     q_mod = re.sub(sub[0], sub[1], q_mod)
        
        return q_mod
    

    def _tokenize_jsonpath_expression(self, expr: str):
        token_pattern = re.compile(
            r"""
            (?P<LPAREN>\() |
            (?P<RPAREN>\)) |
            (?P<LOGIC>\bAND\b|\bOR\b|\bNOT\b) |
            (?P<OPERATOR>==|!=|<=|>=|<|>) |
            (?P<JSONPATH>
                \$                               # starts with $
                (?:
                    [^\s\[\]()]+                # path segments, dots, etc.
                    |
                    \[                           # open bracket
                        (?:                     # non-capturing group
                            [^\[\]]+            # anything but brackets
                            |
                            \[[^\[\]]*\]        # nested brackets (1 level)
                        )*
                    \]
                )+                              # one or more bracket/segment blocks
            ) |
            (?P<LITERAL>
                [A-Za-z_][\w\.\-]*[A-Za-z0-9]   # domain-like literals
            )
            """,
            re.VERBOSE
        )

        tokens = []
        pos = 0
        while pos < len(expr):
            match = token_pattern.match(expr, pos)
            if match:
                group_type = match.lastgroup
                value = match.group().strip()
                tokens.append((value, group_type))
                pos = match.end()
            elif expr[pos].isspace():
                pos += 1  # skip whitespace
            else:
                raise SyntaxError(f"Unexpected character at position {pos}: {expr[pos]}")

        return tokens
    
    
    def _expression_from_tokens(self, pac_id_json:str, tokens: tuple[str, str]):
        out  = []
        for i in range(len(tokens)):
            prev_token = tokens[i-1] if i > 0 else (None, None)
            curr_token = tokens[i]
            next_token = tokens[i+1] if i < len(tokens)-1 else (None, None)
            if curr_token[1] == 'JSONPATH':
                res = self._evaluate_jsonpath(pac_id_json, curr_token[0])
                
                if prev_token[1] == 'OPERATOR' or next_token[1] == 'OPERATOR':
                    # if token is part of comparison return the value of the node
                    if len(res) == 0:
                        out.append('""')
                    else:
                        out.append(f'"{res[0].upper()}"')
                else:
                    # if token is not part of comparison evaluate to boolean
                    if len(res) == 0:
                        out.append(False)
                    else:
                        out.append(True)
                        
            elif curr_token[1] == 'LOGIC':
                out.append(curr_token[0].lower())  
                
            elif curr_token[1] == 'LITERAL':
                t = curr_token[0]
                if t[0] != '"':
                    t = '"' + t
                if t[-1] != '"':
                    t = t + '"' 
                out.append(t.upper())    
            else:
                out.append(curr_token[0])
                
        s = ' '.join([str(e) for e in out])
        return s
                    

    
    
    def _eval_url_template(self, pac_id_json, url_template):
        url = url_template
        placeholders = re.findall(r'\{(.+?)\}', url_template)
        for placeholder in placeholders:
            expanded_placeholder = self._apply_convenience_substitutions(placeholder)
            res = self._evaluate_jsonpath(pac_id_json, expanded_placeholder) or ['']
            url = url.replace(f'{{{placeholder}}}', str(res[0]))
            # res = self.substitute_jsonpath_expressions(expanded_placeholder, Patterns.jsonpath.value, as_bool=False)
            # url = url.replace(f'{{{placeholder}}}', res)
        return url
    

    
    def _evaluate_jsonpath(self, pac_id_json, jp_query):
        jsonpath_expr = jsonpath.parse(jp_query)
        matches = [match.value for match in jsonpath_expr.find(pac_id_json)]
        return matches
    
    

    
    
    
