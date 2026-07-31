from enum import StrEnum


class ServiceUUID(StrEnum):
    MATERIAL_DEVICE = "6b190a7d-5aac-4943-bc3f-0ca90a9dff66"
    MATERIAL_SUBSTANCE = "5a0f2312-e944-4761-adf1-ecac1ea30171"
    MATERIAL_CONSUMABLE = "72e77869-da3c-4dab-b540-563ba5085a3e"
    MATERIAL_MISC = "971b275e-4fa1-4993-bdc6-720d159ffb32"
    
    DATA_RESULT = "1b79bd00-b4f9-4932-b93b-17b9ee161d0c"
    DATA_METHOD = "640cf34a-6a93-423b-adc4-9836d24f33d1"
    DATA_CALIBRATION = "98c5ef48-2059-4692-ac8d-607c97afeb1d"
    DATA_PROGRESS = "114c07af-9d07-48bc-adc0-de34d1d075ce"
    DATA_MISC = "2002cf5a-569f-4d37-84ff-19aeeda6fc72"
    
    PROCESSOR_SOFTWARE = "76a5901e-2438-4f1d-9738-e7c35c813c8c"
    PROCESSOR_MISC = "0e067884-53a4-4470-a5f8-02dec4d4e171"
    
    @classmethod
    def all_uuid(cls):
        out = [member.lower() for member in cls]
        return out



class PAC_Characteristics(StrEnum):
    PAC_ID_PART_0 = "1b79bd10-b4f9-4932-b93b-17b9ee161d0c"
    PAC_ID_PART_1 = "f636bdc7-88da-49e5-b823-12310e62c215"
    PAC_ID_PART_2 = "644c3de5-4337-44be-9dec-8b3abf10bf70"
    PAC_ID_PART_3 = "382bfd6a-a407-48d3-9337-1b1b81a2c314"