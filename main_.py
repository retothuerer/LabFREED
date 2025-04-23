import json
from jsonpath_ng.ext import parse

data = {
    "issuer": "METTORIUS.COM",
    "identifier": [
        {"key": None, "value": "-MS"},
        {"key": None, "value": "X3511"},
        {"key": "CAS", "value": "7732-18-5"}
    ],
    "extensions": [],
    "categories": [
        {
            "key": "-MS",
            "segments": [
                {"key": "240", "value": "X3511"},
                {"key": "CAS", "value": "7732-18-5"}
            ]
        }
    ]
}

data = '{"issuer":"METTORIUS.COM","identifier":[{"key":null,"value":"-MS"},{"key":null,"value":"X3511"},{"key":"CAS","value":"7732-18-5"}],"extensions":[],"categories":[{"key":"-MS","segments":[{"key":"240","value":"X3511"},{"key":"CAS","value":"7732-18-5"}]}]}'
data = json.loads(data)
# Use jsonpath_ng.ext.parse to handle quoted strings like "-MS"
expr = parse('$.categories[?(@.key == "-MS")].segments[?(@.key == "CAS")]')

# Evaluate expression
matches = [match.value for match in expr.find(data)]

# Print results
print(matches)

5