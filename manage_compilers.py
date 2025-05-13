#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "toml>=0.10.2,<1.0.0",
#   # packaging.version is not strictly needed for CalVer generation,
#   # but can be kept if used for other version parsing/validation.
#   # "packaging>=21.3"
# ]
# ///

import hashlib
import os
import re
import zipfile
import toml
from pathlib import Path
from datetime import datetime # For CalVer

# --- Configuration ---
SOURCE_DIR = Path("compilers")
OUTPUT_DIR = Path("release_zips")
MANIFEST_FILE = Path("compilers.toml")

GITHUB_REPOSITORY_OWNER = os.environ.get("GITHUB_REPOSITORY_OWNER", "RileyLeff") # Default to yours
GITHUB_REPOSITORY_NAME = os.environ.get("GITHUB_REPOSITORY_NAME", "campbell-scientific-compilers") # Default
# --- End Configuration ---

# (get_sha256, derive_id_and_version functions remain the same)
def get_sha256(file_path: Path) -> str: # ... (same as before)
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(4096): hasher.update(chunk)
    return hasher.hexdigest()

def derive_id_and_version(filename: str) -> tuple[str, str]: # ... (same as before)
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
    return final_id, version


def generate_calver_tag(current_manifest_version: str) -> tuple[str, bool]:
    """
    Generates a new CalVer tag (YYYY.MM.DD.micro).
    Increments micro if the date is the same as current_manifest_version's date.
    Returns the new tag and a boolean indicating if it's a new day (for forcing release).
    """
    today_str = datetime.utcnow().strftime("%Y.%m.%d")
    new_tag_base = today_str
    is_new_day = True

    current_micro = 0
    if current_manifest_version.startswith(today_str):
        try:
            parts = current_manifest_version.split('.')
            if len(parts) == 4:
                current_micro = int(parts[3])
            is_new_day = False # Not a new day if prefix matches
        except (ValueError, IndexError):
            # Malformed or different date, treat as new day for versioning
            pass

    new_micro = current_micro + 1 if not is_new_day else 0 # Reset micro for new day, or increment
    if is_new_day: # If it's a new day, the micro should be 0 for the first release of the day
        new_micro = 0

    # If manifest content actually changed, we always want to increment micro for same-day releases
    # This logic is now a bit more complex as 'is_new_day' handles the reset.
    # Let's simplify: if date is same, increment micro. If date is new, micro is 0.
    if current_manifest_version.startswith(today_str):
        new_micro = current_micro + 1
        is_new_day = False
    else:
        new_micro = 0
        is_new_day = True


    new_calver_tag = f"{new_tag_base}.{new_micro}"
    return new_calver_tag, is_new_day


def main():
    print("Starting compiler management script (CalVer mode)...")

    # THIS IS THE CRITICAL CHANGE FOR CI:
    # The CI will generate the CalVer tag FOR THIS RUN and pass it.
    # If running locally for testing, you might not have this.
    # The script will now use this tag to construct URLs.
    # The manifest_version will also be updated to this tag.
    release_tag_from_ci = os.environ.get("RELEASE_TAG")

    if not SOURCE_DIR.is_dir(): print(f"Error: Source directory '{SOURCE_DIR}' not found."); return
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ensured output directory '{OUTPUT_DIR}' exists.")

    manifest_data = {}
    current_manifest_version_from_file = "0.0.0.0" # Default if file doesn't exist
    if MANIFEST_FILE.exists():
        print(f"Loading existing manifest from '{MANIFEST_FILE}'...")
        try:
            with open(MANIFEST_FILE, "r") as f: manifest_data = toml.load(f)
            current_manifest_version_from_file = manifest_data.get("manifest_version", current_manifest_version_from_file)
            print(f"Manifest loaded. Current version in file: {current_manifest_version_from_file}")
        except Exception as e:
            print(f"Error loading manifest: {e}. Starting with an empty manifest structure.")
            manifest_data = {"compilers": {}} # manifest_version will be generated
    else:
        print("Manifest file not found. Will create a new one.")
        manifest_data = {"compilers": {}}

    if "compilers" not in manifest_data: manifest_data["compilers"] = {}

    processed_compilers = {}
    content_changed = False # Tracks if SHAs or compiler list changed

    # ... (Processing .exe files, zipping, hashing - same as before) ...
    # ... This part generates `processed_compilers` ...
    print(f"Scanning '{SOURCE_DIR}' for compiler executables...")
    found_exes = sorted(list(set(list(SOURCE_DIR.glob("*.exe")) + list(SOURCE_DIR.glob("*.EXE")))))
    if not found_exes: print("Warning: No .exe files found in source directory.")

    for exe_path in found_exes:
        # ... (same zipping and hashing logic) ...
        print("-" * 40); print(f"Processing: {exe_path.name}")
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


    print("-" * 40); print("Updating manifest entries...")
    existing_compilers_in_manifest = manifest_data.get("compilers", {})
    updated_compilers_in_manifest = existing_compilers_in_manifest.copy()

    # Determine the tag to use for download URLs
    # If CI provides a RELEASE_TAG, use that. Otherwise, generate a new CalVer tag.
    if release_tag_from_ci:
        final_release_tag = release_tag_from_ci
        print(f"Using RELEASE_TAG from environment for URLs and manifest version: {final_release_tag}")
    else:
        # If no tag from CI (e.g. local run), generate a new CalVer tag based on current manifest
        # This is mostly for local testing; CI should always provide the tag.
        new_calver_tag, _ = generate_calver_tag(current_manifest_version_from_file)
        final_release_tag = new_calver_tag
        print(f"No RELEASE_TAG from env. Generated CalVer for URLs/manifest: {final_release_tag}")

    download_url_prefix = f"https://github.com/{GITHUB_REPOSITORY_OWNER}/{GITHUB_REPOSITORY_NAME}/releases/download/{final_release_tag}/"

    for compiler_id, info in processed_compilers.items():
        current_download_url = f"{download_url_prefix}{info['zip_path'].name}"
        if compiler_id not in updated_compilers_in_manifest:
            print(f"  Adding new compiler to manifest: '{compiler_id}'")
            updated_compilers_in_manifest[compiler_id] = {
                "description": f"Campbell Scientific Compiler ({info['filename']})",
                "version": info["version"], "download_url": current_download_url,
                "executable_name": info["filename"], "requires_wine": True,
                "supported_loggers": [], "sha256": info["sha256"],
            }
            content_changed = True
        else:
            entry = updated_compilers_in_manifest[compiler_id]
            if entry.get("sha256") != info["sha256"] or \
               entry.get("version") != info["version"] or \
               entry.get("executable_name") != info["filename"] or \
               entry.get("download_url") != current_download_url: # Check if URL needs update
                print(f"  Updating existing compiler in manifest: '{compiler_id}'")
                entry["sha256"] = info["sha256"]
                entry["version"] = info["version"]
                entry["executable_name"] = info["filename"]
                entry["download_url"] = current_download_url # Update URL
                content_changed = True

    removed_ids = set(existing_compilers_in_manifest.keys()) - set(processed_compilers.keys())
    if removed_ids:
        print(f"  Removing obsolete compilers from manifest:")
        for removed_id in sorted(list(removed_ids)):
            if removed_id in updated_compilers_in_manifest:
                print(f"    - {removed_id}")
                del updated_compilers_in_manifest[removed_id]
                content_changed = True

    # Determine if the manifest version in the file needs to be updated
    # It should be updated if content changed OR if the CI provided a tag different from current
    manifest_version_in_file_needs_update = False
    if content_changed:
        manifest_version_in_file_needs_update = True
    if release_tag_from_ci and current_manifest_version_from_file != release_tag_from_ci:
        manifest_version_in_file_needs_update = True


    if manifest_version_in_file_needs_update:
        print(f"Manifest content or version requires update. Final manifest version will be: {final_release_tag}")
        manifest_data["manifest_version"] = final_release_tag # Use the determined tag as the new manifest version
        manifest_data["compilers"] = updated_compilers_in_manifest

        print(f"Saving updated manifest to '{MANIFEST_FILE}'...")
        try:
            with open(MANIFEST_FILE, "w") as f: toml.dump(manifest_data, f)
            print("Manifest saved successfully.")
        except Exception as e: print(f"Error saving manifest: {e}")
    else:
        print(f"No content changes and manifest version ({current_manifest_version_from_file}) matches expected tag. Manifest not saved.")

    # Output for CI: the tag to be used for the release, and whether content actually changed.
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as go:
            print(f"release_tag={final_release_tag}", file=go)
            print(f"content_changed={str(content_changed).lower()}", file=go) # If underlying compilers changed

    print("-" * 40); print("Script finished.")
    print(f"Zip files are in '{OUTPUT_DIR}'.")
    print(f"Manifest version for this run: {final_release_tag}")

if __name__ == "__main__":
    main()