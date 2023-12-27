import requests

from op_tcg.crawling.common import get_random_headers, get_random_user_agent
from op_tcg.crawling.selenium_fns import SeleniumBrowser

browser = SeleniumBrowser()

headers = get_random_headers()
browser.setup(headless=False,
              headers=headers,
              allow_javascript=True,
              disable_images=True
              )

browser.driver.get("https://www.cardmarket.com/de/OnePiece/Products/Singles?site=3&mode=list")
html = browser.driver.page_source