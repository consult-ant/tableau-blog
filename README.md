# Ant Pulley’s Tableau Blog

This repository contains a static archive of the former WordPress blog. It is
published as a GitHub Pages site; WordPress itself, including comments and
other server-side features, is not required.

## Publishing

The GitHub Actions workflow builds the site from `Consult-Ant/` and deploys it
when changes are pushed to `main` (or when manually started from the Actions
tab). The build keeps the mirrored pages and their local assets, fixes the
archived CSS and JavaScript bundle extensions so browsers can load them from
GitHub Pages, and omits the HTTrack update cache.

To enable deployment, set **Settings → Pages → Build and deployment → Source**
to **GitHub Actions**. The deployed root redirects visitors to the blog at
`consult-ant.uk/`.

The original mirror files remain in `Consult-Ant/`; the build prepares a
separate deployable copy and does not modify the archive.
