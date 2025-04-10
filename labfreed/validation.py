from pydantic import BaseModel, Field, PrivateAttr
from typing import List, Set, Tuple

from rich import print
from rich.text import Text


domain_name_pattern = r"(?!-)([A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,63}"
hsegment_pattern = r"[A-Za-z0-9_\-\.~!$&'()+,:;=@]|%[0-9A-Fa-f]{2}"


class ValidationMessage(BaseModel):
    source:str 
    type: str
    problem_msg:str
    recommendation_msg: str = ""
    highlight:str = "" #this can be used to highlight problematic parts
    highlight_sub:list[str] = Field(default_factory=list)
        
    @property
    def emphazised_highlight(self):
        fmt = lambda s: f'[emph]{s}[/emph]'
        
        if not self.highlight_sub:
            return fmt(self.highlight)
          
        result = []
        for c in self.highlight:
            if c in self.highlight_sub:
                result.append(fmt(c))
            else:
                result.append(c)

        return ''.join(result)

    
class LabFREEDValidationError(ValueError):
    def __init__(self, message=None, validation_msgs=None):
        super().__init__(message)
        self._validation_msgs = validation_msgs

    @property
    def validation_msgs(self):
        return self._validation_msgs
    
    


class BaseModelWithValidationMessages(BaseModel):
    """ Extension of Pydantic BaseModel, so that validator can issue warnings.
    The purpose of that is to allow only minimal validation but on top check for stricter recommendations"""
    _validation_messages: list[ValidationMessage] = PrivateAttr(default_factory=list)

    def add_validation_message(self, *, msg: str, type:str, recommendation:str="", source:str="", highlight_pattern="", highlight_sub=None):
        if not highlight_sub:
            highlight_sub = []
        w = ValidationMessage(problem_msg=msg, recommendation_msg=recommendation, source=source, type=type, highlight=highlight_pattern, highlight_sub=highlight_sub)

        if not w in self._validation_messages:
            self._validation_messages.append(w)

    def get_validation_messages(self) -> list[ValidationMessage]:
        return self._validation_messages
    
    def get_errors(self) -> list[ValidationMessage]: 
        return filter_errors(self._validation_messages)
    
    def get_warnings(self) -> list[ValidationMessage]: 
        return filter_warnings(self._validation_messages)
    
    def is_valid(self) -> bool:
        return len(filter_errors(self.get_nested_validation_messages())) == 0

    # Function to extract warnings from a model and its nested models
    def get_nested_validation_messages(self, parent_name: str = "", visited: Set[int] = None) -> List[ValidationMessage]:
        """
        Recursively extract warnings from a Pydantic model and its nested fields.
        
        :param model: The Pydantic model instance to inspect.
        :param parent_name: The name of the parent model to track the path.
        :return: List of tuples containing (model name, warning message).
        """                   
        if visited is None:
            visited = set()

        model_id = id(self)
        if model_id in visited:
            return []
        visited.add(model_id)
        
        warnings_list = [warning for warning in self.get_validation_messages()]
        # warnings_list = [(parent_name or self.__class__.__name__, model_id,  warning) for warning in self.get_validation_messages()]


        for field_name, field in self.__fields__.items():
            full_path = f"{parent_name}.{field_name}" if parent_name else field_name
            value = getattr(self, field_name)

            if isinstance(value, BaseModelWithValidationMessages):
                warnings_list.extend(value.get_nested_validation_messages(full_path, visited))
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    if isinstance(item, BaseModelWithValidationMessages):
                        list_path = f"{full_path}[{index}]"
                        warnings_list.extend(item.get_nested_validation_messages(list_path, visited))
        return warnings_list
    
    
    def get_nested_errors(self) -> list[ValidationMessage]: 
        return filter_errors(self.get_nested_validation_messages())
    
    def get_nested_warnings(self) -> list[ValidationMessage]: 
        return filter_warnings(self.get_nested_validation_messages())
    
    
    def print_validation_messages(self, str_to_highlight_in=None, target='console'):
        if not str_to_highlight_in:
            str_to_highlight_in = str(self)
        msgs = self.get_nested_validation_messages()
        print('\n'.join(['\n',
                         '=======================================',
                         'Validation Results',
                         '---------------------------------------'
                        ]
                        )
        )
        
        if not msgs:
            print('All clear!')
            return

        for m in msgs:
            if m.type.casefold() == "error":
                color = 'red'
            else:
                color = 'yellow'
                
            text = Text.from_markup(f'\n [bold {color}]{m.type} [/bold {color}] in \t {m.source}' )
            print(text)
            match target:
                case 'markdown':
                    formatted_highlight = m.emphazised_highlight.replace('emph', f'🔸').replace('[/', '').replace('[', '').replace(']', '')
                case 'console':     
                    formatted_highlight = m.emphazised_highlight.replace('emph', f'bold {color}')
                case 'html':
                    formatted_highlight = m.emphazised_highlight.replace('emph', f'b').replace('[', '<').replace(']', '>')
            fmtd = str_to_highlight_in.replace(m.highlight, formatted_highlight)
            fmtd = Text.from_markup(fmtd)
            print(fmtd)
            print(Text.from_markup(f'{m.problem_msg}'))
        
    
    
def filter_errors(val_msg:list[ValidationMessage]) -> list[ValidationMessage]:
    return [ m for m in val_msg if m.type.casefold() == "error" ]

def filter_warnings(val_msg:list[ValidationMessage]) -> list[ValidationMessage]:
    return [ m for m in val_msg if m.type.casefold() != "error" ]     

