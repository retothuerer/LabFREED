import os
import re
import io
import contextlib
from rich.text import Text

start_marker = "<!-- BEGIN EXAMPLES -->"
end_marker = "<!-- END EXAMPLES -->"

with open("examples/examples.py", encoding="utf-8") as ex_file:
    example_content = ex_file.read()

# Match blocks: either triple-quoted docstrings or plain code chunks
pattern = r"(?P<docstring>'''(.*?)'''|\"\"\"(.*?)\"\"\")"
matches = list(re.finditer(pattern, example_content, flags=re.DOTALL))

output_parts = []
last_index = 0

shared_globals = {
    "__file__": os.path.abspath("build_tools/examples.py")
}

def run_code_block(code_str):
    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            exec(code_str, shared_globals)
    except Exception as e:
        return f"[Error during execution: {e}]"
    return stdout.getvalue().strip()


def format_output_as_html(output: str) -> str:
    lines = output.splitlines()
    formatted = "\n".join(f">> {line}" for line in lines)
    html_output = f"<pre><code style=\"color: green\">{formatted}</code></pre>"
    return html_output


def format_output(output: str) -> str:
    output = Text.from_ansi(output).plain
    lines = output.splitlines()
    formatted = "\n".join(f">> {line}" for line in lines)
    return  f"```text\n{formatted}\n```"


for match in matches:
    # Capture code before this docstring
    code_chunk = example_content[last_index:match.start()]
    if code_chunk.strip():
        code_block = code_chunk.strip("\n")
        output_parts.append(f"```python\n{code_block}\n```")

        result = run_code_block(code_block)
        if result:
            output_parts.append(format_output(result))

    # Capture the docstring itself
    doc = match.group(0).strip('\'" \n')
    if doc:
        output_parts.append(doc.strip() + "\n")

    last_index = match.end()

# Add any remaining code after the last docstring
if last_index < len(example_content):
    remaining_code = example_content[last_index:].strip("\n")
    if remaining_code.strip():
        output_parts.append(f"```python\n{remaining_code}\n```")

        result = run_code_block(remaining_code)
        if result:
            output_parts.append(format_output(result))

# Combine the parts
example_content_md = "\n".join(part for part in output_parts if part.strip())

# Inject into README.md
with open("README.md", encoding="utf-8") as readme_file:
    readme = readme_file.read()

if not readme:
    raise ValueError("README.md is empty")

if start_marker not in readme or end_marker not in readme:
    raise ValueError("Markers not found in README.md")

new_readme = (
    readme.split(start_marker)[0]
    + start_marker + "\n"
    + example_content_md + "\n"
    + end_marker
    + readme.split(end_marker)[1]
)

with open("README.md", "w", encoding="utf-8") as readme_file:
    readme_file.write(new_readme)
