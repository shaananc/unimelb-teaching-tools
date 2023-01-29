   
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
    print("HERE!")
    unescaped = html.unescape(match.group(0))
    unescaped.strip('\n').lstrip("\n")
    return unescaped

def main():
    # glob all markdown files in output/grok_exercises
    # for each file, read it in, and write it out again
    origin = Path('output/grok_exercises/')
    files = chain(origin.glob('**/content.md'), origin.glob('**/solution_notes.md'))
    print(files)
    for f in tqdm(files):
        if not '4.10,11' in str(f.absolute()):
            continue

        # find this regex: "path.*;lang:(.*);.*\n"
        # replace it with group 1
        # write it out again
        text = ""
        with open(f, 'r') as fin:
            text = fin.read()
            # first check if the file has the regex
            if re.search(r'lang:(.*).*\n', text):
                # print the file name
                print(f)

                text = text.replace("bashshell","bash")
                text = re.sub(r'```.*lang:(.*?);.*\n', r'```\1\n\n', text)  
                text = text.replace('''```

```''','')
                #print(text)
                #break
            
        # move the old file to *.bak
        f.rename(f'{f}.bak')
        # write the new file
        with open(f, 'w') as fout:
            fout.write(text)

        
        # in the final amber, replace the code blocks with snippets somehow <snippet language=\"py\" runnable=\"true\" line-numbers=\"true\"/>

        # convert the markdown to html
        html = markdown.markdown(text, extensions=['fenced_code'])
        # write the file to html using the same name, with a .html file extension instead of .md
        with open(f.with_suffix('.html'), 'w') as fout:
            fout.write(html)



        # get path of the current file
        cpath = Path(__file__).parent.absolute()
        # add to cpath amber/amber-util/convert.js
        cpath = cpath / 'amber' / 'amber-util'/'convert.js'

        # then run the html through the html to amber converter (convert.js)
        fabs = f.absolute().with_suffix('.html')
        famber = f.absolute().with_suffix('.xml')
        #print(f'node {cpath} {fabs} {famber}')
        subprocess.run(['node', cpath, str(fabs), str(famber)])

        # amber_text = ""
        # with open(famber, 'r') as fin:
        #     amber_text = fin.read()




        # amber_text = re.sub(r"<snippet>.*?</snippet>", replace_entities, amber_text, flags=re.DOTALL)

        # with open(famber, 'w') as fout:
        #     fout.write(amber_text)


def unescape_all():
    origin = Path('output/grok_exercises/')
    files = chain(origin.glob('**/content.xml'))
    for f in tqdm(files):
        # if not '4.10,11' in str(f.absolute()):
        #     continue

        # print("Unescaping: " + str(f))

        soup = ""
        with open(f, 'r') as fin:
            soup = BeautifulSoup(fin.read(), 'html.parser')

        #print(soup)
        for snippet in soup.find_all("snippet"):
            if snippet.string:
                snippet.string = snippet.string.rstrip().lstrip()
                snippet.string = unidecode(html.unescape(snippet.string))
            if not snippet.string:
                snippet.decompose()
        #         print(snippet.string)
        #         print("HERE!")
        # print(soup)

        with open(f, 'w') as fout:
            fout.write(str(soup))

#main()
unescape_all()