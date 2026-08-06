# Building the SMuFL specification

The SMuFL specification is published using [mdBook](https://rust-lang.github.io/mdBook/), an open source package for producing books using Markdown sources.

This document describes the build process for the SMuFL specification.

## Repository layout

**BUILDING.md** is this document.

**font** contains `Bravura.ufo`, the canonical UFO source for the Bravura reference font. `Bravura.otf` is built from it by `tools/generate_font.py` and is not committed — see [CONTRIBUTING.md](CONTRIBUTING.md#how-this-connects-to-bravura).

**drafts** contains published drafts of the SMuFL specification. Each draft version should be contained in a subfolder named _version-date_, e.g. **1.4-2021-01-03**. The contents of each subfolder is a complete set of GitBook (for versions up to 1.4) or mdBook (for 1.5 or later) output.

**gitbook** contains a single file **index.html**. Because of limitations in GitHub Pages, we use an old-fashioned HTML meta tag with http-equiv attribute to redirect visitors who land at https://w3c.github.io/smufl to the latest version of the specification, which is found at **/latest**.

**index.html** similarly redirects to **/latest**.

**latest** is not stored in the repository — it's built fresh from **mdbook** and published by the GitHub Actions workflow on every push to **gh-pages** (see below).

**mdbook** contains the input and configuration files used to build the mdBook output.

**metadata** contains the latest versions of the standard SMuFL metadata files.

**README.md** is a brief description of this repository.

**releases** contains published versions of the SMuFL specification. Each published version should be in a subfolder named _version_, e.g. **1.4**. The contents of each subfolder is a complete set of GitBook (for versions up to 1.4) or mdBook (for 1.5 or later) output.

**scripts** contains some useful scripts for working with SMuFL fonts in different font editing software.

**w3c.json** contains configuration data used by the W3C organisation to manage their many GitHub repositories.

**metadata/schema** contains [JSON Schema](https://json-schema.org/) definitions for **glyphnames.json**, **classes.json** and **ranges.json**, plus **check_consistency.py**, a script that checks relationships between those three files that a schema alone can't express (e.g. that every glyph's codepoint falls within the range it belongs to).

**.github/workflows/pages.yml** is the GitHub Actions workflow that validates and publishes the specification (see below).

## Prerequisites

* [Install mdBook](https://rust-lang.github.io/mdBook/guide/installation.html)
* Python 3, if you want to run the metadata validation locally (`pip install check-jsonschema`)

## Updating the specification

The working folder is **mdbook/src**. This contains all of the Markdown sources for the specification.

The structure of the book is described in **SUMMARY.md**. To add one or more new pages to the specification, it must be added to this file.

The configuration for the overall book is **mdbook/book.toml**, a configuration file in [TOML](https://toml.io/en/), but it should not normally be necessary to adjust this configuration file.

The **theme** folder contains overrides to mdBook's default theme. It is advised only to include files that differ from the default theme, to be able to take advantage of improvements and fixes added to the default theme.

mdBook has a very handy local web server that updates the book live as the Markdown source files and theme data are updated. To run the local web server and preview the book, using Terminal:

```
mdbook serve --open
```

This will open the default web browser and point it at the local web server.

## Validating your changes locally

Before opening a pull request, it's worth running the same checks CI will run. From the root of the repository:

```
pip install check-jsonschema
check-jsonschema --schemafile metadata/schema/glyphnames.schema.json metadata/glyphnames.json
check-jsonschema --schemafile metadata/schema/ranges.schema.json metadata/ranges.json
check-jsonschema --schemafile metadata/schema/classes.schema.json metadata/classes.json
python3 metadata/schema/check_consistency.py
```

And that the book itself builds without errors:

```
cd mdbook
mdbook build
```

## Building and publishing the specification

Publishing is automated. Every push and pull request against **gh-pages** triggers the **Validate and publish specification** GitHub Actions workflow (`.github/workflows/pages.yml`), which:

1. Validates **glyphnames.json**, **classes.json** and **ranges.json** against their JSON Schemas, and runs the cross-file consistency checks.
2. Builds the book with `mdbook build` to confirm the Markdown sources are well-formed.

On a push to **gh-pages** (i.e. once a pull request is merged), a second job also runs, which builds `Bravura.otf` from `font/Bravura.ufo`, copies it into the book's media folder, builds the book again, assembles the site (the built book, plus **drafts**, **releases**, **gitbook**, **metadata**, **index.html** and **w3c.json**), and deploys it directly to GitHub Pages. There is no longer a manual "build, rename the folder, commit" step — merging is enough.

This requires the repository's Pages source (Settings → Pages) to be set to "GitHub Actions" rather than "Deploy from a branch".
