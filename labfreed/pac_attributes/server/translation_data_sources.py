import json
from labfreed.pac_attributes.api_data_models.response import Translations
from labfreed.pac_attributes.server.server import TranslationDataSource

class DictTranslationDataSource(TranslationDataSource):
    def __init__(self, data:dict) -> None:
        self._data = data
        
    def get(self, key:str):
        t = self._data.get(key)
        if t:
            return Translations(key, t)
        else:
            return None
    
class JsonFileTranslationDataSource(DictTranslationDataSource):
    def __init__(self, path:str) -> None:
        with open(path) as f:
            data = json.load(f)
        super().__init__(data=data)