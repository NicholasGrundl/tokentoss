# nicholasgrundl-registry


# insilicostrategy

## Initial Deployment

1. Clean up repo
2. build and manually deploy a new docker setup to DO droplet (see md instructions)
3. setup SA key for docker pulling in DO droplet
4. update initial documentation


## CI/CD
1. Connect Cloud Build trigger to GitHub repo
2. Create a read-only SA with `artifactregistry.reader`, activate on droplet via `gcloud auth configure-docker us-west1-docker.pkg.dev`
3. Add Watchtower to `docker-compose.yml` on the droplet
4. Create Gemini API key and add to `.env` on droplet

**Future improvement:** Migrate from `.env` to Secret Manager when the number of secrets grows or you need rotation. Enable `secretmanager.googleapis.com` at that point and use a bootstrap script on the droplet to fetch secrets on startup.



# nicholasgrundl-site

## Initial Deployment

Double check current deployment and mirror any updates we might want

## CI/CD

**Next steps (outside this runbook):**
1. Set up Workload Identity Federation in `nicholasgrundl-registry` for GitHub Actions (pool + provider + SA with `artifactregistry.writer`)
2. Create a read-only SA in `nicholasgrundl-registry` with `artifactregistry.reader`, generate a key, activate on droplet via `gcloud auth configure-docker us-west1-docker.pkg.dev`
3. Write GitHub Actions workflow: build → push to registry (no deploy step needed)
4. Add [Watchtower](https://containrrr.dev/watchtower/) to `docker-compose.yml` on the droplet to auto-pull and restart on new images


# nicholasgrundl-sandbox


