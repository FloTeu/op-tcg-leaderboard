# op-tcg
Unofficial one piece tcg leaderboard with extended analytic features. 


## Local Setup

### Environment System
```sh
pip install poetry
or
brew install poetry
```
```sh
poetry install --with crawler
```
Access environment in your shell
```sh
poetry shell
```


## Crawling
Get raw data from limitless
```
optcg crawl limitless
```


## Update Big Query Date
Get raw data from limitless
```
optcg etl upload-matches
```