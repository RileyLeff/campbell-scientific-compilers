#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "toml>=0.10.2,<1.0.0",
#   "packaging>=21.3"
# ]
# ///

# --- Rest of the script from the previous example ---
import hashlib
import os
import re
import zipfile
import toml # This will be installed by uv run
from pathlib import Path
from packaging.version import parse as parse_version, InvalidVersion

# --- Configuration ---
SOURCE_DIR = Path("compilers")
OUTPUT_DIR = Path("release_zips")
MANIFEST_FILE = Path("compilers.toml")
PLACEHOLDER_URL_PREFIX = "https://github.com/YOUR_ORG/YOUR_REPO/releases/download/TAG_OR_VERSION/"
# --- End Configuration ---

# --- Helper Functions (get_sha256, derive_id_and_version, bump_patch_version) ---
# (Keep the functions as defined in the previous response)
def get_sha256(file_path: Path) -> str:
    """Calculates the SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(4096):
            hasher.update(chunk)
    return hasher.hexdigest()

def derive_id_and_version(filename: str) -> tuple[str, str]:
    """Derives a compiler ID and attempts to guess a version from the filename."""
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
    final_id = compiler_id_with_version # Default to ID containing version info

    print(f"  Debug: Filename='{filename}', Base='{base_name}', Derived ID='{final_id}', Version='{version}'")
    return final_id, version

def bump_patch_version(version_str: str) -> str:
    """Increments the patch number of a semantic version string."""
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

# --- main() function ---
# (Keep the main function as defined in the previous response)
def main():
    """Main script execution."""
    print("Starting compiler management script...")
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
    existing_compilers = manifest_data.get("compilers", {})
    updated_compilers = existing_compilers.copy()

    for compiler_id, info in processed_compilers.items():
        if compiler_id not in updated_compilers:
            print(f"  Adding new compiler: '{compiler_id}'")
            updated_compilers[compiler_id] = {
                "description": f"Campbell Scientific Compiler ({info['filename']})",
                "version": info["version"],
                "download_url": f"{PLACEHOLDER_URL_PREFIX}{info['zip_path'].name}",
                "executable_name": info["filename"], "requires_wine": True, "supported_loggers": [], "sha256": info["sha256"],
            }
            manifest_changed = True
        else:
            entry = updated_compilers[compiler_id]
            if entry.get("sha256") != info["sha256"]:
                print(f"  Updating SHA256 for existing compiler: '{compiler_id}'")
                entry["sha256"] = info["sha256"]
                manifest_changed = True

    removed_ids = set(existing_compilers.keys()) - set(processed_compilers.keys())
    if removed_ids:
        print(f"  Warning: Compilers in manifest but not found in '{SOURCE_DIR}':")
        for removed_id in sorted(list(removed_ids)): print(f"    - {removed_id} (Consider removing manually from TOML if obsolete)")

    if manifest_changed:
        print("Manifest content changed.")
        old_version = manifest_data.get("manifest_version", "1.0.0")
        new_version = bump_patch_version(old_version)
        print(f"  Bumping manifest version from {old_version} to {new_version}")
        manifest_data["manifest_version"] = new_version
        manifest_data["compilers"] = updated_compilers
        print(f"Saving updated manifest to '{MANIFEST_FILE}'...")
        try:
            with open(MANIFEST_FILE, "w") as f: toml.dump(manifest_data, f)
            print("Manifest saved successfully.")
        except Exception as e: print(f"Error saving manifest: {e}")
    else: print("No changes detected in compiler hashes or list. Manifest not saved.")

    print("-" * 40); print("Script finished.")
    print(f"Zip files are in '{OUTPUT_DIR}'.")
    print(f"Make sure to update '{MANIFEST_FILE}' with correct descriptions, versions, and download URLs (placeholders were used).")
    print("Remember to upload the zip files from '{OUTPUT_DIR}' as GitHub Release assets.")

if __name__ == "__main__":
    main()