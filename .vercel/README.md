# Vercel Deployment

This directory contains the Vercel deployment configuration for the OP TCG Leaderboard.

## Structure

- `.vercel/output/` - Vercel Build Output API v3 structure
  - `config.json` - Main deployment configuration
  - `static/` - Static assets (CSS, JS, images)
  - `functions/` - Serverless functions
    - `index.func/` - Main FastHTML application function

## Deployment Process

### Automated (GitHub Actions)
1. Push to main/master branch triggers automatic deployment
2. GitHub Actions runs `deploy_vercel.py` to prepare the deployment
3. Vercel CLI deploys the application

### Manual Deployment
1. Run `python deploy_vercel.py` to prepare the deployment
2. Set environment variables in Vercel dashboard:
   - `GOOGLE_SERVICE_KEY` - Base64 encoded service account JSON
   - `GOOGLE_CLOUD_PROJECT` - Your Google Cloud project ID
3. Deploy using `vercel --prod`

## Static Files

Static files are served from `/static/` and include:
- CSS files for styling (leaderboard.css, multiselect.css, etc.)
- JavaScript files for interactivity (utils.js, sidebar.js, etc.)
- Any images or other assets

The FastHTML application is configured to serve static files from `.vercel/output/static/`.

## Environment Variables

### Required
- `GOOGLE_SERVICE_KEY`: Base64 encoded Google Cloud service account JSON key
- `GOOGLE_CLOUD_PROJECT`: Your Google Cloud project ID

### GitHub Actions Secrets (for automated deployment)
- `VERCEL_TOKEN`: Vercel authentication token
- `VERCEL_ORG_ID`: Vercel organization ID
- `VERCEL_PROJECT_ID`: Vercel project ID

### Optional
- `PYTHONPATH`: Set to "." (configured automatically)

## Troubleshooting

- Check Vercel function logs for runtime errors
- Ensure all dependencies are in requirements.txt
- Verify environment variables are set correctly
- Check that static files are accessible at `/static/` URLs
- Validate that the FastHTML app uses `static_path='.vercel/output/'`

## File Structure

```
.vercel/
├── output/
│   ├── config.json          # Vercel routing configuration
│   ├── static/              # Static assets
│   │   ├── css/            # Stylesheets
│   │   └── js/             # JavaScript files
│   └── functions/          # Serverless functions
│       └── index.func/     # Main application function
│           ├── .vc-config.json
│           └── index.py
└── README.md               # This file
```
