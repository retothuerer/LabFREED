import pytest
import pydantic

from labfreed.pac_id_resolver.resolver_config import ResolverConfig, ResolverConfigBlock, ResolverConfigEntry
from labfreed.pac_id_resolver.resolver_config_common import ServiceType
from labfreed.pac_id_resolver.resolver_config_evaluator import ResolverConfigEvaluator


def _entry(**overrides):
    d = {
        'service_name': 'Service',
        'application_intents': ['view-apinilabs'],
        'service_type': 'userhandover-generic',
        'template_url': 'https://example.com/{$.name}',
    }
    d.update(overrides)
    return d


class _FakePac:
    ''' Stand-in for a PAC_ID/PAC_CAT object: evaluate_pac_id only ever calls .to_dict().
    Note: this returns the PAC-ID's own flat dict - ResolverConfigEvaluator.evaluate()
    is what nests it under a `pac` key, so callers going through evaluate_pac_id()
    (below) must write `$.pac....` in their config, while the flat dict passed here
    stays unwrapped. '''
    def __init__(self, d):
        self._d = d

    def to_dict(self):
        return self._d


# ---------------------------------------------------------------------------
# ResolverConfigEntry.service_name validation
# ---------------------------------------------------------------------------

def test_service_name_with_allowed_characters_has_no_errors():
    e = ResolverConfigEntry(**_entry(service_name='My Service-1'))
    assert e.errors() == []


def test_service_name_with_invalid_characters_is_flagged():
    e = ResolverConfigEntry(**_entry(service_name='Bad$Name'))
    assert any('invalid characters' in m.msg for m in e.errors())


def test_service_name_empty_is_flagged():
    e = ResolverConfigEntry(**_entry(service_name=''))
    assert any('at least one and maximum 255' in m.msg for m in e.errors())


def test_service_name_too_long_is_flagged():
    e = ResolverConfigEntry(**_entry(service_name='A' * 256))
    assert any('at least one and maximum 255' in m.msg for m in e.errors())


# ---------------------------------------------------------------------------
# ResolverConfigEntry.application_intents validation
# ---------------------------------------------------------------------------

def test_application_intent_with_allowed_characters_has_no_errors():
    e = ResolverConfigEntry(**_entry(application_intents=['show-manual-apinilabs']))
    assert e.errors() == []


def test_application_intent_ending_in_generic_suffix_is_flagged():
    e = ResolverConfigEntry(**_entry(application_intents=['foo-generic']))
    assert any("Ends with '-generic'" in m.msg for m in e.errors())


def test_application_intent_with_invalid_characters_is_flagged():
    e = ResolverConfigEntry(**_entry(application_intents=['bad intent']))
    assert any('invalid characters' in m.msg for m in e.errors())


def test_application_intent_empty_is_flagged():
    e = ResolverConfigEntry(**_entry(application_intents=['']))
    assert any('at least one and maximum 255' in m.msg for m in e.errors())


def test_application_intent_too_long_is_flagged():
    e = ResolverConfigEntry(**_entry(application_intents=['a' * 256]))
    assert any('at least one and maximum 255' in m.msg for m in e.errors())


# ---------------------------------------------------------------------------
# ResolverConfigEntry.service_type validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('service_type', [
    'attributes-generic',
    'userhandover-generic',
    'action-generic',
    ServiceType.ATTRIBUTE_SERVICE_GENERIC,
    ServiceType.USER_HANDOVER_GENERIC,
    ServiceType.ACTION_GENERIC,
])
def test_service_type_allowed_values_have_no_errors(service_type):
    e = ResolverConfigEntry(**_entry(service_type=service_type))
    assert e.errors() == []


def test_service_type_invalid_value_is_flagged():
    e = ResolverConfigEntry(**_entry(service_type='not-a-real-type'))
    assert any('Invalid service type' in m.msg for m in e.errors())


# ---------------------------------------------------------------------------
# ResolverConfigEntry.key validation
# ---------------------------------------------------------------------------

def test_key_absent_has_no_errors():
    e = ResolverConfigEntry(**_entry())
    assert e.key is None
    assert e.errors() == []


def test_key_valid_iri_has_no_errors():
    # PAC-ID Attributes' own recommended key for "Safety Data Sheet" (well_known_keys.md,
    # "Documents" section) - key reuses the same external vocabularies Attributes
    # already sources its keys from, rather than a LabFREED-specific namespace.
    e = ResolverConfigEntry(**_entry(key='https://www.wikidata.org/wiki/Q222067'))
    assert e.errors() == []


def test_key_without_scheme_is_flagged():
    e = ResolverConfigEntry(**_entry(key='msds'))
    assert any('absolute IRI' in m.msg for m in e.errors())


def test_key_with_whitespace_is_flagged():
    e = ResolverConfigEntry(**_entry(key='https://www.wikidata.org/wiki/Q222067 msds'))
    assert any('absolute IRI' in m.msg for m in e.errors())


# ---------------------------------------------------------------------------
# ResolverConfigBlock.applicable_if defaulting
# ---------------------------------------------------------------------------

def test_applicable_if_defaults_to_true_when_omitted():
    b = ResolverConfigBlock(entries=[_entry()])
    assert b.applicable_if == 'True'


def test_applicable_if_none_converts_to_true():
    b = ResolverConfigBlock(**{'if': None, 'entries': [_entry()]})
    assert b.applicable_if == 'True'


def test_applicable_if_accepts_unquoted_yaml_true():
    # PyYAML parses an unquoted `if: true` as a native Python bool, not the
    # string "true" -- the field must accept that, since that's exactly what a
    # config author gets by writing the natural, unquoted YAML.
    b = ResolverConfigBlock(**{'if': True, 'entries': [_entry()]})
    assert b.applicable_if == 'True'


def test_applicable_if_accepts_unquoted_yaml_false():
    b = ResolverConfigBlock(**{'if': False, 'entries': [_entry()]})
    assert b.applicable_if == 'False'


# ---------------------------------------------------------------------------
# ResolverConfig.from_yaml
# ---------------------------------------------------------------------------

def test_from_yaml_parses_a_valid_config():
    yml = '''
    schema_version: "2.0"
    origin: my-origin
    config:
      - if: $.pac.issuer == ACME.COM
        entries:
          - service_name: Shop
            application_intents: [view-apinilabs]
            service_type: userhandover-generic
            template_url: "https://acme.com/shop"
    '''
    rc = ResolverConfig.from_yaml(yml)
    assert rc.origin == 'my-origin'
    assert len(rc.config) == 1
    assert rc.config[0].entries[0].service_name == 'Shop'


def test_from_yaml_invalid_yaml_raises_value_error():
    with pytest.raises(ValueError):
        ResolverConfig.from_yaml('config: [this is not: valid: yaml')


def test_from_yaml_wrong_schema_version_is_rejected():
    with pytest.raises(pydantic.ValidationError):
        ResolverConfig.from_yaml('schema_version: "1.0"\norigin: x\n')


def test_origin_empty_produces_warning():
    rc = ResolverConfig()
    assert any('Origin should not be empty' in m.msg for m in rc.warnings())


# ---------------------------------------------------------------------------
# Expression helpers: convenience substitutions & tokenizing
# ---------------------------------------------------------------------------

def test_apply_convenience_substitutions_rewrites_double_quoted_bracket_key_access():
    ev = ResolverConfigEvaluator(ResolverConfig())
    out = ev._apply_convenience_substitutions('$.identifier["ID"].value')
    assert out == '$.identifier[?(@.key == "ID")].value'


def test_apply_convenience_substitutions_rewrites_single_quoted_bracket_key_access():
    ev = ResolverConfigEvaluator(ResolverConfig())
    out = ev._apply_convenience_substitutions("$.identifier['ID'].value")
    assert out == "$.identifier[?(@.key == 'ID')].value"


def test_tokenize_recognizes_all_token_types():
    ev = ResolverConfigEvaluator(ResolverConfig())
    tokens = ev._tokenize_jsonpath_expression('($.a == FOO) AND NOT ($.b != BAR) OR $.c')
    types = [t[1] for t in tokens]
    assert types == [
        'LPAREN', 'JSONPATH', 'OPERATOR', 'LITERAL', 'RPAREN',
        'LOGIC', 'LOGIC', 'LPAREN', 'JSONPATH', 'OPERATOR', 'LITERAL', 'RPAREN',
        'LOGIC', 'JSONPATH',
    ]


def test_tokenize_recognizes_quoted_string_literals_with_spaces():
    ev = ResolverConfigEvaluator(ResolverConfig())
    tokens = ev._tokenize_jsonpath_expression('''$.a == 'John Doe' AND $.b == "Jane Doe"''')
    assert tokens == [
        ('$.a', 'JSONPATH'), ('==', 'OPERATOR'), ("'John Doe'", 'STRING'),
        ('AND', 'LOGIC'),
        ('$.b', 'JSONPATH'), ('==', 'OPERATOR'), ('"Jane Doe"', 'STRING'),
    ]


def test_tokenize_raises_syntax_error_on_invalid_character():
    ev = ResolverConfigEvaluator(ResolverConfig())
    with pytest.raises(SyntaxError):
        ev._tokenize_jsonpath_expression('$.a == #quoted#')


# ---------------------------------------------------------------------------
# applicable_if evaluation (boolean logic)
# ---------------------------------------------------------------------------

def test_applicable_if_true_literal_is_applicable():
    rc = ResolverConfig()
    _, applicable = ResolverConfigEvaluator(rc)._evaluate_applicable_if({}, 'True')
    assert applicable


def test_applicable_if_false_literal_is_not_applicable():
    # currently broken: any bare word literal (including "False") gets wrapped
    # into a non-empty, therefore truthy, quoted string -- so a literal false
    # condition can never actually apply. See resolver_config.py review.
    rc = ResolverConfig()
    _, applicable = ResolverConfigEvaluator(rc)._evaluate_applicable_if({}, 'False')
    assert applicable is False


def test_applicable_if_jsonpath_present_is_applicable():
    rc = ResolverConfig()
    _, applicable = ResolverConfigEvaluator(rc)._evaluate_applicable_if({'pac': {'issuer': 'ACME.COM'}}, '$.pac.issuer')
    assert applicable is True


def test_applicable_if_jsonpath_absent_is_not_applicable():
    rc = ResolverConfig()
    _, applicable = ResolverConfigEvaluator(rc)._evaluate_applicable_if({}, '$.pac.issuer')
    assert applicable is False


def test_applicable_if_equality_comparison_true_case_insensitive():
    rc = ResolverConfig()
    _, applicable = ResolverConfigEvaluator(rc)._evaluate_applicable_if({'pac': {'issuer': 'acme.com'}}, '$.pac.issuer == ACME.COM')
    assert applicable is True


def test_applicable_if_equality_comparison_false():
    rc = ResolverConfig()
    _, applicable = ResolverConfigEvaluator(rc)._evaluate_applicable_if({'pac': {'issuer': 'OTHER.COM'}}, '$.pac.issuer == ACME.COM')
    assert applicable is False


def test_applicable_if_and_or_not_logic():
    rc = ResolverConfig()
    pac = {'pac': {'issuer': 'ACME.COM', 'category': '-MD'}}
    _, applicable = ResolverConfigEvaluator(rc)._evaluate_applicable_if(
        pac, '$.pac.issuer == ACME.COM AND NOT ($.pac.category == "-MC")'
    )
    assert applicable is True


def test_applicable_if_comparison_against_quoted_literal_with_spaces():
    rc = ResolverConfig()
    pac = {'name': 'John Doe'}
    _, applicable = ResolverConfigEvaluator(rc)._evaluate_applicable_if(pac, "$.name == 'John Doe'")
    assert applicable is True


# ---------------------------------------------------------------------------
# evaluate_pac_id: end-to-end block/entry selection
# ---------------------------------------------------------------------------

def test_evaluate_pac_id_includes_services_from_applicable_blocks():
    yml = '''
    origin: my-origin
    config:
      - if: $.pac.issuer == ACME.COM
        entries:
          - service_name: Shop
            application_intents: [view-apinilabs]
            service_type: userhandover-generic
            template_url: "https://acme.com/shop"
      - if: $.pac.issuer == OTHER.COM
        entries:
          - service_name: Should Not Appear
            application_intents: [view-apinilabs]
            service_type: userhandover-generic
            template_url: "https://other.com/shop"
    '''
    rc = ResolverConfig.from_yaml(yml)
    result = rc.evaluate_pac_id(_FakePac({'issuer': 'ACME.COM'}))
    assert [s.service_name for s in result.services] == ['Shop']
    assert result.origin == 'my-origin'


def test_evaluate_pac_id_skips_entries_with_validation_errors():
    yml = '''
    origin: my-origin
    config:
      - if: True
        entries:
          - service_name: Good Service
            application_intents: [view-apinilabs]
            service_type: userhandover-generic
            template_url: "https://example.com/good"
          - service_name: Bad Entry
            application_intents: [view-apinilabs]
            service_type: not-a-real-type
            template_url: "https://example.com/bad"
    '''
    rc = ResolverConfig.from_yaml(yml)
    result = rc.evaluate_pac_id(_FakePac({}))
    assert [s.service_name for s in result.services] == ['Good Service']


def test_evaluate_pac_id_expands_url_template_placeholders():
    rc = ResolverConfig(origin='o')
    block = ResolverConfigBlock(entries=[_entry(template_url='https://example.com/item/{$.pac.name}')])
    rc.config = [block]
    result = rc.evaluate_pac_id(_FakePac({'name': 'widget'}))
    assert result.services[0].url == 'https://example.com/item/widget'


def test_evaluate_pac_id_url_encodes_special_characters_in_placeholder_values():
    rc = ResolverConfig(origin='o')
    block = ResolverConfigBlock(entries=[_entry(template_url='https://example.com/{$.pac.q}')])
    rc.config = [block]
    result = rc.evaluate_pac_id(_FakePac({'q': 'a b&c=d'}))
    assert result.services[0].url == 'https://example.com/a%20b%26c%3Dd'


def test_evaluate_pac_id_propagates_key_to_resolved_service():
    rc = ResolverConfig(origin='o')
    block = ResolverConfigBlock(entries=[_entry(key='https://www.wikidata.org/wiki/Q222067')])
    rc.config = [block]
    result = rc.evaluate_pac_id(_FakePac({}))
    assert result.services[0].key == 'https://www.wikidata.org/wiki/Q222067'


def test_evaluate_pac_id_resolved_service_key_defaults_to_none_when_absent():
    rc = ResolverConfig(origin='o')
    block = ResolverConfigBlock(entries=[_entry()])
    rc.config = [block]
    result = rc.evaluate_pac_id(_FakePac({}))
    assert result.services[0].key is None


# ---------------------------------------------------------------------------
# client_info: forward-looking Resolver Context extension (not part of the
# published v2 spec - see the PAC-ID-Resolver v3 roadmap, "Resolver Context:
# beyond just the PAC-ID").
# ---------------------------------------------------------------------------

def test_evaluate_pac_id_client_info_is_usable_in_template_url():
    rc = ResolverConfig(origin='o')
    block = ResolverConfigBlock(entries=[_entry(template_url='https://example.com/{$.client_info.location}')])
    rc.config = [block]
    result = rc.evaluate_pac_id(_FakePac({'issuer': 'ACME.COM'}), client_info={'location': 'HTTPS://PAC.BUCHI.COM/-MD/C-950/FAKE0000'})
    assert result.services[0].url == 'https://example.com/HTTPS%3A//PAC.BUCHI.COM/-MD/C-950/FAKE0000'


def test_evaluate_pac_id_client_info_is_usable_in_applicable_if():
    yml = '''
    origin: my-origin
    config:
      - if: $.client_info.language == FR
        entries:
          - service_name: French Page
            application_intents: [view-apinilabs]
            service_type: userhandover-generic
            template_url: "https://example.com/fr"
    '''
    rc = ResolverConfig.from_yaml(yml)
    result = rc.evaluate_pac_id(_FakePac({}), client_info={'language': 'FR'})
    assert [s.service_name for s in result.services] == ['French Page']


def test_evaluate_pac_id_without_client_info_leaves_resolver_context_unchanged():
    rc = ResolverConfig(origin='o')
    block = ResolverConfigBlock(entries=[_entry(template_url='https://example.com/{$.client_info.location}')])
    rc.config = [block]
    result = rc.evaluate_pac_id(_FakePac({'issuer': 'ACME.COM'}))
    assert result.services[0].url == 'https://example.com/'


# ---------------------------------------------------------------------------
# Security regression: matched PAC-ID content must be treated as inert data,
# never as part of the evaluated expression (see security review of the
# eval() in _evaluate_applicable_if).
# ---------------------------------------------------------------------------

def test_applicable_if_does_not_crash_on_quote_and_paren_characters_in_matched_value():
    # a stray `"` / `(` in a matched PAC-ID field currently breaks out of the
    # quoted literal the eval'd expression is built from and raises an
    # unhandled SyntaxError -- resolution of the PAC-ID must degrade to "not
    # applicable", not crash.
    rc = ResolverConfig()
    pac = {'name': 'a"b('}
    _, applicable = ResolverConfigEvaluator(rc)._evaluate_applicable_if(pac, '$.name == FOO')
    assert applicable is False


def test_applicable_if_does_not_crash_on_non_string_matched_value():
    # a jsonpath match that isn't a string (e.g. a numeric T-REX value) must
    # not crash the comparison.
    rc = ResolverConfig()
    pac = {'count': 42}
    _, applicable = ResolverConfigEvaluator(rc)._evaluate_applicable_if(pac, '$.count == 42')
    assert applicable is True


def test_applicable_if_treats_matched_value_as_literal_data_not_code():
    # a matched value that looks like executable code must be compared as an
    # inert string, never interpreted -- this is the core eval-injection
    # concern from the security review.
    rc = ResolverConfig()
    pac = {'name': '__import__("os").system("true")'}
    _, applicable = ResolverConfigEvaluator(rc)._evaluate_applicable_if(pac, '$.name == FOO')
    assert applicable is False


# ---------------------------------------------------------------------------
# Reported issue: quoting a literal value used to crash the tokenizer
# (github.com/ApiniLabs/PAC-ID-Resolver -- quotes around a comparison value
# like 'PERSON' raised an unhandled SyntaxError instead of just working).
# ---------------------------------------------------------------------------

def test_applicable_if_supports_quoted_literals_as_reported():
    rc = ResolverConfig()
    pac = {'pac': {'issuer': 'APINILABS.COM', 'identifier': [{'value': 'PERSON'}, {'value': 'THOMAS'}]}}
    expr = ("$.pac.issuer == APINILABS.COM AND $.pac.identifier[0].value == 'PERSON'"
            " AND $.pac.identifier[1].value == 'THOMAS'")
    _, applicable = ResolverConfigEvaluator(rc)._evaluate_applicable_if(pac, expr)
    assert applicable is True


def test_applicable_if_quoted_literal_mismatch_is_not_applicable():
    rc = ResolverConfig()
    pac = {'pac': {'identifier': [{'value': 'PERSON'}]}}
    _, applicable = ResolverConfigEvaluator(rc)._evaluate_applicable_if(
        pac, "$.pac.identifier[0].value == 'ROBOT'"
    )
    assert applicable is False


# ---------------------------------------------------------------------------
# Block-level resilience: a malformed applicable_if must not crash resolution
# of the whole PAC-ID, same contract as invalid entries.
# ---------------------------------------------------------------------------

def test_evaluate_pac_id_skips_blocks_with_malformed_applicable_if():
    rc = ResolverConfig(origin='o')
    bad_block = ResolverConfigBlock(**{'if': '$.a ~~ not valid syntax [[', 'entries': []})
    good_block = ResolverConfigBlock(entries=[_entry(service_name='Good Service')])
    rc.config = [bad_block, good_block]

    result = rc.evaluate_pac_id(_FakePac({}))

    assert [s.service_name for s in result.services] == ['Good Service']
