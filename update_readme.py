import re

start_marker = "<!-- BEGIN EXAMPLES -->"
end_marker = "<!-- END EXAMPLES -->"

with open("examples.py", encoding="utf-8") as ex_file:
    example_content = ex_file.read()

# Split on docstring blocks, keeping the docstring delimiters
pattern = r"(?:'''(.*?)'''|\"\"\"(.*?)\"\"\")"
splits = re.split(pattern, example_content, flags=re.DOTALL)

# Rebuild output
output_parts = []
in_code_block = False

def flush_code_block(buffer):
    if buffer:
        return "```python\n" + "".join(buffer).strip() + "\n```\n"
    return ""

code_buffer = []

for i in range(len(splits)):
    chunk = splits[i]
    if chunk is None:
        continue

    # Every odd-numbered chunk is a docstring match (because of how re.split works with groups)
    if i % 3 == 1 or i % 3 == 2:
        # Flush any previous code block
        output_parts.append(flush_code_block(code_buffer))
        code_buffer = []
        docstring = chunk.strip()
        output_parts.append(docstring + "\n")
    else:
        code_buffer.append(chunk)

# Final flush
output_parts.append(flush_code_block(code_buffer))

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
