from pathlib import Path
import re
import markdown
import subprocess
import html
from bs4 import BeautifulSoup
from unidecode import unidecode

from itertools import chain
from tqdm import tqdm


# all printing should be done by rich
from rich import print


def replace_entities(match):
    unescaped = html.unescape(match.group(0))
    unescaped.strip("\n").lstrip("\n")
    return unescaped


def process_file(f: Path):

    # find this regex: "path.*;lang:(.*);.*\n"
    # replace it with group 1
    # write it out again
    text = f.read_text()

    # text = re.sub(r"```.*lang:(.*?);.*\n", r"```\1", text) # TODO: make an RE that works
    text = text.replace("bashshell", "bash")

    lines = []
    for line in text.splitlines():
        if re.match("```.+:.*$", line):
            line = re.sub(r"```.*lang:(.+?)(;*)$", r"```\1", line)
            line = line.split(";")[0]
        if not (line.find("```c") > -1 or line.find("```bash") > -1):
            line = re.sub(r"```.*$", r"```", line)
        lines.append(line)

    text = "\n".join(lines)

    text = text.replace(
        """```

```""",
        "",
    )

    text = re.sub(r"\s*```", "\n```", text, flags=re.MULTILINE)

    text = text.replace("```norun", "```")

    text = text.replace("$$", "$")
    text = text.replace("@@@", "")

    # move the old file to *.bak
    f.rename(f"{f}.bak")
    # write the new file
    f.write_text(text)

    # in the final amber, replace the code blocks with snippets somehow <snippet language=\"py\" runnable=\"true\" line-numbers=\"true\"/>

    # convert the markdown to html
    html = markdown.markdown(text, extensions=["fenced_code"])
    # write the file to html using the same name, with a .html file extension instead of .md
    f.with_suffix(".html").write_text(html)

    # get path of the current file
    cpath = Path(__file__).parent.absolute()
    # add to cpath amber/amber-util/convert.js
    cpath = cpath / "amber" / "amber-util" / "convert.js"

    # then run the html through the html to amber converter (convert.js)
    fabs = f.absolute().with_suffix(".html")
    famber = f.absolute().with_suffix(".xml")
    # print(f'node {cpath} {fabs} {famber}')
    subprocess.run(["node", cpath, str(fabs), str(famber)])

    amber_text = famber.read_text()
    amber_text = re.sub(
        r"<snippet>.*?</snippet>", replace_entities, amber_text, flags=re.DOTALL
    )
    famber.write_text(amber_text)


def process_exercises():
    # glob all markdown files in output/grok_exercises
    # for each file, read it in, and write it out again
    origin = Path("output/grok_exercises/")
    files = chain(origin.rglob("content.md"), origin.rglob("solution_notes.md"))
    for f in tqdm(files):
        process_file(f)


def process_modules():
    origin = Path("output/modules/")
    files = chain(origin.rglob("**/*.md"))
    for f in tqdm(files):
        # process_file(f)
        print(f)
        # TODO this was hacky because didn't run it properly the first time. Remove later
        # convert the markdown to html
        text = f.read_text()
        html = markdown.markdown(text, extensions=["fenced_code"])
        # write the file to html using the same name, with a .html file extension instead of .md
        f.with_suffix(".html").write_text(html)

        # get path of the current file
        cpath = Path(__file__).parent.absolute()
        # add to cpath amber/amber-util/convert.js
        cpath = cpath / "amber" / "amber-util" / "convert.js"
        fabs = f.absolute().with_suffix(".html")
        famber = f.absolute().with_suffix(".xml")
        # print(f'node {cpath} {fabs} {famber}')
        subprocess.run(["node", cpath, str(fabs), str(famber)])


def main():
    pass
    # modules disabled at the moment to avoid overwriting the existing files
    # process_modules()
    process_exercises()


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


if __name__ == "__main__":
    main()
    unescape_all()
