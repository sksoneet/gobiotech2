# Putting GoBiotech on GitHub

You need: a free GitHub account (github.com/signup). Keep the repository **Public**: GitHub Pages
(the free website hosting used here) only works for private repositories on paid plans.

## Option A: browser only (no command line)

1. Sign in, click **+ > New repository**. Name: `gobiotech`. Choose **Public**. Do not add a README. Create it.
2. On your computer, unzip `gobiotech-project.zip`.
   - **Mac:** the `.github` folder is hidden. In Finder press Cmd+Shift+. (full stop) to show hidden files.
   - **Windows:** File Explorer > View > Show > Hidden items.
3. In the new repository click **uploading an existing file**. Select everything inside the unzipped folder
   (`.github`, `data`, `docs`, `tools`, `README.md`, `requirements.txt`, `.gitignore`) and drag it in.
   Confirm the file list includes `.github/workflows/check-sources.yml` and `deploy-pages.yml`, then **Commit changes**.
   (If the hidden `.github` folder will not drag in, use Add file > Create new file, type
   `.github/workflows/deploy-pages.yml` as the name, and paste in the file's contents; repeat for the other workflow.)
4. **Settings > Actions > General > Workflow permissions**: choose **Read and write permissions**. Save.
5. **Settings > Pages > Build and deployment > Source**: choose **GitHub Actions**.
6. **Actions** tab > **Build and deploy website** > **Run workflow**. When it turns green, your site is at
   `https://YOUR-USERNAME.github.io/gobiotech/`.
7. **Actions** tab > **Check institute sources** > **Run workflow**. The first run saves baselines of every source page.

## Option B: command line

```bash
cd gobiotech                      # the unzipped folder
git init -b main
git add -A
git commit -m "Initial GoBiotech data and tools"
# with the GitHub CLI (https://cli.github.com), after `gh auth login`:
gh repo create gobiotech --public --source=. --push
# or create the empty repository in the browser, then:
# git remote add origin https://github.com/YOUR-USERNAME/gobiotech.git
# git push -u origin main
```
Then do steps 4 to 7 above.

## What to expect on the first checker run
- It visits about 125 source links. Aggregator pages (Careers360, Collegedunia) may block automated visits or
  be slow; those show up as "could not fetch". That is useful: it tells you which links to replace.
- Links that are cut off (for example the Manav Rachna B.Tech link) will fail. Fix them in `data/institutes.json`.
- The first run only records baselines, so it will not report content changes until the second run.
- Prefer official admission notices and prospectuses as sources; they change less often for unrelated reasons.

## Each week
Open the Issue the checker creates, check each flagged page against the source, edit `data/institutes.json`
(the pencil icon on GitHub works), set `last_checked`, and commit. The website rebuilds by itself.
After you confirm a change, run **Check institute sources** with the `--accept` option locally, or simply
let the next weekly run record the new page as the baseline.

## Custom domain (after you buy it)
Settings > Pages > **Custom domain**. At your registrar add a CNAME record `www` pointing to
`YOUR-USERNAME.github.io`, or the four GitHub Pages A records for the bare domain, then tick **Enforce HTTPS**.
