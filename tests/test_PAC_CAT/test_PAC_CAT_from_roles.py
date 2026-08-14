'''
PAC_CAT.from_roles(issuer, main=, processor=None) and Category.from_key(key, **fields) -
named-role construction replacing from_categories()'s positional-list role
assignment (main vs. processor inferred purely from list position today, with
no validation - the same bug class an external field-notes brief described at
the segment-key level, one level up). Both new constructors also accept an
`of` alias; from_roles/from_key are the encouraged spelling.

from_roles() internally builds long-form, forces short notation, and re-parses,
so the returned PAC_CAT's plain .to_url() (no explicit use_short_notation=True)
already gives the minimized form - the caller never decides which keys ride
implicitly. See design-choices.md ("PAC_CAT.from_categories() deprecated...").
'''
import pytest

from labfreed.pac_cat import PAC_CAT, Category, Material_Substance, Processor_Software


def test_category_from_key_builds_the_right_predefined_category():
    cat = Category.from_key("-MS", **{"240": "X67678", "10": "BATCH1"})
    assert isinstance(cat, Material_Substance)
    assert cat.product_number == "X67678"
    assert cat.batch_number == "BATCH1"


def test_category_from_key_falls_back_to_generic_category_for_unregistered_keys():
    cat = Category.from_key("-ZZ", **{"240": "X67678"})
    assert type(cat) is Category
    assert cat.key == "-ZZ"


def test_category_of_is_an_alias_for_from_key():
    via_of = Category.of("-MS", **{"240": "X67678"})
    via_from_key = Category.from_key("-MS", **{"240": "X67678"})
    assert via_of == via_from_key


def test_from_roles_with_only_main_gives_short_notation_by_default():
    main = Category.from_key("-MS", **{"240": "X67678", "10": "BATCH1"})
    pac = PAC_CAT.from_roles("METTORIUS.COM", main=main)
    assert pac.to_url() == "HTTPS://PAC.METTORIUS.COM/-MS/X67678/BATCH1"


def test_from_roles_with_main_and_processor():
    main = Category.from_key("-MS", **{"240": "X67678", "10": "BATCH1"})
    processor = Category.from_key("-PS", **{"21": "INSTANCE1", "240": "AURORA"})
    pac = PAC_CAT.from_roles("METTORIUS.COM", main=main, processor=processor)
    assert pac.to_url() == "HTTPS://PAC.METTORIUS.COM/-MS/X67678/BATCH1/-PS/INSTANCE1/AURORA"
    assert pac.main_category.key == "-MS"
    assert pac.processor.key == "-PS"


def test_from_roles_never_writes_an_explicit_key_the_caller_did_not_ask_for():
    ''' Mirrors the field-notes brief's own example: a skipped optional slot (no
    container_size/container_number here) must fall back to an explicit key for
    whatever comes after it, rather than silently shifting a later value into the
    skipped slot's position. '''
    main = Category.from_key("-MS", **{"240": "X67678", "250": "AL9"})  # batch/size/container skipped
    pac = PAC_CAT.from_roles("METTORIUS.COM", main=main)
    assert pac.to_url() == "HTTPS://PAC.METTORIUS.COM/-MS/X67678/250:AL9"


def test_pac_cat_of_is_an_alias_for_from_roles():
    main = Category.from_key("-MS", **{"240": "X67678"})
    assert PAC_CAT.of("METTORIUS.COM", main=main).to_url() == PAC_CAT.from_roles("METTORIUS.COM", main=main).to_url()


def test_from_categories_still_works_but_warns_deprecated():
    main = Material_Substance(**{"240": "X67678", "10": "BATCH1"})
    with pytest.deprecated_call():
        pac = PAC_CAT.from_categories("METTORIUS.COM", [main])
    assert pac.to_url() == "HTTPS://PAC.METTORIUS.COM/-MS/240:X67678/10:BATCH1"
