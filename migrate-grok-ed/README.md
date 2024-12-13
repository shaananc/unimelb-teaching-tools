# Migrate Grok To Ed

To convert a Grok project to Ed, you need to do the following:

## Installation
- Install all python modules (probably via `pip install poetry && poetry install`)
- Install all the modules for amber-util (probably via `yarn install` or `npm install` in the amber-util directory)
- Fill in the necessary fields in config.ini


## Run

- Host the amber-util using a http server (probably use `npx http-server ./` from the amber-util folder path)
- Run `poetry run python scrape_grok.py` to scrape the data from Grok, 
- Run `poetry run python arrange_files.py` parse it, unpack it.
- Run `poetry run python preprocess_markdown.py` to convert the Markdown to Amber (Ed's format for representing the content of a slide or 'challenge')
- Run `poetry run python upload.py` to upload the scraped data to Ed
