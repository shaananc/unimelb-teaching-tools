from pathlib import Path
import re
import markdown
import subprocess
import html
import json
from bs4 import BeautifulSoup
from unidecode import unidecode
from itertools import chain
from tqdm import tqdm
from rich import print  # Use rich for all printing
from configparser import ConfigParser

config = ConfigParser()
config.read("config/config_comp90059.ini")

grok_slug = config.get("GROK", "grok_course_slug")
lesson_type = config.get("ED", "lesson_type")


def replace_entities(match):
    unescaped = html.unescape(match.group(0))
    unescaped = unescaped.strip("\n").lstrip("\n")
    return unescaped


def replace_inline_code(text):
    """
    Replace <code data-lang='py3'>...</code> with Markdown backticks.
    """
    pattern: str = ""
    match lesson_type.lower():
        case "python":
            pattern = r'<code data-lang="py3">(.*?)</code>'
        case "mysql":
            pattern = r'<code data-lang="psql">(.*?)</code>'
    return re.sub(pattern, r"`\1`", text, flags=re.DOTALL | re.IGNORECASE)



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


def process_jsons(f: Path):
    """
    f is a JSON file that should be extracted from into markdown files and runs
        them through Amber.
    """
    print("Processing {}".format(f))
    text = f.read_text()
    json_data = json.loads(text)
    if "content" in json_data.keys():
        content_file = f.with_suffix(".md")
        with open(content_file, "w") as file:
            file.write(json_data["content"])
        json_content = replace_inline_code(json_data["content"])
        html_content = markdown.markdown(json_content, extensions=["fenced_code"])
        content_file.with_suffix(".html").write_text(html_content)

        # Get path to the converter
        cpath = Path(__file__).parent / "amber" / "amber-util" / "convert.js"
        fabs = content_file.absolute().with_suffix(".html")
        famber = content_file.absolute().with_suffix(".xml")
        subprocess.run(["node", cpath, str(fabs), str(famber)])    
    # Create subdirectory for files.
    sub_dir = f.parent / f.stem
    Path(sub_dir).mkdir(parents=True, exist_ok=True)
    # See if there are solution notes.
    if "notes" in json_data.keys() and len(json_data["notes"]) > 0:
        output_path = sub_dir / "solution_notes.html"
        json_content = replace_inline_code(json_data["notes"])
        html_content = markdown.markdown(json_content, extensions=["fenced_code"])
        output_path.write_text(html_content)

        # Get path to the converter
        cpath = Path(__file__).parent / "amber" / "amber-util" / "convert.js"
        fabs = output_path.absolute().with_suffix(".html")
        famber = output_path.absolute().with_suffix(".xml")
        subprocess.run(["node", cpath, str(fabs), str(famber)])
    
    if "teacher_notes" in json_data.keys() and len(json_data["teacher_notes"]) > 0:
        output_path = sub_dir / "teacher_notes.html"
        json_content = replace_inline_code(json_data["teacher_notes"])
        html_content = markdown.markdown(json_content, extensions=["fenced_code"])
        output_path.write_text(html_content)

        # Get path to the converter
        cpath = Path(__file__).parent / "amber" / "amber-util" / "convert.js"
        fabs = output_path.absolute().with_suffix(".html")
        famber = output_path.absolute().with_suffix(".xml")
        subprocess.run(["node", cpath, str(fabs), str(famber)])

    # Split out test files
    sub_dir_test = sub_dir / "tests"
    if "tests" in json_data.keys():
        Path(sub_dir_test).mkdir(parents=True, exist_ok=True)
        test_json = json.loads(json_data["tests"])
        for i, t in enumerate(test_json['tests']):
            HANDLED_TYPES = [0, 1, 2, 4, 5, 6, 8, 10, 13, 14, 15, 22]
            ALT_OUTPUT = [14, 15]
            for filenum, testfile in enumerate(t['files']):
                if testfile["type"] in HANDLED_TYPES:
                    test_folder = Path(sub_dir_test) / f"{i}"
                    test_folder.mkdir(parents=True, exist_ok=True)
                    if 'content' in testfile.keys():
                        test_data = testfile['content']
                    if testfile["type"] == 10:
                        test_driver = test_folder / "test.py"
                    elif testfile["type"] == 1:
                        # Seems like 1 is expected output text contained from program run in 4.
                        test_driver = test_folder / "expected.txt"
                    elif testfile["type"] == 2:
                        # Seems like 2 is some kind of other check.
                        test_driver = test_folder / "okcheck.txt"
                    elif testfile["type"] == 14 or testfile["type"] == 15:
                        test_driver = test_folder / testfile["path"]
                        test_data = testfile['content']
                        import urllib.request
                        urllib.request.urlretrieve(test_data, test_driver)
                    elif testfile["type"] == 13:
                        test_driver = test_folder / "stdout.txt"
                    elif testfile['type'] == 5 or testfile['type'] == 4:
                        # Seems like 4 is a small output text
                        # Seems like 5 is a larger output text
                        test_driver = test_folder / testfile['path']
                    elif testfile["type"] == 8:
                        # PEP8 check
                        test_driver = test_folder / "PEP8Check.sh"
                    else:
                        # Either 0 or 6 go to this
                        # 0 is a mixed input/output
                        # 1 is unknown...
                        # 6 is stdin
                        # 22 is something else - assuming stdin
                        test_driver = test_folder / "stdin.txt"
                    if testfile["type"] not in ALT_OUTPUT:
                        with open(test_driver, "w") as file:
                            file.write(test_data)
                else:
                    assert testfile["type"] in HANDLED_TYPES, f"Haven't seen what other types are like, type for file {filenum} was {testfile['type']}"

    # Split out solution files
    sub_dir_solutions = sub_dir / "solutions"
    if "solutions" in json_data.keys():
        Path(sub_dir_solutions).mkdir(parents=True, exist_ok=True)
        sol_json = json.loads(json_data["solutions"])
        for i, t in enumerate(sol_json):
            if i >= 1:
                for file_data in t:
                    file_path = sub_dir_solutions / f"alternative_{i}" / file_data["path"]
                    file_parent = file_path.parent
                    file_parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(file_data["content"])
            # assert i <= 0, f"Assumed only one solution but actually {i + 1}"
            else:
                for file_data in t:
                    file_path = sub_dir_solutions / file_data["path"]
                    file_parent = file_path.parent
                    file_parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(file_data["content"])

    # Split out scaffold files
    sub_dir_scaffold = sub_dir / "workspace"
    if "workspace" in json_data.keys():
        Path(sub_dir_scaffold).mkdir(parents=True, exist_ok=True)
        ws_json = json.loads(json_data["workspace"])
        for file_data in ws_json:
            file_path = sub_dir_solutions / file_data["path"]
            file_parent = file_path.parent
            file_parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_data["content"])



def process_exercises():
    # Glob all markdown files in output/grok_exercises
    origin = Path(f"output/{grok_slug}/grok_exercises/")
    files = chain(origin.rglob("*.md"), origin.rglob("solution_notes.md"))
    for f in tqdm(files):
        process_file(f)
    exercise_jsons = origin.rglob("*.json")
    for f in tqdm(exercise_jsons):
        process_jsons(f)



def process_modules():
    origin = Path(f"output/{grok_slug}/modules/")
    files = chain(origin.rglob("**/*.md"))
    for f in tqdm(files):
        # Convert the markdown to HTML
        text = f.read_text()
        text = replace_inline_code(text)
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
    origin = Path(f"output/{grok_slug}/grok_exercises/")
    modules = Path(f"output/{grok_slug}/modules/")
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

