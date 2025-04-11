from enum import Enum, auto
import re
from pydantic import BaseModel, Field, PrivateAttr
from typing import List, Set, Tuple

from rich import print
from rich.text import Text
from rich.table import Table


domain_name_pattern = r"(?!-)([A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,63}"
hsegment_pattern = r"[A-Za-z0-9_\-\.~!$&'()+,:;=@]|%[0-9A-Fa-f]{2}"


class ValidationMsgLevel(Enum):
    ERROR = auto()
    ERROR_AUTO_FIX = auto()
    WARNING = auto()
    RECOMMENDATION = auto()
    INFO = auto()

class ValidationMessage(BaseModel):
    source_id:int
    source:str 
    level: ValidationMsgLevel
    problem_msg:str
    recommendation_msg: str = ""
    highlight:str = "" #this can be used to highlight problematic parts
    highlight_sub_patterns:list[str] = Field(default_factory=list)


    
        
        
    # @property
    # def emphazised_highlight(self):
    #     fmt = lambda s: f'[emph]{s}[/emph]'
        
    #     if not self.highlight_sub_patterns:
    #         return fmt(self.highlight)
          
    #     result = []
    #     for c in self.highlight:
    #         if c in self.highlight_sub_patterns:
    #             result.append(fmt(c))
    #         else:
    #             result.append(c)

    #     return ''.join(result)

    
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

    def add_validation_message(self, *, msg: str, level:ValidationMsgLevel, recommendation:str="", source:str="", highlight_pattern="", highlight_sub=None):
        if not highlight_sub:
            highlight_sub = []
        w = ValidationMessage(problem_msg=msg, recommendation_msg=recommendation, source=source, level=level, highlight=highlight_pattern, highlight_sub_patterns=highlight_sub, source_id=id(self))

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
    
    
    def str_for_validation_msg(self, validation_msg:ValidationMessage):
        if validation_msg.source_id == id(self):
            return validation_msg.source_id
            #return validation_msg.emphasize_in(self(str))
        else:
            return str(self)
        
    def str_highlighted(self):
        raise NotImplementedError("Subclasses must implement format_special()")
    
    
        
    def _emphasize_in(self, validation_msg, validation_node_str:str, fmt, color='black'):
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
    
    
    def print_validation_messages(self, target='console'):
        msgs = self.get_nested_validation_messages()
        
        table = Table(title=f"Validation Results", show_header=False)

        col = lambda s:  table.add_column(s, vertical='top')
        col("-")
        
             
        if not msgs:
            table.add_row('All clear!', end_section=True)
            return

        for m in msgs:
            if m.level == ValidationMsgLevel.ERROR:
                color = 'red'
            else:
                color = 'yellow'
                
            match target:
                case 'markdown':
                    fmt = lambda s: f'🔸{s}🔸'
                case 'console':     
                    fmt = lambda s: f'[{color} bold]{s}[/{color} bold]'
                case 'html':
                    fmt = lambda s: f'<span class="val_{color}">{s}</span>'
                case 'html_styled':
                    fmt = lambda s: f'<b style="color:{color}>{s}</b>'
                
            serialized = str(self)
            emphazised_highlight = self._emphasize_in(m, serialized, fmt=fmt, color=color)
            
            txt =       f'[bold {color}]{m.level.name} [/bold {color}]'
            txt += '\n' + f'{m.problem_msg}'
            txt += '\n' + emphazised_highlight

            table.add_row( txt)
            table.add_section()

        print(table)
    
    # def print_validation_messages_(self, str_to_highlight_in=None, target='console'):
    #     if not str_to_highlight_in:
    #         str_to_highlight_in = str(self)
    #     msgs = self.get_nested_validation_messages()
    #     print('\n'.join(['\n',
    #                      '=======================================',
    #                      'Validation Results',
    #                      '---------------------------------------'
    #                     ]
    #                     )
    #     )
        
    #     if not msgs:
    #         print('All clear!')
    #         return

    #     for m in msgs:
    #         if m.level.casefold() == "error":
    #             color = 'red'
    #         else:
    #             color = 'yellow'
                
    #         text = Text.from_markup(f'\n [bold {color}]{m.level} [/bold {color}] in \t {m.source}' )
    #         print(text)
    #         match target:
    #             case 'markdown':
    #                 formatted_highlight = m.emphazised_highlight.replace('emph', f'🔸').replace('[/', '').replace('[', '').replace(']', '')
    #             case 'console':     
    #                 formatted_highlight = m.emphazised_highlight.replace('emph', f'bold {color}')
    #             case 'html':
    #                 formatted_highlight = m.emphazised_highlight.replace('emph', f'b').replace('[', '<').replace(']', '>')
    #         fmtd = str_to_highlight_in.replace(m.highlight, formatted_highlight)
    #         fmtd = Text.from_markup(fmtd)
    #         print(fmtd)
    #         print(Text.from_markup(f'{m.problem_msg}'))
        
    
    
def filter_errors(val_msg:list[ValidationMessage]) -> list[ValidationMessage]:
    return [ m for m in val_msg if m.level == ValidationMsgLevel.ERROR ]

def filter_warnings(val_msg:list[ValidationMessage]) -> list[ValidationMessage]:
    return [ m for m in val_msg if m.level != ValidationMsgLevel.ERROR  ]     

