import os
import re
import yaml
import json
import jsonpath_ng.ext as jsonpath


from labfreed.IO.parse_pac import PAC_Parser, PACID_With_Extensions
from labfreed.PAC_ID_Resolver.data_types import CIT, CITEntry, CITEvaluated, Service

from labfreed.PAC_ID_Resolver.non_needed.query_tools import JSONPathTools


def load_cit(path):
    with open(path, 'r') as f:
        cit = yaml.safe_load(f)
        cit = CIT.model_validate(cit)
        return cit


class PAC_ID_Resolver():
    def __init__(self, cits:list[CIT]=None):
        if not cits:
            cits = []
        self.cits = cits
        
        # load the default cit
        dir = os.path.dirname(__file__)
        fn ='cit.yaml'
        p = os.path.join(dir, fn)       
        with open(p, 'r') as f:
            cit = yaml.safe_load(f)
            cit = CIT.model_validate(cit)
            self.cits.append(cit)
        
        
    def resolve(self, pac_id:PACID_With_Extensions|str):
        if isinstance(pac_id, str):
            pac_id = PAC_Parser().parse(pac_id)
        
        pac_id_json = pac_id.model_dump(by_alias=True)
        
        
        # dir = os.path.dirname(__file__)
        # p = os.path.join(dir, 'pac-id.json')
        # with open(p , 'r') as f:
        #     _json = f.read()
        #     pac_id_json = json.loads(_json)
        
        matches = [self._evaluate_against_cit(pac_id_json, cit) for cit in self.cits]
        return matches
            

    def _evaluate_against_cit(self, pac_id_json, cit:CIT):
        cit_evaluated = CITEvaluated(origin=cit.origin)   
        for block in cit.cit:
            _, is_applicable = self._evaluate_applicable_if(pac_id_json, block.applicable_if)
            if not is_applicable:
                continue

            for e in block.entries:
                url = self.eval_url_template(pac_id_json, e.template_url)
                cit_evaluated.services.append(Service(  
                                                        service_name=e.service_name,
                                                        application_intents=e.application_intents,
                                                        service_type=e.service_type,
                                                        url = url
                                    )
                              )            
        return cit_evaluated
    
    
    def _evaluate_applicable_if(self, pac_id_json:str, expression) -> tuple[str, bool]:
        expression = self._apply_convenience_substitutions(expression)
        
        tokens = self._tokenize_jsonpath_expression(expression)
        expression_for_eval = self._expression_from_tokens(pac_id_json, tokens)
        applicable = eval(expression_for_eval, {}, {})
        
        return expression_for_eval, applicable
    
    
    def _apply_convenience_substitutions(self, query):
        ''' applies a few substitutions, which enable abbreviated syntax.'''
        
        # allow access to array elements by key
        q_mod = re.sub(r"\[('.+?')\]", r"[?(@.key == \1)]", query )
        
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
            (?P<LITERAL>
                [A-Za-z_][\w\.\-]*[A-Za-z0-9]   # domain-like literals
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
    
    
    def _expression_from_tokens(self, pac_id_json:str, tokens: tuple[str, str]):
        out  = []
        for i in range(len(tokens)):
            prev_token = tokens[i-1] if i > 0 else (None, None)
            curr_token = tokens[i]
            next_token = tokens[i+1] if i < len(tokens)-1 else (None, None)
            if curr_token[1] == 'JSONPATH':
                res = self._evaluate_jsonpath(pac_id_json, curr_token[0])
                
                if prev_token[1] == 'OPERATOR' or next_token[1] == 'OPERATOR':
                    # if token is part of comparison return the value of the node
                    if len(res) == 0:
                        out.append('""')
                    else:
                        out.append(f'"{res[0].upper()}"')
                else:
                    # if token is not part of comparison evaluate to boolean
                    if len(res) == 0:
                        out.append(False)
                    else:
                        out.append(True)
                        
            elif curr_token[1] == 'LOGIC':
                out.append(curr_token[0].lower())  
                
            elif curr_token[1] == 'LITERAL':
                t = curr_token[0]
                if t[0] != '"':
                    t = '"' + t
                if t[-1] != '"':
                    t = t + '"' 
                out.append(t.upper())    
            else:
                out.append(curr_token[0])
                
        s = ' '.join([str(e) for e in out])
        return s
                    

    
    
    def eval_url_template(self, pac_id_json, url_template):
        url = url_template
        placeholders = re.findall(r'\{(.+?)\}', url_template)
        for placeholder in placeholders:
            expanded_placeholder = self._apply_convenience_substitutions(placeholder)
            res = self._evaluate_jsonpath(pac_id_json, expanded_placeholder) or ['']
            url = url.replace(f'{{{placeholder}}}', str(res[0]))
            # res = self.substitute_jsonpath_expressions(expanded_placeholder, Patterns.jsonpath.value, as_bool=False)
            # url = url.replace(f'{{{placeholder}}}', res)
        return url
    

    
    
    def _evaluate_jsonpath(self, pac_id_json, jp_query):
        jsonpath_expr = jsonpath.parse(jp_query)
        matches = [match.value for match in jsonpath_expr.find(pac_id_json)]
        return matches
    
    

    
    
if __name__ == '__main__':
    r = PAC_ID_Resolver()
    r.resolve()
