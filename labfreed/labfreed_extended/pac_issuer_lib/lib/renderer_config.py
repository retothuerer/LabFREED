'''Predicate-based selection of which page template renders a PacInfo.

One flat, ordered list of rules, evaluated "last match wins": every rule's predicate is
checked in order, and whichever *last* rule matches provides the template. Register
from most-generic to most-specific, so a later, narrower predicate naturally overrides
an earlier, broader one purely by position - no separate "category" vs. "dedicated"
concept, and every rule points at a full, self-contained page template.

Overriding a template that needs no new predicate at all (e.g. an issuer wants its own
content for a category LabFREED already has a default for) needs no entry here -
that's handled by the pre-existing ChoiceLoader file-shadowing mechanism (an issuer's
own template file of the same name is found before labfreed_extended's bundled one).
RendererConfig rules are only needed for genuinely new predicates an issuer introduces.
'''
from dataclasses import dataclass, field
from typing import Callable

from labfreed.labfreed_extended.app.pac_info.pac_info import PacInfo


@dataclass(frozen=True)
class RendererRule:
    name: str
    '''For logging/debugging.'''
    predicate: Callable[[PacInfo], bool]
    template: str
    '''A full, self-contained page template.'''


@dataclass(frozen=True)
class RendererConfig:
    rules: tuple[RendererRule, ...] = field(default_factory=tuple)

    def resolve_page_template(self, pac_info: PacInfo) -> str:
        matched = None
        for rule in self.rules:
            if rule.predicate(pac_info):
                matched = rule.template  # keep overwriting - last matching rule in the list wins
        return matched or 'pac_info/pac_info.jinja.html'  # absolute last-resort backstop

    def merge(self, other: 'RendererConfig | None') -> 'RendererConfig':
        if other is None:
            return self
        # Append - issuer rules evaluated after (and so can override) LabFREED's, purely by list position.
        return RendererConfig(rules=self.rules + other.rules)

    @classmethod
    def labfreed_defaults(cls) -> 'RendererConfig':
        return cls(rules=(
            # Ordered most-generic to most-specific: "last match wins", so anything
            # more specific added later (by LabFREED itself, or by an issuer's
            # merge()) naturally overrides.
            RendererRule('generic', lambda pac_info: True, 'pac_info/pac_info.jinja.html'),
            RendererRule('substance', lambda pac_info: bool(pac_info.main_category) and pac_info.main_category.key == '-MS', 'pac_info/digital_label.jinja.html'),
            RendererRule('device', lambda pac_info: bool(pac_info.main_category) and pac_info.main_category.key == '-MD', 'pac_info/device.jinja.html'),
            RendererRule('run', lambda pac_info: bool(pac_info.main_category) and pac_info.main_category.key == '-DR', 'pac_info/run_page.jinja.html'),
        ))
