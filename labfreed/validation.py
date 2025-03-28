from pydantic import BaseModel, Field, PrivateAttr
from typing import List, Set, Tuple


domain_name_pattern = r"(?!-)([A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,63}"
hsegment_pattern = r"[A-Za-z0-9_\-\.~!$&'()+,:;=@]|%[0-9A-Fa-f]{2}"


class ValidationWarning(BaseModel):
    source:str 
    type: str
    problem_msg:str
    recommendation_msg: str = ""
    highlight:str = "" #this can be used to highlight problematic parts
    highlight_sub:list[str] = Field(default_factory=list())
    
    


class BaseModelWithWarnings(BaseModel):
    """ Extension of Pydantic BaseModel, so that validator can issue warnings.
    The purpose of that is to allow only minimal validation but on top check for stricter recommendations"""
    _warnings: list[ValidationWarning] = PrivateAttr(default_factory=list)

    def add_warning(self, *, msg: str, type:str, recommendation:str="", source:str="", highlight_pattern="", highlight_sub=None):
        if not highlight_sub:
            highlight_sub = []
        w = ValidationWarning(problem_msg=msg, recommendation_msg=recommendation, source=source, type=type, highlight=highlight_pattern, highlight_sub=highlight_sub)
        if not w in self._warnings:
            self._warnings.append(w)

    def get_warnings(self) -> list[ValidationWarning]:
        return self._warnings

    def clear_warnings(self):
        self._warnings.clear()
    
    
# Function to extract warnings from a model and its nested models
def extract_warnings(model: BaseModelWithWarnings, parent_name: str = "", visited: Set[int] = None) -> List[ValidationWarning]:
    """
    Recursively extract warnings from a Pydantic model and its nested fields.
    
    :param model: The Pydantic model instance to inspect.
    :param parent_name: The name of the parent model to track the path.
    :return: List of tuples containing (model name, warning message).
    """                   
    if visited is None:
        visited = set()

    model_id = id(model)
    if model_id in visited:
        return []
    visited.add(model_id)
    
    warnings_list = [(parent_name or model.__class__.__name__, model_id,  warning) for warning in model.get_warnings()]

    for field_name, field in model.__fields__.items():
        full_path = f"{parent_name}.{field_name}" if parent_name else field_name
        value = getattr(model, field_name)

        if isinstance(value, BaseModelWithWarnings):
            warnings_list.extend(extract_warnings(value, full_path, visited))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, BaseModelWithWarnings):
                    list_path = f"{full_path}[{index}]"
                    warnings_list.extend(extract_warnings(item, list_path, visited))

    return warnings_list

