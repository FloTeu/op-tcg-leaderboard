# op-tcg
Unofficial one piece tcg leaderboard with extended analytic features. 

## Application
The app is currently deployed in the community cloud of streamlit.
PROD: https://optcg-leaderboard.streamlit.app/
DEV: https://optcg-leaderboard-dev.streamlit.app/

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

## Local development
For local development it's recommended to set the `DEBUG` value in the environment file to true. 
If `DEBUG` is true you also need to start the frontend code via localhost at port 3002.
```
cd components/nivo_charts/nivo_charts/frontend
npm install    # Install npm dependencies
npm run start  # Start the Webpack dev server
```

## Crawling
Get tournament data from limitless
```
optcg crawl limitless tournaments
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

## Cloud Deployment
If not already done, update package version
```shell
poetry version patch/minor/major/prepatch/preminor/premajor/prerelease
```
Ensure the frontend components are up-to-date
```shell
cd components/nivo_charts/nivo_charts/frontend
sh build.sh
```
```shell
cd terraform
sh terraform_apply.sh
```