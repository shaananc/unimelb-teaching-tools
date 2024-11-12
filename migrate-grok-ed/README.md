# Migrate Grok To Ed

To convert a Grok project to Ed, you need to do the following:

- Install all python modules (probably via `pip install poetry && poetry install`)
- Install all the modules for amber-util (probably via `yarn install` in the amber-util directory)
- Fill in the necessary fields in config.ini
- Run `poetry run python scrape_grok.py` to scrape the data from Grok, parse it, unpack it, and convert the Markdown to Amber (Ed's format for representing the content of a slide or 'challenge')
- Run `poetry run python scrape_grok.py` to upload the scraped data to Ed
