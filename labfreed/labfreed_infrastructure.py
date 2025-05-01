from enum import Enum, auto
import logging
import re
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from typing import Any, List, Set

from rich import print
from rich.table import Table

''' Configure pdoc'''
__all__ = ["LabFREED_BaseModel", "ValidationMessage", "ValidationMsgLevel", "LabFREED_ValidationError"]

class PDOC_Workaround_Base(BaseModel):
    '''@private
    This class only exists to make pdoc work better with Pydantic models. It is set up such, that some things are not showing up in docu
    '''
    model_config = ConfigDict(extra="forbid")
    """@private"""
    def model_post_init(self, context: Any) -> None:
        '''@private'''
        super().model_post_init(context)





class ValidationMsgLevel(Enum):
    '''
    Level of validation messages
    '''
    ERROR = auto() 
    '''Model is **invalid**'''
    WARNING = auto() 
    '''Model is **valid**, but has issues'''
    RECOMMENDATION = auto()
    '''Model is **valid**, but recommendations apply'''
    INFO = auto()
    '''Model is **valid**. Something of interest was detected, which is not a recommendation.'''

class ValidationMessage(PDOC_Workaround_Base):
    '''
    Represents one problem in the model
    '''
    source_id:int
    source:str 
    level: ValidationMsgLevel
    msg:str
    highlight:str = "" #this can be used to highlight problematic parts
    highlight_sub_patterns:list[str] = Field(default_factory=list)

    @field_validator('highlight_sub_patterns', mode='before')
    @classmethod
    def _ensure_list(cls, v):
        if isinstance(v, str):
            return [v]
        return v


    
class LabFREED_ValidationError(ValueError):
    '''Error which is raised, when LabFREED validation fails, i.e. when the model contains at least one error.'''
    
    def __init__(self, message=None, validation_msgs=None):
        '''@private'''
        super().__init__(message)
        self._validation_msgs = validation_msgs

    @property
    def validation_msgs(self):
        ''' The validation messages (errors, recommendations, info) present in the invalid model'''
        return self._validation_msgs
    
    


class LabFREED_BaseModel(PDOC_Workaround_Base):
    """ Extension of Pydantic BaseModel, so that validator can issue warnings.
    The purpose of that is to allow only minimal validation but on top check for stricter recommendations"""
    
    _validation_messages: list[ValidationMessage] = PrivateAttr(default_factory=list)
    """Validation messages for this model"""
    
    @property
    def is_valid(self) -> bool:
        return len(self.errors()) == 0
    

    def validation_messages(self, nested=True) -> list[ValidationMessage]:
        if nested:
            msgs = self._get_nested_validation_messages()
        else:
            msgs = self._validation_messages
        return msgs
    
    def errors(self, nested=True) -> list[ValidationMessage]: 
        return _filter_errors(self.validation_messages(nested=nested))
    
    def warnings(self, nested=True) -> list[ValidationMessage]: 
        return _filter_warnings(self.validation_messages(nested=nested))
    

    def _add_validation_message(self, *, msg: str, level:ValidationMsgLevel, source:str="", highlight_pattern="", highlight_sub=None):
        if not highlight_sub:
            highlight_sub = []
        w = ValidationMessage(msg=msg, source=source, level=level, highlight=highlight_pattern, highlight_sub_patterns=highlight_sub, source_id=id(self))

        if w not in self._validation_messages:
            self._validation_messages.append(w)

    # Function to extract warnings from a model and its nested models
    def _get_nested_validation_messages(self, parent_name: str = "", visited: Set[int] = None) -> List['ValidationMessage']:
        """
        Recursively extract warnings from a Pydantic model and its nested fields, including computed fields.

        :param parent_name: The name of the parent model to track the path.
        :param visited: Set of visited object IDs to prevent infinite loops.
        :return: List of ValidationMessages from this and nested models.
        """
        if visited is None:
            visited = set()

        model_id = id(self)
        if model_id in visited:
            return []
        visited.add(model_id)

        warnings_list = [warning for warning in self.validation_messages(nested=False)]

        # Traverse regular fields
        for field_name, field in self.__fields__.items():
            full_path = f"{parent_name}.{field_name}" if parent_name else field_name
            value = getattr(self, field_name)

            if isinstance(value, LabFREED_BaseModel):
                warnings_list.extend(value._get_nested_validation_messages(full_path, visited))
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    if isinstance(item, LabFREED_BaseModel):
                        list_path = f"{full_path}[{index}]"
                        warnings_list.extend(item._get_nested_validation_messages(list_path, visited))

        # Traverse computed fields
        computed_fields = getattr(self, '__pydantic_decorators__', {}).computed_fields or {}
        for field_name in computed_fields:
            full_path = f"{parent_name}.{field_name}" if parent_name else field_name
            try:
                value = getattr(self, field_name)
            except Exception:
                continue  # Safely skip computed properties that raise errors

            if isinstance(value, LabFREED_BaseModel):
                warnings_list.extend(value._get_nested_validation_messages(full_path, visited))
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    if isinstance(item, LabFREED_BaseModel):
                        list_path = f"{full_path}[{index}]"
                        warnings_list.extend(item._get_nested_validation_messages(list_path, visited))

        return warnings_list
        

    
    def print_validation_messages(self, target='console'):
        msgs = self.format_validation_messages(target=target)
        
        table = Table(title="Validation Results", show_header=False, title_justify='left')

        def col(s):
            return table.add_column(s, vertical='top')
        col("-")
        
        if not msgs:
            table.add_row('All clear!', end_section=True)
            return

        for m in msgs:
            table.add_row(m)
            table.add_section()

        logging.info(table)
        print(table)
        return table
        
        
    def format_validation_messages(self, target='console') -> list[str]:
        """Format validation messages

        Args:
            target (str, optional): Target format: 'markdown', 'console', 'html', 'html_styled'.

        Returns:
            list[str]: formated messages
        """
        formatted_msg = list()
        for m in self.validation_messages():
            if m.level == ValidationMsgLevel.ERROR:
                color = 'red'
            else:
                color = 'yellow'
                
            match target:
                case 'markdown':
                    fmt = lambda s: f'👉{s}👈'  # noqa: E731
                    fmt_title = lambda s: f'**{s}**'  # noqa: E731
                    br = '\n'
                case 'console':     
                    fmt = lambda s: f'[{color} bold]{s}[/{color} bold]'  # noqa: E731
                    fmt_title = fmt
                    br = '\n'
                case 'html':
                    lvl = m.level.name.lower()
                    fmt = lambda s: f'<span class="validation-problem {lvl}">{s}</span>'  # noqa: E731
                    fmt_title = lambda s: f'<span class="validation-title {lvl}">{s}</span>'  # noqa: E731
                    br = '<br>'
                case 'html_styled':
                    fmt = lambda s: f'<b style="color:{color}">{s}</b>'  # noqa: E731
                    fmt_title = fmt
                    br = '<br>'
                
            serialized = str(self)
            emphazised_highlight = self._emphasize_in(m, serialized, fmt=fmt)
            emphazised_highlight = emphazised_highlight.replace('👈👉','') # removes two consecutive markers, to make it cleaner
            
            txt =   f'{fmt_title(m.level.name)} in {m.source}'
            txt += br + f'{m.msg}'
            txt += br+br + emphazised_highlight
            
            formatted_msg.append(txt)
        return formatted_msg
    
    def _emphasize_in(self, validation_msg, validation_node_str:str, fmt):
        if validation_msg.highlight_sub_patterns:
            replacements = validation_msg.highlight_sub_patterns
        else:
            replacements = [validation_msg.highlight]
        # Sort patterns by length descending to avoid subpattern clobbering
        sorted_patterns = sorted(replacements, key=len, reverse=True)
        # Escape the patterns for regex safety
        escaped_patterns = [re.escape(p) for p in sorted_patterns]
        # Create one regex pattern with alternation (longest first)
        pattern = re.compile("|".join(escaped_patterns))
        
        out = pattern.sub(lambda m: fmt(m.group(0)), validation_node_str)
        return out
            

    
def _filter_errors(val_msg:list[ValidationMessage]) -> list[ValidationMessage]:
    return [ m for m in val_msg if m.level == ValidationMsgLevel.ERROR ]

def _filter_warnings(val_msg:list[ValidationMessage]) -> list[ValidationMessage]:
    return [ m for m in val_msg if m.level != ValidationMsgLevel.ERROR  ]     

def _quote_texts(texts:list[str]):
    return ','.join([f"'{t}'" for t in texts])


