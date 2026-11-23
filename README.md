# Ant Pulley’s Tableau Blog

This repository contains a static archive of the former blog. It is published
as a GitHub Pages site; comments and other server-side features are not
required.

## Publishing

The GitHub Actions workflow builds the site from `Consult-Ant/` and deploys it
when changes are pushed to `main` (or when manually started from the Actions
tab). The build keeps the mirrored pages and their local assets, fixes the
archived CSS and JavaScript bundle extensions so browsers can load them from
GitHub Pages, removes old platform links, branding, promotional banners,
subscription prompts, comment and like controls, and omits the HTTrack update
cache. The Contact page points visitors to LinkedIn instead of displaying the
archived contact form.

To enable deployment, set **Settings → Pages → Build and deployment → Source**
to **GitHub Actions**. The deployed root redirects visitors to the blog at
`consult-ant.uk/`.

The original mirror files remain in `Consult-Ant/`; the build prepares a
separate deployable copy and does not modify the archive.

The build copies `ap-monogram-parametric-sliceFavicon.svg` into the deployed
site and replaces the archived WordPress favicon links with the monogram.
