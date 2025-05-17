# Campbell Scientific Compiler Repository for crbrs

This repository serves as a community-maintained source for Campbell Scientific datalogger compiler binaries, packaged for use with the `crbrs` command-line interface and its associated tools (like the LSP). It contains a manifest file (`compilers.toml`) that `crbrs` uses to discover and download specific compiler versions.

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
*   `compilers/`: A directory containing the raw Campbell Scientific compiler `.exe` files. This directory is used by the `manage_compilers.py` script to generate the zip archives. Changes here trigger the automation.
*   `manage_compilers.py`: A Python script (using `uv` for self-contained execution) that automates:
    *   Zipping individual executables from the `compilers/` directory into `release_zips/`.
    *   Calculating SHA256 hashes for the zip files.
    *   Updating the `compilers.toml` manifest with new entries, hashes, and the correct download URLs pointing to the future GitHub Release assets.
    *   Updating the `manifest_version` in `compilers.toml` to a CalVer tag (YYYY.MM.DD.micro).
*   `release_zips/`: (Gitignored) A temporary local directory where `manage_compilers.py` outputs the generated `.zip` files before they are uploaded to a GitHub Release by the automation.
*   `.github/workflows/`: Contains GitHub Actions workflows, specifically `release-compilers.yml`, which automates the process of zipping, updating the manifest, creating a GitHub Release (using a CalVer tag), and uploading the generated zip files as assets when changes are pushed to the `compilers/` directory or `manage_compilers.py`.
*   `LICENSE_INFO`: A place to reiterate the licensing disclaimer and provide more detailed information if necessary.
*   `README.md`: This file.

## Using with `crbrs`

The `crbrs` tool is configured by default to point to the `compilers.toml` manifest from this repository.

1.  **List Available Compilers:**
    You can use `crbrs` to see the compilers listed in the manifest:

    ```bash
    crbrs compiler list-available
    ```

2.  **Install a Compiler:**
    Install a compiler by its ID (from the `list-available` output):

    ```bash
    crbrs compiler install <compiler-id-from-list>
    ```
    (Example: `crbrs compiler install cr300comp`)

    `crbrs` will download the corresponding zip asset from the GitHub Release URL specified in the manifest and verify its SHA256 checksum before unpacking it to your local compiler storage directory.

## Contributing or Updating Compilers

Updates to the available compilers (adding new ones, updating versions) are managed through this repository's automated GitHub Actions workflow.

If you want to modify the available compilers (e.g. to contribute a new one or alter them in some way for your own development environment), try forking this repo and if you're ready to contribute back, send a PR and/or open an issue.

**Notes:**

*   **SHA256 Checksums:** These are automatically generated and included in `compilers.toml` for each compiler zip to ensure the integrity of downloads. `crbrs` verifies these checksums after downloading.
*   **Versioning:** The `version` field for each compiler entry in `compilers.toml` ideally reflects the official versioning from Campbell Scientific if known. The `manifest_version` at the top of `compilers.toml` is automatically updated to a CalVer (Calendar Versioning) tag (YYYY.MM.DD.micro) by the automation script and reflects the version of the manifest file itself.
*   **Placeholder URLs:** The `download_url` entries in `compilers.toml` will point to a GitHub Release tag. The `manage_compilers.py` script dynamically updates these URLs to point to the tag generated *for that specific release run*. When contributing, you can ignore the placeholder URL during development; the automation handles setting the correct one.

## License

All content in this repository **except** for the Campbell Scientific compiler binaries themselves (located in the `compilers/` directory and packaged into the release zip assets) is licensed under either of

*   Apache License, Version 2.0, (http://www.apache.org/licenses/LICENSE-2.0)
*   MIT license (http://opensource.org/licenses/MIT)

at your option.

**The compiler binaries (`.exe` files and their packaged zips) are proprietary software owned by Campbell Scientific, Inc. Their usage is governed by Campbell Scientific's licensing terms.**