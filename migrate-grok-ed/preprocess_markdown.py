from pathlib import Path
import re
import markdown
import subprocess
import html
from bs4 import BeautifulSoup
from unidecode import unidecode
from itertools import chain
from tqdm import tqdm
from rich import print  # Use rich for all printing


def replace_entities(match):
    unescaped = html.unescape(match.group(0))
    unescaped = unescaped.strip("\n").lstrip("\n")
    return unescaped


def replace_inline_code(text):
    """
    Replace <code data-lang='py3'>...</code> with Markdown backticks.
    """
    pattern = r"<code data-lang='py3'>(.*?)</code>"
    return re.sub(pattern, r"`\1`", text)


def process_file(f: Path):
    # Read the file content
    text = f.read_text()

    # Replace code blocks with language directives
    lines = []
    for line in text.splitlines():
        if re.match("```.+:.*$", line):
            line = re.sub(r"```.*lang:(.+?)(;*)$", r"```\1", line)
            line = line.split(";")[0]
        if not (line.find("```c") > -1 or line.find("```bash") > -1):
            line = re.sub(r"```.*$", r"```", line)
        lines.append(line)

    text = "\n".join(lines)

    # Replace specific text patterns
    text = text.replace("bashshell", "bash")
    text = text.replace(
        """```

```""",
        "",
    )
    text = text.replace("Grok", "Ed").replace("grok", "Ed")
    text = re.sub(r"\s*```", "\n```", text, flags=re.MULTILINE)
    text = text.replace("```norun", "```")
    text = text.replace("$$", "$").replace("@@@", "")

    # Replace inline code
    text = replace_inline_code(text)

    # Check if a .bak file already exists
    backup_path = f.with_suffix(f"{f.suffix}.bak")
    if not backup_path.exists():
        f.rename(backup_path)
    else:
        print(
            f"[yellow]Backup file already exists for {f}. Skipping backup creation.[/yellow]"
        )

    # Write the updated file content back
    f.write_text(text)

    # Convert Markdown to HTML
    html_content = markdown.markdown(text, extensions=["fenced_code"])
    f.with_suffix(".html").write_text(html_content)

    # Get path to the HTML-to-Amber converter
    cpath = Path(__file__).parent / "amber" / "amber-util" / "convert.js"

    # Run the converter
    fabs = f.absolute().with_suffix(".html")
    famber = f.absolute().with_suffix(".xml")
    subprocess.run(["node", cpath, str(fabs), str(famber)])

    # Clean up Amber snippets
    amber_text = famber.read_text()
    amber_text = re.sub(
        r"<snippet>.*?</snippet>", replace_entities, amber_text, flags=re.DOTALL
    )
    famber.write_text(amber_text)


def process_exercises():
    # Glob all markdown files in output/grok_exercises
    origin = Path("output/grok_exercises/")
    files = chain(origin.rglob("*.md"), origin.rglob("solution_notes.md"))
    for f in tqdm(files):
        process_file(f)


def process_modules():
    origin = Path("output/modules/")
    files = chain(origin.rglob("**/*.md"))
    for f in tqdm(files):
        # Convert the markdown to HTML
        text = f.read_text()
        html_content = markdown.markdown(text, extensions=["fenced_code"])
        f.with_suffix(".html").write_text(html_content)

        # Get path to the converter
        cpath = Path(__file__).parent / "amber" / "amber-util" / "convert.js"
        fabs = f.absolute().with_suffix(".html")
        famber = f.absolute().with_suffix(".xml")
        subprocess.run(["node", cpath, str(fabs), str(famber)])


def unescape_file(f: Path):
    xml = f.read_text()
    xml = xml.replace("$$", "$").replace("@@@", "")
    soup = BeautifulSoup(xml, "html.parser")

    for snippet in soup.find_all("snippet"):
        if snippet.string:
            snippet.string = snippet.string.rstrip().lstrip()
            snippet.string = unidecode(html.unescape(snippet.string))
        if not snippet.string:
            snippet.decompose()

    f.write_text(str(soup))


def unescape_all():
    origin = Path("output/grok_exercises/")
    modules = Path("output/modules/")
    files = chain(origin.glob("**/content.xml"), modules.rglob("**/*.xml"))
    for f in tqdm(files):
        unescape_file(f)


def main():
    # Modules disabled at the moment to avoid overwriting the existing files
    process_modules()
    process_exercises()


if __name__ == "__main__":
    main()
    unescape_all()
