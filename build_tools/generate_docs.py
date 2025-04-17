from pathlib import Path
import pdoc

pdoc.render.configure(show_source=False, mermaid=True)
output_dir = Path("docs")
pdoc.pdoc('labfreed', output_directory=output_dir)

5

