import json
import operator
import re

import jsonpath_ng.ext as jsonpath
from jsonpath_ng.exceptions import JSONPathError
from urllib.parse import quote as url_encode

from labfreed.pac_id_resolver.services import Service, ServiceGroup
from labfreed.pac_id_resolver.resolver_config import ResolverConfig


__all__ = ["ResolverConfigEvaluator"]


_COMPARATORS = {
    '==': operator.eq,
    '!=': operator.ne,
    '<': operator.lt,
    '<=': operator.le,
    '>': operator.gt,
    '>=': operator.ge,
}


class ResolverConfigEvaluator:
    ''' Evaluates a ResolverConfig against a PAC-ID: applicable_if expressions,
    jsonpath lookups and url templating. Kept separate from ResolverConfig
    itself, which is just the data model for a resolver config. '''

    def __init__(self, config: ResolverConfig):
        self._config = config

    def evaluate(self, pac, client_info: dict | None = None) -> ServiceGroup:
        '''`client_info` (e.g. `{"language": ..., "location": ...}`) is merged into the
        Resolver Context alongside the PAC-ID's own fields, so `applicable_if`/`template_url`
        can reference it as `$.client_info....` - forward-looking, not part of the published
        v2 spec (see the PAC-ID-Resolver v3 roadmap, "Resolver Context: beyond just the
        PAC-ID"). Omit it (default) to get exactly today's PAC-ID-only behavior.'''
        pac_id_json = pac.to_dict()
        if client_info is not None:
            pac_id_json = {**pac_id_json, 'client_info': client_info}
        resolver_config_evaluated = ServiceGroup(origin=self._config.origin)
        for block in self._config.config:
            try:
                _, is_applicable = self._evaluate_applicable_if(pac_id_json, block.applicable_if)
            except (SyntaxError, JSONPathError):
                # a malformed applicable_if must not take down resolution of
                # the whole PAC-ID -- same "stable against errors in the
                # resolver config" contract as invalid entries below.
                continue
            if not is_applicable:
                continue

            for e in block.entries:
                if e.errors():
                    continue  # make this stable against errors in the resolver config
                url = self._eval_url_template(pac_id_json, e.template_url)
                resolver_config_evaluated.services.append(Service(
                                                        service_name=e.service_name,
                                                        application_intents=e.application_intents,
                                                        service_type=e.service_type,
                                                        url = url
                                    )
                              )
        return resolver_config_evaluated


    def _evaluate_applicable_if(self, pac_id_json:str, expression) -> tuple[str, bool]:
        expression = self._apply_convenience_substitutions(expression)

        tokens = self._tokenize_jsonpath_expression(expression)
        applicable = _TokenEvaluator(self, pac_id_json, tokens).evaluate()

        return expression, applicable


    def _apply_convenience_substitutions(self, query):
        ''' applies a few substitutions, which enable abbreviated syntax.'''

        # allow access to array elements by key (single or double quoted)
        q_mod = re.sub(r'\[([\'"].+?[\'"])\]', r'[?(@.key == \1)]', query )

        # allow shorter path
        # substitutions = [
        #     (r'(?<=^)id', 'pac.id'),
        #     (r'(?<=^)cat', 'pac.id.cat'),
        #     (r'(?<=\.)id(?=\.)', 'identifier'),
        #     (r'(?<=\.)cat$', 'categories'),
        #     (r'(?<=\.)cat(?=\[)', 'categories'),
        #     (r'(?<=\.)seg$', 'segments'),
        #     (r'(?<=\.)seg(?=\[)', 'segments'),
        #     (r'(?<=^)isu', 'pac.isu'),
        #     (r'(?<=\.)isu', 'issuer'),
        #     (r'(?<=^)ext', 'pac.ext'),
        #     (r'(?<=\.)ext(?=$)', 'extensions'),
        #     (r'(?<=\.)ext(?=\[)', 'extensions'),
        # ]
        # for sub in substitutions:
        #     q_mod = re.sub(sub[0], sub[1], q_mod)

        return q_mod


    def _tokenize_jsonpath_expression(self, expr: str):
        token_pattern = re.compile(
            r"""
            (?P<LPAREN>\() |
            (?P<RPAREN>\)) |
            (?P<LOGIC>\bAND\b|\bOR\b|\bNOT\b) |
            (?P<OPERATOR>==|!=|<=|>=|<|>) |
            (?P<JSONPATH>
                \$                               # starts with $
                (?:
                    [^\s\[\]()]+                # path segments, dots, etc.
                    |
                    \[                           # open bracket
                        (?:                     # non-capturing group
                            [^\[\]]+            # anything but brackets
                            |
                            \[[^\[\]]*\]        # nested brackets (1 level)
                        )*
                    \]
                )+                              # one or more bracket/segment blocks
            ) |
            (?P<STRING>
                "[^"]*"                         # double-quoted literal, spaces allowed
                |
                '[^']*'                         # single-quoted literal, spaces allowed
            ) |
            (?P<LITERAL>
                -?[\w\.\-]+   # domain-like literals
            )
            """,
            re.VERBOSE
        )

        tokens = []
        pos = 0
        while pos < len(expr):
            match = token_pattern.match(expr, pos)
            if match:
                group_type = match.lastgroup
                value = match.group().strip()
                tokens.append((value, group_type))
                pos = match.end()
            elif expr[pos].isspace():
                pos += 1  # skip whitespace
            else:
                raise SyntaxError(f"Unexpected character at position {pos}: {expr[pos]}")

        return tokens


    def _eval_url_template(self, pac_id_json, url_template):
        url = url_template
        placeholders = re.findall(r'\{(.+?)\}', url_template)
        for placeholder in placeholders:
            expanded_placeholder = self._apply_convenience_substitutions(placeholder)
            res = self._evaluate_jsonpath(pac_id_json, expanded_placeholder) or ['']
            url:str = url.replace(f'{{{placeholder}}}', url_encode(str(res[0])))
            url = url.strip()
            # res = self.substitute_jsonpath_expressions(expanded_placeholder, Patterns.jsonpath.value, as_bool=False)
            # url = url.replace(f'{{{placeholder}}}', res)
        return url


    def _evaluate_jsonpath(self, pac_id_json, jp_query):
        if isinstance(pac_id_json, str):
            pac_id_json = json.loads(pac_id_json)
        jsonpath_expr = jsonpath.parse(jp_query)
        matches = [match.value for match in jsonpath_expr.find(pac_id_json)]
        return matches


class _TokenEvaluator:
    ''' Evaluates applicable_if tokens directly against real values, instead of
    reassembling them into a Python source string for eval() -- matched PAC-ID
    content must never be able to influence anything but the comparison it's
    the operand of. '''

    def __init__(self, evaluator: ResolverConfigEvaluator, pac_id_json, tokens):
        self._evaluator = evaluator
        self._json = pac_id_json
        self._tokens = tokens
        self._pos = 0

    def evaluate(self) -> bool:
        result = self._or()
        if self._pos != len(self._tokens):
            raise SyntaxError(f'Unexpected token: {self._peek()[0]!r}')
        return result

    def _peek(self):
        return self._tokens[self._pos] if self._pos < len(self._tokens) else (None, None)

    def _advance(self):
        tok = self._peek()
        self._pos += 1
        return tok

    def _or(self) -> bool:
        result = self._and()
        while self._peek()[1] == 'LOGIC' and self._peek()[0].upper() == 'OR':
            self._advance()
            result = self._and() or result
        return result

    def _and(self) -> bool:
        result = self._not()
        while self._peek()[1] == 'LOGIC' and self._peek()[0].upper() == 'AND':
            self._advance()
            result = self._not() and result
        return result

    def _not(self) -> bool:
        if self._peek()[1] == 'LOGIC' and self._peek()[0].upper() == 'NOT':
            self._advance()
            return not self._not()
        return self._comparison()

    def _comparison(self) -> bool:
        if self._peek()[1] == 'LPAREN':
            self._advance()
            result = self._or()
            if self._advance()[1] != 'RPAREN':
                raise SyntaxError('Missing closing parenthesis')
            return result

        lhs_value, lhs_truthy = self._operand()
        op_tok = self._peek()
        if op_tok[1] == 'OPERATOR':
            self._advance()
            rhs_value, _ = self._operand()
            return _COMPARATORS[op_tok[0]](lhs_value, rhs_value)
        return lhs_truthy

    def _operand(self):
        value, ttype = self._advance()
        if ttype == 'JSONPATH':
            matches = self._evaluator._evaluate_jsonpath(self._json, value)
            resolved = str(matches[0]).upper() if matches else ''
            return resolved, bool(matches)
        if ttype == 'STRING':
            content = value[1:-1]
            return content.upper(), bool(content)
        if ttype == 'LITERAL':
            if value.upper() in ('TRUE', 'FALSE'):
                b = value.upper() == 'TRUE'
                return b, b
            return value.upper(), True
        raise SyntaxError(f'Expected a value, got {value!r}')
