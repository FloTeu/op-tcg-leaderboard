import os
import random
import requests

from typing import List
from dotenv import load_dotenv

load_dotenv()

def get_headers_list() -> List[str]:
    response = requests.get('http://headers.scrapeops.io/v1/browser-headers?api_key=' + os.getenv("api_token_scrape_ops"))
    json_response = response.json()
    return json_response.get('result', [])


def get_user_agent_list() -> List[str]:
  response = requests.get('http://headers.scrapeops.io/v1/user-agents?api_key=' + os.getenv("api_token_scrape_ops"))
  json_response = response.json()
  return json_response.get('result', [])


def get_random_user_agent():
    user_agent_list = get_user_agent_list()
    return random.choice(user_agent_list)

def get_random_headers():
    headers_list = get_headers_list()
    return random.choice(headers_list)