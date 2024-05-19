# op-tcg
Unofficial one piece tcg leaderboard with extended analytic features. 


## Local Setup

What you need:
* [Google cloud cli](https://cloud.google.com/sdk/docs/install-sdk?hl=de)
* Google Cloud IAM permission
* Populate `.env` file with help of `.env.template`

### Environment System
[Install pipx](https://github.com/pypa/pipx) first
```sh
pipx install poetry
```
```sh
poetry install --with crawler,frontend
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
Push data to Google Cloud BigQuery (expects a dataset `matches` already existing)
```
optcg etl upload-matches
```


## Start Local Frontend Server
```
optcg frontend start
```


## Cloud Setup
The app is running in Google cloud and can be initialized by terraform. 

### Prerequisites
* Activate Cloud Functions API
* Activate Cloud Run API
* Activate Cloud Build API 
* Activate Cloud Scheduler API 
* Setup IAM service account with BigQuery read/write access