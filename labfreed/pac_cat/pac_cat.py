from __future__ import annotations  # optional in 3.11, but recommended for consistency

from typing import Self
from deprecated import deprecated
from pydantic import computed_field, model_validator

from rich import print
from rich.text import Text
from rich.table import Table

from labfreed.labfreed_infrastructure import ValidationMsgLevel

from labfreed.pac_cat.category_base import Category, CategorySegment
from labfreed.pac_cat.predefined_categories import (
    Material_Device, PredefinedCategory, Processor_Misc, Processor_Software, category_key_to_class_map
)
from labfreed.pac_id.id_segment import IDSegment
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.pac_id.keyed_values import KeyedValue

''' Configure pdoc'''

    
class PAC_CAT(PAC_ID):
    ''' 
    Extends a PAC-ID with interpretation of the identifier as categories
    '''
    @computed_field
    @property
    def categories(self) -> list[Category]:
        '''The categories present in the PAC-ID's identifier - the primary category
        and, if present, the PAC-ID's own top-level issuing system. Capped at these
        two: a derivation's own issuing system (PAC-CAT "Identifying the issuing
        system of a derivation") is scoped to that one derivation, not to the
        PAC-ID itself, so it does not appear here - see `derivation_issuing_systems`.'''
        categories, _ = self._partition_categories(self._build_all_categories())
        return categories

    @property
    def derivation_issuing_systems(self) -> dict[str, Category]:
        '''The issuing system used for each derivation (`+<namespace>` block) that
        declared one, keyed by namespace - see PAC-CAT "Identifying the issuing
        system of a derivation". Empty if none of the PAC-ID's derivations declared
        one. Python-only convenience: not part of the Resolver Context JSON contract
        (unlike `categories`), since including it there would mean serializing a
        redundant, differently-shaped side channel through the same `to_dict()`
        that resolver configs are written against.'''
        _, derivation_issuing_systems = self._partition_categories(self._build_all_categories())
        return derivation_issuing_systems

    def _build_all_categories(self) -> list[Category]:
        ''' @private All categories in original split order: the primary category
        first, then every "second category" group in the order it appears in the
        identifier - the PAC-ID's own top-level issuing system (if any) and each
        derivation's own issuing system (if any) are peers here, even though only
        the primary and the top-level one are ever exposed via the public
        `.categories` (see `_partition_categories`). Kept separate from
        `_partition_categories` because `_resolve_identifier_for_notation` needs
        this full, unfiltered set too - forced-notation re-keying must account for
        every category actually present in `self.identifier`, not just the
        publicly-exposed ones. '''
        groups = self._split_segments_by_category(self.identifier)
        return [self._cat_from_cat_segments(segs, derivation_namespace=scope) for scope, segs in groups]

    def _partition_categories(self, all_categories: list[Category]) -> tuple[list[Category], dict[str, Category]]:
        ''' @private Splits `all_categories` (in original split order) into the
        public `.categories` (every group scoped to `None` - i.e. everything
        *except* a derivation's own issuing system, so a PAC-ID with several
        plain, marker-free categories keeps working exactly as before) and the
        derivation-scoped issuing systems dict. Also wires the primary category's
        `_issuing_systems_by_scope`, so `CategorySegment.issuing_system` resolves
        correctly for segments built fresh on every `.segments` access
        (`PredefinedCategory._get_segments_canonical`/`_get_segments_from_bindings`).

        Two kinds of segment are never rebuilt, though, and so need stamping here
        directly instead of relying on a rebuild path to do it on demand: a
        primary category that ISN'T a `PredefinedCategory` (base `Category.segments`
        just returns its stored `_segments` as-is, never rebuilding), and
        `additional_segments`/unbound `_segment_bindings` entries on a
        `PredefinedCategory` primary (custom segments the rebuild paths pass
        through unchanged rather than reconstructing - see `_get_segments_from_bindings`). '''
        categories = [c for c in all_categories if c.derivation_namespace is None]
        derivation_issuing_systems = {c.derivation_namespace: c for c in all_categories if c.derivation_namespace is not None}

        primary = categories[0] if categories else None
        if primary is not None:
            # Whichever unscoped category comes right after the primary (if any)
            # is the PAC-ID's own top-level issuing system - same positional
            # convention `.processor` already uses.
            top_level_issuing = categories[1] if len(categories) > 1 else None
            issuing_by_scope = dict(derivation_issuing_systems)
            if top_level_issuing is not None:
                issuing_by_scope[None] = top_level_issuing
            primary._issuing_systems_by_scope = issuing_by_scope
            if isinstance(primary, PredefinedCategory):
                for seg, alias in primary._segment_bindings or []:
                    if alias is None:
                        seg._issuing_system = issuing_by_scope.get(seg.derivation_namespace)
            else:
                for seg in primary._segments:
                    seg._issuing_system = issuing_by_scope.get(seg.derivation_namespace)

        return categories, derivation_issuing_systems

    @computed_field
    @property
    def main_category(self) -> Category | None:
        '''The primary category - the one the PAC-ID actually refers to (the first category in the identifier)'''
        categories = self.categories
        return categories[0] if categories else None

    @computed_field
    @property
    def processor(self) -> Category | None:
        '''The second category in the identifier, if present - PAC-CAT's "second
        category identifying what system generated/manages this record". Purely
        positional: whichever category sits there counts, regardless of type (usually
        -PS/-PX, or a -MD instrument acting as processor). A PAC-ID with only one
        category has no processor.'''
        categories = self.categories
        return categories[1] if categories and len(categories)>1 else None

    def get_category(self, key) -> Category | None:
        """Helper to get a category by key
        """
        tmp = [c for c in self.categories if c.key == key]
        if not tmp:
            return None
        return tmp[0]

    def _segment_values_for_key(self, key: str) -> list[KeyedValue]:
        '''Overrides PAC_ID's explicit-key-only lookup to also resolve implicit/
        positional segment keys, via each category's own already-resolved fields -
        each category already tags its own match with a SegmentOrigin, so this just
        collects them.'''
        return [kv for category in self.categories if (kv := category.value_for_key(key)) is not None]

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

        Uses `_build_all_categories()` rather than the public `.categories` - a
        derivation-scoped issuing system needs its own cursor/omit-lookup entry
        here too, even though it's excluded from `.categories` itself (see
        `_partition_categories`), since it's still a real category physically
        present in `self.identifier` that needs correct re-keying.
        '''
        all_categories = self._build_all_categories()
        cursors = [
            iter(cat._segment_bindings) if isinstance(cat, PredefinedCategory) else None
            for cat in all_categories
        ]
        omit_lookup = [
            cat._omit_key_for_alias(use_short_notation) if isinstance(cat, PredefinedCategory) else None
            for cat in all_categories
        ]

        out = []
        owner = -1
        primary_mode = True
        for seg in self.identifier:
            if seg.is_derivation_namespace:
                # Mirrors _split_segments_by_category: a marker redirects
                # subsequent segments back to the primary category (owner 0)
                # without touching `owner` itself - `owner` must keep counting
                # from wherever it left off, so a *later* "-" (e.g. a second
                # derivation's own issuing system) still gets the next index,
                # not one that collides with an earlier category. Unlike a
                # category-key segment below, the marker itself DOES still
                # consume a binding-cursor slot (`_cat_from_cat_segments` binds
                # it to `(seg, None)`) - falling through rather than
                # `continue`-ing keeps that slot in sync with every segment
                # after it.
                primary_mode = True
            elif seg.value.startswith('-'):
                owner += 1
                primary_mode = False
                out.append(seg)
                continue

            this_owner = 0 if primary_mode else owner
            if this_owner < 0 or this_owner >= len(cursors) or cursors[this_owner] is None:
                out.append(seg)
                continue

            _, alias = next(cursors[this_owner], (seg, None))
            if alias is None:
                out.append(seg)
            else:
                key = None if omit_lookup[this_owner].get(alias) else alias
                out.append(IDSegment(key=key, value=seg.value))
        return out
    
    
    @classmethod
    @deprecated("Role assignment is purely positional here - use PAC_CAT.from_roles() "
                "instead, which assigns main/processor by name, not list position. "
                "Deprecated since v1.0, will be removed in v2.0.")
    def from_categories(cls, issuer:str, categories:list[Category]) -> PAC_CAT:
        identifier = list()
        for category in categories:
            identifier.append(IDSegment(value=category.key))
            identifier.extend(category.segments)
        return PAC_CAT(issuer=issuer, identifier=identifier)


    @classmethod
    def from_roles(cls, issuer: str, main: Category, processor: Category | None = None) -> PAC_CAT:
        '''Builds a PAC_CAT from named category roles instead of a positional list -
        main/processor are assigned by name, so a caller can never accidentally swap
        them the way a positional list allows. Builds the long-form identifier, forces
        short notation, and re-parses, so the caller never decides which keys ride
        implicitly - the returned PAC_CAT already reflects the minimized form.'''
        categories = [main] if processor is None else [main, processor]
        identifier = list()
        for category in categories:
            identifier.append(IDSegment(value=category.key))
            identifier.extend(category.segments)
        long_form = PAC_CAT(issuer=issuer, identifier=identifier)
        return PAC_CAT.from_url(long_form.to_url(use_short_notation=True), suppress_validation_errors=True)


    @classmethod
    def of(cls, issuer: str, main: Category, processor: Category | None = None) -> PAC_CAT:
        '''Alias for from_roles() - from_roles is the encouraged spelling (matches this
        codebase's from_* convention); of is provided for callers coming from Java/
        TS-influenced ecosystems, where that's the idiomatic name.'''
        return cls.from_roles(issuer, main=main, processor=processor)


    @classmethod
    def from_pac_id(cls, pac_id:PAC_ID) -> PAC_CAT:
        '''Constructs a PAC-CAT from a PAC-ID'''
        return PAC_CAT(issuer=pac_id.issuer, identifier=pac_id.identifier)
    

    
    def to_pac_id(self) -> PAC_ID:
        return PAC_ID(issuer=self.issuer, identifier=self.identifier)
        
            
    def _cat_from_cat_segments(self, segments: list[IDSegment], derivation_namespace: str | None = None) -> Category:
        ''' Builds one `Category` from one group of `_split_segments_by_category`'s
        output. `derivation_namespace` is that group's own scope (`None` for the
        primary category and for the PAC-ID's own top-level issuing system, a real
        namespace for a derivation's own issuing system) - stamped onto the
        returned `Category` itself, alongside the base PAC-ID's `issuer` every
        category needs regardless of scope (see `CategorySegment.issuer`). '''
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
            tagged_seg = CategorySegment(key=seg.key, value=seg.value)
            tagged_seg._derivation_namespace = current_namespace
            tagged_seg._issuer = self.issuer
            tagged_segments.append(tagged_seg)
        segments = tagged_segments

        known_cat = category_key_to_class_map.get(category_key)

        if not known_cat:
            cat = Category(key=category_key, segments=segments)
            cat._derivation_namespace = derivation_namespace
            cat._issuer = self.issuer
            return cat

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
        cat._derivation_namespace = derivation_namespace
        cat._issuer = self.issuer
        return cat

    @staticmethod
    def _split_segments_by_category(segments: list[IDSegment]) -> list[tuple[str | None, list[IDSegment]]]:
        ''' Splits `segments` into per-category groups, in original order, paired
        with each group's derivation-namespace scope: the primary category is
        always first (scope irrelevant - `_cat_from_cat_segments` ignores it for
        that group), followed by zero or more "second category" groups - each
        either the PAC-ID's own top-level issuing system (scope `None`, appears
        before any `+<namespace>` marker) or one specific derivation's issuing
        system (scope = that namespace, appears after that block's own segments -
        PAC-CAT "Identifying the issuing system of a derivation").

        Any segment that isn't itself a category-key ('-...') or marker ('+...')
        folds into the primary category while `primary_mode` is active - active
        again immediately after every marker, until the next '-' category-key
        segment reopens issuing-system mode. This is what keeps a derivation's own
        segments in the primary category (PAC-CAT "derivation namespace" section)
        while still letting a '-' *after* those segments start a real, separate
        category instead of being swallowed too.

        Before the very first '-' (i.e. before the primary category itself has
        even been opened), `primary_mode` does NOT apply - any stray segment there
        is discarded exactly as it always was, not folded into a category that
        doesn't exist yet. Without this distinction, an identifier with no
        category segments at all (e.g. a plain PAC-ID's whole identifier) would
        wrongly get a synthetic, empty-keyed "category", and `PAC_Parser` would
        never fall back from `PAC_CAT` to a plain `PAC_ID` for it. '''
        category_segments: list[list[IDSegment]] = []
        scopes: list[str | None] = []
        current: list[IDSegment] = []
        current_scope = None
        primary_mode = False

        for s in segments:
            if s.is_derivation_namespace:
                current_scope = s.value[1:]
                if category_segments:
                    primary_mode = True
                    category_segments[0].append(s)
                else:
                    current.append(s)
                continue

            if s.value.startswith('-'):
                current = [s]
                category_segments.append(current)
                scopes.append(current_scope)
                primary_mode = False
                continue

            if primary_mode:
                category_segments[0].append(s)
            else:
                current.append(s)

        # first cat can be empty > remove (keeping scopes in sync)
        return [(scope, segs) for scope, segs in zip(scopes, category_segments) if segs]
    
    
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
        

        
