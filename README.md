# Campbell Scientific Compiler Repository for crbrs

This repository serves as a community-maintained source for Campbell Scientific datalogger compiler binaries, packaged for use with the `crbrs` command-line interface. It contains a manifest file (`compilers.toml`) that `crbrs` uses to discover and download specific compiler versions.

**The actual compiler binaries are hosted as assets on GitHub Releases within this repository.**

## 🚨 Important Disclaimer: Licensing and Usage 🚨

The compiler binaries are packaged and provided here solely as a convenience for users who are **already licensed by Campbell Scientific to use them.** By downloading or using any compiler package linked from this repository via `crbrs` or other means, you affirm that:

1.  You possess the necessary licenses from Campbell Scientific for the specific compiler(s) you intend to use.
2.  You agree to Campbell Scientific's terms of service and licensing conditions associated with their software.

This repository and the `crbrs` tool are not affiliated with, sponsored by, or endorsed by Campbell Scientific, Inc. All trademarks related to Campbell Scientific belong to their respective owners.

## Purpose

The goal of this repository is to:

1.  Provide a centralized, versioned manifest (`compilers.toml`) detailing available Campbell Scientific compilers.
2.  Offer pre-packaged ZIP archives of individual compiler executables, hosted as GitHub Release assets.
3.  Enable the `crbrs` tool to easily list, download, and manage these compilers for cross-platform CRBasic development.

## Structure

*   `compilers.toml`: The primary manifest file. This TOML file lists available compilers, their versions, descriptions, download URLs (pointing to GitHub Release assets in this repo), SHA256 checksums for integrity, and other metadata.
*   `compilers/`: A directory containing the raw Campbell Scientific compiler `.exe` files. This directory is used by the `manage_compilers.py` script to generate the zip archives. **This directory itself might not be essential to keep in the repo long-term if all executables are reliably versioned through the release zips.**
*   `manage_compilers.py`: A Python script (using `uv` for self-contained execution) that automates:
    *   Zipping individual executables from the `compilers/` directory.
    *   Calculating SHA256 hashes for the zip files.
    *   Updating the `compilers.toml` manifest with new entries, hashes, and download URLs (based on a release tag).
    *   Bumping the `manifest_version` in `compilers.toml`.
*   `release_zips/`: (Gitignored) A temporary local directory where `manage_compilers.py` outputs the generated `.zip` files before they are uploaded to a GitHub Release.
*   `.github/workflows/`: Contains GitHub Actions workflows, for example, to automate the process of zipping, updating the manifest, and creating GitHub Releases when compilers are updated.
*   `LICENSE_INFO`: A place to reiterate the licensing disclaimer and provide more detailed information if necessary.
*   `README.md`: This file.

## Using with `crbrs`

The `crbrs` tool can be configured to use the `compilers.toml` manifest from this repository.

1.  **Find the Raw URL for `compilers.toml`:**
    Navigate to the `compilers.toml` file in this repository on GitHub. Click the "Raw" button. Copy the URL from your browser's address bar.

2.  **Configure `crbrs`:**
    ```bash
    crbrs config set compiler_repository_url <RAW_URL_OF_COMPILERS.TOML_FROM_STEP_1>
    ```

3.  **List Available Compilers:**
    ```bash
    crbrs compiler list-available
    ```

4.  **Install a Compiler:**
    ```bash
    crbrs compiler install <compiler-id-from-list>
    ```
    (Example: `crbrs compiler install cr300comp`)

## Contributing or Updating Compilers

Updates to the available compilers (adding new ones, updating versions) are managed through this repository, ideally via Pull Requests and an automated GitHub Actions workflow.

**General Workflow (Manual or Automated):**

1.  **Add/Update Executables:** Place new or updated compiler `.exe` files into the `compilers/` directory.
2.  **Run Management Script:** Execute `python manage_compilers.py` (or `uv run manage_compilers.py`). This will:
    *   Create/update zip archives in `release_zips/`.
    *   Update `compilers.toml` with SHA256 hashes and new entries/versions. The download URLs will be placeholders initially or constructed if a `RELEASE_TAG` environment variable is set (used by CI).
3.  **Commit Changes:** Commit the updated `compilers.toml` (and potentially the `manage_compilers.py` script if it was changed).
4.  **Create GitHub Release:**
    *   Create a new tag (e.g., `vX.Y.Z`, matching the `manifest_version` from `compilers.toml`).
    *   Create a new GitHub Release associated with this tag.
    *   Upload all `.zip` files from `release_zips/` as assets to this release.
5.  **Finalize `compilers.toml`:**
    *   Update the `download_url` fields in `compilers.toml` to point to the actual URLs of the assets you just uploaded to the GitHub Release.
    *   Commit and push this final version of `compilers.toml`.

**Automation via GitHub Actions:**
A GitHub Actions workflow in `.github/workflows/` aims to automate steps 2-5 when changes are pushed to the `compilers/` directory or the management script.

## Notes

*   **SHA256 Checksums:** These are provided in `compilers.toml` for each compiler zip to ensure the integrity of downloads. `crbrs` should verify these checksums after downloading.
*   **Versioning:** The `version` field for each compiler in `compilers.toml` should reflect the official versioning from Campbell Scientific if known. The `manifest_version` at the top of `compilers.toml` refers to the version of the manifest file itself and its structure.
