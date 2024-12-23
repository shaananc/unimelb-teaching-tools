import re
import html
import markdownify


def escape_doublequotes(text):
    return text.replace('"', '\\"')

def replace_entities(match):
    unescaped = html.unescape(match.group(0))
    unescaped = unescaped.strip("\n").lstrip("\n")
    return unescaped

#def modify_terminal_output(text, lang):


def replace_terminal_outputs_without_lang(text):
    pattern :str = r'```eg:last;\s*terminal;.*?```'
    replaced_text = str(re.sub(pattern, "", text, flags=re.DOTALL))
    pattern: str = r'```eg:last;(.*?)```'
    replaced_text = str(re.sub(pattern, r"`\1`", replaced_text, flags=re.DOTALL))
    pattern: str = r'```terminal;eg:none;(.*?)```'
    replaced_text = re.sub(pattern, r"`\1`", replaced_text, flags=re.DOTALL)
    pattern: str = r'```terminal;(.*?)```'
    replaced_text = re.sub(pattern, "", replaced_text, flags=re.DOTALL)
    pattern: str = r'```norun;(.*?)```'
    replaced_text = str(re.sub(pattern, r"`\1`", replaced_text, flags=re.DOTALL))
    pattern: str = r'```exportable;terminal;eg:none;(.*?)```'
    replaced_text = re.sub(pattern, r"`\1`", replaced_text, flags=re.DOTALL)
    pattern: str = r'```exportable;(.*?)```'
    replaced_text = re.sub(pattern, r"`\1`", replaced_text, flags=re.DOTALL)
    pattern: str = r'```readonly;(.*?)```'
    replaced_text = re.sub(pattern, r"`\1`", replaced_text, flags=re.DOTALL)
    pattern: str = r'`readonly;(.*?)`'
    replaced_text = re.sub(pattern, r"`\1`", replaced_text, flags=re.DOTALL)
    pattern: str = r'`lang:txt;path:.*;(.*?)`'
    replaced_text = re.sub(pattern, r"`\1`", replaced_text, flags=re.DOTALL)
    pattern :str = r'```eg:none;\s*terminal;(.*?)```'
    return re.sub(pattern, r"`\1`", replaced_text, flags=re.DOTALL)


def replace_terminal_outputs_with_lang(text, lang):
    pattern: str = fr'```eg:last;lang:{lang};terminal;.*?```'
    replaced_text =  str(re.sub(pattern, "", text, flags=re.DOTALL))
    pattern: str = fr'```eg:none;lang:{lang};terminal;(.*?)```'
    replaced_text  = str( re.sub(pattern, r"`\1`", replaced_text, flags=re.DOTALL))
    pattern:str = rf'```lang:{lang};terminal;eg:none;(.*?)```'
    return re.sub(pattern, r"`\1`", replaced_text, flags=re.DOTALL )




def replace_inline_code(text, lesson_type, replace_output= True, replace_html_table: bool = True):
    """
    Replace code and outputs with Markdown backticks.
    """
    lang  = ""
    pattern3 = r'language=\"bash\"' # converts the language from generic bash to actual language, this was not handled in DocumentFormat.js
    replacement3 = ""

    match lesson_type.lower():
        case "python":
            replacement3 = f'language=\"py\"'
            lang = "py3"
        case "mysql":
            replacement3 = f'language=\"psql\"'
            lang = "mysql"
    pattern1: str = fr"<code data-lang=('|\"){lang}('|\")>(.*?)</code>"  # converts code blocks into `code markdown text`
    pattern2: str = rf'`lang:{lang};(.*?)`' # converts code blocks into `code markdown text`
    pattern4: str = fr'```eg:[a-zA-Z0-9\-]*;lang:{lang};(.*?)```' # converts code blocks into `runnable code blocks markdown`
    pattern5: str = r'`lang:(out|str|int|err|in);(.*?)`'
    pattern6: str = fr'```eg:[a-zA-Z0-9\-]*;{lesson_type};(.*?)```'
    text = str(replace_terminal_outputs_without_lang(text)) # replaces the terminal outputs which are unnecessary
    text = str(replace_terminal_outputs_with_lang(text, lang))
    text = str(replace_comments(text))  # replace the comments
    text = str(re.sub(pattern1, r"`\3`", text, flags=re.DOTALL | re.IGNORECASE))
    text = str(re.sub(pattern2, r"`\1`", text, flags=re.DOTALL | re.IGNORECASE))
    text = str(re.sub(pattern3, replacement3, text))
    text = str(re.sub(pattern4, r"```\1```", text, flags=re.DOTALL | re.IGNORECASE))
    text = str(re.sub(pattern5, r"`\1`", text, flags=re.DOTALL | re.IGNORECASE))
    text = str(re.sub(pattern6, r"```\1```", text, flags=re.DOTALL))
    if replace_html_table:
        text = convert_html_table(text)
    return text


def replace_comments(text: str):
    """
    Replace <!-- --> with Markdown backticks.
    Args:
        text: text that contains the comments.
    Returns: replaced text

    """

    pattern: str = r'<!--(.*?)-->'
    if re.search(pattern, text):
        print("xml comments updated")
    return re.sub(pattern, "", text)

def convert_html_table(text):
    pattern:str = r'<table(.*?)</table>'
    tables = re.findall(pattern, text, flags=re.DOTALL|re.IGNORECASE)

    for i, t in enumerate(tables, start = 1):
        if t.strip() == "":
            continue

        table_text = "<table" +t + "</table>"
        markdown_table = markdownify.markdownify(table_text)
        new_mk_tbl = ""
        for mt in markdown_table.split("\n"):
            new_mk_tbl += mt + "\\n"
        text = text.replace(table_text, '<code>\n' + new_mk_tbl + "\n</code>")
    return text
