from pydantic import BaseModel


class ServerCapabilities(BaseModel):
    supported_languages: list[str]
    default_language: str
    available_attribute_groups: list[str]