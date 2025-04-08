# update_readme.py
start_marker = "<!-- BEGIN EXAMPLES -->"
end_marker = "<!-- END EXAMPLES -->"

with open("examples.py") as ex_file:
    example_code = ex_file.read()

# Optional: Format as Markdown code block
example_code_md = f"```python\n{example_code}\n```"

with open("README.md") as readme_file:
    readme = readme_file.read()

# Replace the section between markers
new_readme = (
    readme.split(start_marker)[0]
    + start_marker + "\n"
    + example_code_md + "\n"
    + end_marker
    + readme.split(end_marker)[1]
)
new_readme.replace

with open("README.md", "w") as readme_file:
    readme_file.write(new_readme)
