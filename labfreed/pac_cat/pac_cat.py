from __future__ import annotations  # optional in 3.11, but recommended for consistency

from typing import Self
from pydantic import computed_field, model_validator

from rich import print
from rich.text import Text
from rich.table import Table

from labfreed.labfreed_infrastructure import ValidationMsgLevel

from labfreed.pac_cat.category_base import Category, CategorySegment
from labfreed.pac_cat.predefined_categories import PredefinedCategory, category_key_to_class_map
from labfreed.pac_id.id_segment import IDSegment
from labfreed.pac_id.pac_id import PAC_ID

''' Configure pdoc'''

    
class PAC_CAT(PAC_ID):
    ''' 
    Extends a PAC-ID with interpretation of the identifier as categories
    '''
    @computed_field
    @property
    def categories(self) -> list[Category]: 
        '''The categories present in the PAC-ID's identifier'''
        category_segments = self._split_segments_by_category(self.identifier)
        categories = list()
        for c in category_segments:
            categories.append(self._cat_from_cat_segments(c))
        return categories
    
    

    def get_category(self, key) -> Category:
        """Helper to get a category by key
        """
        tmp = [c for c in self.categories if c.key == key]
        if not tmp:
            return None
        return tmp[0]

    def _resolve_identifier_for_notation(self, use_short_notation: bool) -> list[IDSegment]:
        ''' @private Rebuilds the full identifier for forced short/long notation by
        walking `self.identifier` in its true original order and re-keying only the
        segments bound to a known category field. Category-key segments, derivation
        namespace markers, and unbound/custom segments are always passed through
        unchanged, in their original position.

        This is deliberately NOT built by concatenating each category's own
        reconstructed segments (`self.categories`, in category order): a marker's
        reattributed tail can sit textually before a *later* category in the raw
        identifier (see PAC-CAT "derivation namespace" section), and concatenating
        would move that later category's key segment to right after the marker -
        which, on reparsing, incorrectly redirects it into the primary category too,
        collapsing two categories into one.
        '''
        categories = self.categories
        cursors = [
            iter(cat._segment_bindings) if isinstance(cat, PredefinedCategory) else None
            for cat in categories
        ]
        omit_lookup = [
            cat._omit_key_for_alias(use_short_notation) if isinstance(cat, PredefinedCategory) else None
            for cat in categories
        ]

        derivation_idx = next((i for i, s in enumerate(self.identifier) if s.is_derivation_namespace), None)

        out = []
        owner = -1
        for i, seg in enumerate(self.identifier):
            if derivation_idx is not None and i >= derivation_idx:
                owner = 0 if categories else -1
            elif seg.value[0] == '-':
                owner += 1
                out.append(seg)
                continue

            if owner < 0 or cursors[owner] is None:
                out.append(seg)
                continue

            _, alias = next(cursors[owner], (seg, None))
            if alias is None:
                out.append(seg)
            else:
                key = None if omit_lookup[owner].get(alias) else alias
                out.append(IDSegment(key=key, value=seg.value))
        return out
    
    
    @classmethod
    def from_categories(cls, issuer:str, categories:list[Category]) -> PAC_CAT:
        identifier = list()
        for category in categories:
            identifier.append(IDSegment(value=category.key))
            identifier.extend(category.segments)
        return PAC_CAT(issuer=issuer, identifier=identifier)
    
    
    @classmethod
    def from_pac_id(cls, pac_id:PAC_ID) -> PAC_CAT:
        '''Constructs a PAC-CAT from a PAC-ID'''
        return PAC_CAT(issuer=pac_id.issuer, identifier=pac_id.identifier)
    

    
    def to_pac_id(self) -> PAC_ID:
        return PAC_ID(issuer=self.issuer, identifier=self.identifier)
        
            
    @classmethod
    def _cat_from_cat_segments(cls, segments:list[IDSegment]) -> Category:
        segments = segments.copy()
        category_key = segments[0].value
        segments.pop(0)

        # Tag every segment with the derivation namespace that contributed it, so
        # consumers can tell who added a segment without scanning back for the
        # nearest marker themselves. Everything after a marker inherits its tag until
        # the next one. The marker itself is kept in the stream (tagged with the
        # namespace it declares) so re-serialization can reconstruct it in its exact
        # original position - it's only hidden from the public `.segments` view
        # (see `PredefinedCategory.segments`), since that information now lives on
        # `derivation_namespace` and showing both would be redundant.
        current_namespace = None
        has_marker = False
        tagged_segments = []
        for seg in segments:
            if seg.is_derivation_namespace:
                current_namespace = seg.value[1:]
                has_marker = True
            tagged_segments.append(CategorySegment(key=seg.key, value=seg.value, derivation_namespace=current_namespace))
        segments = tagged_segments

        known_cat = category_key_to_class_map.get(category_key)

        if not known_cat:
            return Category(key=category_key, segments=segments)

        field_aliases = [
            field_info.alias
            for name, field_info in known_cat.model_fields.items()
            if field_info.alias and name not in ('key', 'additional_segments')
        ]
        model_dict = {alias: None for alias in field_aliases}

        # bindings keeps every segment in its original order, paired with the model
        # field alias it was matched to (or None for derivation markers / custom segments).
        # This lets `.segments` and forced-notation serialization reproduce the exact
        # original ordering instead of grouping known fields before custom ones.
        bindings: list[tuple[CategorySegment, str | None]] = []
        field_idx = 0
        can_imply = True
        for seg in segments:
            if seg.is_derivation_namespace:
                # A `+<namespace>` marker does not consume a field slot and does not
                # interrupt the implicit key sequence (PAC-CAT "derivation namespace" section).
                bindings.append((seg, None))
                continue

            bound = False
            if can_imply and field_idx < len(field_aliases):
                expected_alias = field_aliases[field_idx]
                # Explicit keys MAY be used along implicit ones, as long as the order
                # of segments is matched - only a key that differs from what's expected
                # next stops further implicit assignment.
                if seg.key is None or seg.key == expected_alias:
                    model_dict[expected_alias] = seg.value
                    bindings.append((seg, expected_alias))
                    field_idx += 1
                    bound = True
                else:
                    can_imply = False
            if not bound:
                bindings.append((seg, None))

        # try to fill remaining model keys by explicit key match, regardless of position
        for i, (seg, alias) in enumerate(bindings):
            if alias is not None:
                continue
            if seg.key in model_dict and not model_dict.get(seg.key):
                model_dict[seg.key] = seg.value
                bindings[i] = (seg, seg.key)

        additional_segments = [seg for seg, alias in bindings if alias is None]

        model_dict['additional_segments'] = additional_segments
        model_dict['key'] = category_key
        cat = known_cat(**model_dict)

        # Bindings are kept regardless of whether a marker is present - forced-notation
        # serialization (`_resolve_identifier_for_notation`) needs them for every
        # category, since it works by re-keying `PAC_CAT.identifier` in place rather
        # than reassembling from each category's own segments.
        cat._segment_bindings = bindings

        # But the *public* `.segments` view only switches to this position-preserving
        # order when a derivation namespace marker is actually involved: without one,
        # it keeps the long-standing canonical ordering (known fields in schema order,
        # then custom segments) that existing consumers already rely on. With one,
        # canonical reordering would move the marker (and whatever it precedes) out of
        # place, corrupting who-added-what attribution - so original ordering must be
        # preserved instead.
        cat._use_position_preserving_segments = has_marker
        return cat

    @staticmethod
    def _split_segments_by_category(segments:list[IDSegment]) -> list[list[IDSegment]]:
        category_segments = list()
        c = list()
        # Once a derivation namespace segment (`+<namespace>`) appears, every segment
        # from there on belongs to the *primary* (first) category - it MUST NOT start a
        # new category and MUST NOT be attributed to a subsequent issuing-system category,
        # even if it looks like one (PAC-CAT "derivation namespace" section).
        derivation_idx = next((i for i, s in enumerate(segments) if s.is_derivation_namespace), None)

        for i, s in enumerate(segments):
            if derivation_idx is not None and i >= derivation_idx:
                if not category_segments:
                    category_segments.append([])
                category_segments[0].append(s)
                continue
            # new category starts with "-"
            if s.value[0] == '-':
                c = [s]
                category_segments.append(c)
            else:
                c.append(s)

        # first cat can be empty > remove
        category_segments = [c for c in category_segments if len(c) > 0]

        return category_segments
    
    
    @model_validator(mode='after')
    def _check_keys_are_unique_in_each_category(self) -> Self:
        for c in self.categories:
            keys = [s.key for s in c.segments if s.key]
            duplicate_keys = [k for k in set(keys) if keys.count(k) > 1]
            if duplicate_keys:
                for k in duplicate_keys:
                    self._add_validation_message(
                        source=f"identifier {k}",
                        level = ValidationMsgLevel.ERROR,
                        msg=f"Duplicate key {k} in category {c.key}",
                        highlight_pattern = k
                    )
        return self
        
        
    @model_validator(mode='after')
    def _check_identifier_segment_keys_are_unique(self) -> Self:
        ''' override the validator of PAC-ID: in PAC-CAT segments can replicate in different categories'''
        return self
    
        
    def print_categories(self):
        table = Table(title=f'Categories in {str(self)}', show_header=False)
        table.add_column('0')
        table.add_column('1')
        for i, c in enumerate(self.categories):
            if i == 0:
                title = Text('Main Category', style='bold')
            else:
                title = Text('Category', style='bold')
            
            table.add_row(title)
            
            for field_name, field_info in c.model_fields.items():
                if not getattr(c, field_name):
                    continue
                table.add_row(f"{field_name} ({field_info.alias or ''})",
                              f" {getattr(c, field_name)}"
                              )      
            table.add_section()        
        print(table)
        

        
