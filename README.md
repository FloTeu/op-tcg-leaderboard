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

## Vercel Deployment

The FastHTML application can be deployed to Vercel. The deployment is configured to serve static files (CSS and JavaScript) from the `/static` route.

### Static Files Setup
Static files are automatically copied during deployment via the `buildCommand` in `vercel.json`. You can also manually prepare static files for deployment:

```shell
python prepare_deployment.py
```

This script copies all static files from `op_tcg/frontend_fasthtml/static/` to the root `static/` directory where Vercel can serve them.

### Deployment Configuration
The `vercel.json` file is configured to:
- Copy static files during build: `cp -r op_tcg/frontend_fasthtml/static ./static`
- Serve static files directly from `/static/*` routes (handled by Vercel)
- Route all non-static requests to the FastHTML application in `api/index.py`
- Use Python 3.11 runtime for the serverless function

### Route Configuration
The key configuration uses a negative lookahead regex to exclude static files from being processed by the Python handler:
```json
{
  "src": "/((?!static).*)$",
  "dest": "api/index.py"
}
```

This ensures that:
- `/static/*` requests are served directly as static files
- All other requests go to your FastHTML application

### Testing Static Files
After deployment, you can test static file serving by visiting:
- `https://your-app.vercel.app/static/test.txt`
- `https://your-app.vercel.app/static/css/loading.css`
- `https://your-app.vercel.app/static/js/utils.js`

### Environment Variables
Make sure to set the following environment variables in your Vercel project:
- `GOOGLE_SERVICE_KEY` (base64 encoded service account JSON)
- `GOOGLE_CLOUD_PROJECT` (your GCP project ID)

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