#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "toml>=0.10.2,<1.0.0",
#   "packaging>=21.3"
# ]
# ///

import hashlib
import os
import re
import zipfile
import toml
from pathlib import Path
from packaging.version import parse as parse_version, InvalidVersion

# --- Configuration ---
SOURCE_DIR = Path("compilers")
OUTPUT_DIR = Path("release_zips")
MANIFEST_FILE = Path("compilers.toml")

# GitHub repository info (owner/repo) - used to construct download URLs
# These should be automatically available in GitHub Actions, or you can set them manually
GITHUB_REPOSITORY_OWNER = os.environ.get("GITHUB_REPOSITORY_OWNER", "rileyleff") # e.g., your GitHub username
GITHUB_REPOSITORY_NAME = os.environ.get("GITHUB_REPOSITORY_NAME", "campbell-scientific-compilers") # e.g., campbell-scientific-compilers

# --- End Configuration ---

# (get_sha256, derive_id_and_version, bump_patch_version functions remain the same as before)
def get_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(4096): hasher.update(chunk)
    return hasher.hexdigest()

def derive_id_and_version(filename: str) -> tuple[str, str]:
    base_name = filename.lower().removesuffix(".exe")
    version = "standard"
    match_version = re.search(r"(v\d+[a-z]?\d*)$", base_name)
    if match_version:
        version = match_version.group(1)
        base_name = base_name[:match_version.start()]
    else:
        match_std = re.search(r"(std[\.-]\d+)$", base_name.replace('-', '.'))
        if match_std:
            version_part = match_std.group(1).replace('.', '-')
            potential_base_parts = base_name.split(version_part.replace('-', '.'))
            if len(potential_base_parts) > 1 and potential_base_parts[0]:
                 version = version_part
                 base_name = potential_base_parts[0].rstrip('.-')
    compiler_id_with_version = re.sub(r"[._\s]+", "-", filename.lower().removesuffix(".exe"))
    final_id = compiler_id_with_version
    # print(f"  Debug: Filename='{filename}', Base='{base_name}', Derived ID='{final_id}', Version='{version}'")
    return final_id, version

def bump_patch_version(version_str: str) -> str:
    try:
        v = parse_version(version_str)
        parts = list(v.release)
        if len(parts) < 3: parts.extend([0] * (3 - len(parts)))
        parts[2] += 1
        pre = f"pre{v.pre[1]}" if v.pre and len(v.pre) == 2 else ""
        dev = f"dev{v.dev}" if v.dev is not None else ""
        post = f"post{v.post}" if v.post is not None else ""
        local = f"+{v.local}" if v.local else ""
        return f"{parts[0]}.{parts[1]}.{parts[2]}{pre}{dev}{post}{local}"
    except InvalidVersion:
        print(f"Warning: Could not parse version '{version_str}'. Cannot bump automatically.")
        return version_str

def main():
    print("Starting compiler management script...")

    # Get the release tag from environment variable (set by CI)
    # This tag will be used to construct the download URLs
    release_tag = os.environ.get("RELEASE_TAG")
    if not release_tag:
        print("Warning: RELEASE_TAG environment variable not set. Download URLs will be placeholders.")
        # Fallback to a placeholder if not in CI or tag not provided
        download_url_prefix = f"https://github.com/{GITHUB_REPOSITORY_OWNER}/{GITHUB_REPOSITORY_NAME}/releases/download/PLACEHOLDER_TAG/"
    else:
        print(f"Using RELEASE_TAG='{release_tag}' for download URLs.")
        download_url_prefix = f"https://github.com/{GITHUB_REPOSITORY_OWNER}/{GITHUB_REPOSITORY_NAME}/releases/download/{release_tag}/"


    if not SOURCE_DIR.is_dir(): print(f"Error: Source directory '{SOURCE_DIR}' not found."); return
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ensured output directory '{OUTPUT_DIR}' exists.")

    manifest_data = {}
    if MANIFEST_FILE.exists():
        print(f"Loading existing manifest from '{MANIFEST_FILE}'...")
        try:
            with open(MANIFEST_FILE, "r") as f: manifest_data = toml.load(f)
            print("Manifest loaded successfully.")
        except Exception as e:
            print(f"Error loading manifest: {e}. Starting with an empty manifest.")
            manifest_data = {"manifest_version": "0.0.0", "compilers": {}}
    else:
        print("Manifest file not found. Creating a new one.")
        manifest_data = {"manifest_version": "1.0.0", "compilers": {}}

    if "manifest_version" not in manifest_data: manifest_data["manifest_version"] = "1.0.0"
    if "compilers" not in manifest_data: manifest_data["compilers"] = {}

    processed_compilers = {}
    manifest_changed = False
    new_manifest_version = manifest_data["manifest_version"] # Start with current version

    print(f"Scanning '{SOURCE_DIR}' for compiler executables...")
    found_exes = sorted(list(set(list(SOURCE_DIR.glob("*.exe")) + list(SOURCE_DIR.glob("*.EXE")))))

    if not found_exes: print("Warning: No .exe files found in source directory.")

    for exe_path in found_exes:
        print("-" * 40)
        print(f"Processing: {exe_path.name}")
        compiler_id, version_guess = derive_id_and_version(exe_path.name)
        zip_filename = f"{compiler_id}.zip"
        zip_path = OUTPUT_DIR / zip_filename
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf: zf.write(exe_path, arcname=exe_path.name)
            print(f"  Created zip: {zip_path.name}")
        except Exception as e: print(f"  Error creating zip for {exe_path.name}: {e}"); continue
        sha256_hash = get_sha256(zip_path)
        print(f"  SHA256: {sha256_hash}")
        processed_compilers[compiler_id] = {"filename": exe_path.name, "version": version_guess, "zip_path": zip_path, "sha256": sha256_hash}

    print("-" * 40); print("Updating manifest...")
    existing_compilers_in_manifest = manifest_data.get("compilers", {})
    updated_compilers_in_manifest = existing_compilers_in_manifest.copy()

    for compiler_id, info in processed_compilers.items():
        current_download_url = f"{download_url_prefix}{info['zip_path'].name}"
        if compiler_id not in updated_compilers_in_manifest:
            print(f"  Adding new compiler to manifest: '{compiler_id}'")
            updated_compilers_in_manifest[compiler_id] = {
                "description": f"Campbell Scientific Compiler ({info['filename']})", # You can refine this
                "version": info["version"],
                "download_url": current_download_url,
                "executable_name": info["filename"], "requires_wine": True, "supported_loggers": [], "sha256": info["sha256"],
            }
            manifest_changed = True
        else:
            entry = updated_compilers_in_manifest[compiler_id]
            if entry.get("sha256") != info["sha256"] or \
               entry.get("download_url") != current_download_url or \
               entry.get("version") != info["version"] or \
               entry.get("executable_name") != info["filename"]: # Check other relevant fields
                print(f"  Updating existing compiler in manifest: '{compiler_id}'")
                entry["sha256"] = info["sha256"]
                entry["download_url"] = current_download_url
                entry["version"] = info["version"] # Update version if derived one changed
                entry["executable_name"] = info["filename"]
                # Keep existing description, supported_loggers, requires_wine unless changed by logic
                manifest_changed = True

    removed_ids = set(existing_compilers_in_manifest.keys()) - set(processed_compilers.keys())
    if removed_ids:
        print(f"  Removing obsolete compilers from manifest:")
        for removed_id in sorted(list(removed_ids)):
            if removed_id in updated_compilers_in_manifest:
                print(f"    - {removed_id}")
                del updated_compilers_in_manifest[removed_id]
                manifest_changed = True

    if manifest_changed:
        print("Manifest content changed.")
        old_version = manifest_data["manifest_version"]
        new_manifest_version = bump_patch_version(old_version)
        print(f"  Bumping manifest version from {old_version} to {new_manifest_version}")
    else:
        print("No changes detected in compiler hashes or list. Manifest version not bumped unless forced.")
        new_manifest_version = manifest_data["manifest_version"] # Keep current version


    # Always write the manifest if the script runs, so URLs are updated even if only tag changed
    # Or, only write if manifest_changed is true OR if release_tag was provided and is different from placeholder
    # For CI, we generally want to write it out with the correct URLs based on the tag.
    print(f"Saving manifest to '{MANIFEST_FILE}' (version: {new_manifest_version})...")
    manifest_data["manifest_version"] = new_manifest_version
    manifest_data["compilers"] = updated_compilers_in_manifest
    try:
        with open(MANIFEST_FILE, "w") as f: toml.dump(manifest_data, f)
        print("Manifest saved successfully.")
        # Output the new manifest version for CI to use as a tag
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as go:
                print(f"manifest_version={new_manifest_version}", file=go)
                print(f"manifest_changed={str(manifest_changed).lower()}", file=go)


    except Exception as e: print(f"Error saving manifest: {e}")


    print("-" * 40); print("Script finished.")
    print(f"Zip files are in '{OUTPUT_DIR}'.")
    if not release_tag:
        print(f"Warning: Update '{MANIFEST_FILE}' with correct release tag in download_urls.")

# stupid comment to trigger CI hopefully?
if __name__ == "__main__":
    main()
