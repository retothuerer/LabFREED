'''
All predefined categories from the PAC-CAT spec must be importable from the
package's public API (`labfreed.pac_cat`), not just from the internal
`predefined_categories` module - otherwise users can't construct or `isinstance`-check
against categories like Data_Static/-DS, Data_Misc/-DX, Processor_Software/-PS,
Processor_Misc/-PX or the top-level Misc/-X category, even though the parser
already recognizes them.
'''
import pytest


@pytest.mark.parametrize("name", [
    "Material_Device",
    "Material_Substance",
    "Material_Consumable",
    "Material_Misc",
    "Data_Method",
    "Data_Result",
    "Data_Progress",
    "Data_Calibration",
    "Data_Static",
    "Data_Misc",
    "Processor_Software",
    "Processor_Misc",
    "Misc",
])
def test_all_predefined_categories_are_publicly_importable(name):
    import labfreed.pac_cat as pac_cat
    assert hasattr(pac_cat, name)


def test_previously_unexported_categories_are_instantiable():
    from labfreed.pac_cat import Data_Static, Data_Misc, Processor_Software, Processor_Misc, Misc

    assert Data_Static(id='X1').is_valid
    assert Data_Misc(id='X1').is_valid
    assert Processor_Software(processor_instance='X1', processor_code=None).is_valid
    assert Processor_Misc(processor_instance='X1', processor_code=None).is_valid
    assert Misc(id='X1').is_valid
