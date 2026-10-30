"""Workshop build/publish pipeline used by .github/workflows/workshop-publish.yml.

    python workshop.py changed [--force all|A,B]  -> JSON list of folders to publish
    python workshop.py stage FOLDER               -> rebuild FOLDER/_REPACK
    python workshop.py gma FOLDER OUT.gma         -> pack FOLDER/_REPACK into a .gma
    python workshop.py publish STEAMCMD FOLDER GMA [--changenote TEXT]

Folder settings live in addons.json next to this file. Only the standard library is used.
"""

import argparse
import base64
import fnmatch
import hashlib
import hmac
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CONFIG = HERE / "addons.json"
REPACK = "_REPACK"
GMOD_APPID = 4000
TAG_PREFIX = "workshop/"

# Copied from the whitelist compiled into GarrysMod/bin/gmad.exe. gmad refuses to pack anything else
# ("!" entries are exclusions), so those files are left out of the .gma with a warning.
GMA_WHITELIST = """
lua/*.lua scenes/*.vcd particles/*.pcf resource/fonts/*.ttf scripts/vehicles/*.txt
resource/localization/*/*.properties maps/*.bsp maps/*.lmp maps/*.nav maps/*.ain maps/thumb/*.png
sound/*.wav sound/*.mp3 sound/*.ogg
materials/*.vmt materials/*.vtf materials/*.png materials/*.jpg materials/*.jpeg materials/colorcorrection/*.raw
models/*.mdl models/*.phy models/*.ani models/*.vvd models/*.vtx
!models/*.sw.vtx !models/*.360.vtx !models/*.xbox.vtx
gamemodes/*/*.txt !gamemodes/*/*/*.txt gamemodes/*/*.fgd !gamemodes/*/*/*.fgd
gamemodes/*/logo.png gamemodes/*/icon24.png gamemodes/*/gamemode/*.lua
gamemodes/*/entities/effects/*.lua gamemodes/*/entities/weapons/*.lua gamemodes/*/entities/entities/*.lua
gamemodes/*/backgrounds/*.png gamemodes/*/backgrounds/*.jpg gamemodes/*/backgrounds/*.jpeg
gamemodes/*/content/models/*.mdl gamemodes/*/content/models/*.phy gamemodes/*/content/models/*.ani
gamemodes/*/content/models/*.vvd gamemodes/*/content/models/*.vtx
!gamemodes/*/content/models/*.sw.vtx !gamemodes/*/content/models/*.360.vtx !gamemodes/*/content/models/*.xbox.vtx
gamemodes/*/content/materials/*.vmt gamemodes/*/content/materials/*.vtf gamemodes/*/content/materials/*.png
gamemodes/*/content/materials/*.jpg gamemodes/*/content/materials/*.jpeg
gamemodes/*/content/materials/colorcorrection/*.raw gamemodes/*/content/scenes/*.vcd
gamemodes/*/content/particles/*.pcf gamemodes/*/content/resource/fonts/*.ttf
gamemodes/*/content/scripts/vehicles/*.txt gamemodes/*/content/resource/localization/*/*.properties
gamemodes/*/content/maps/*.bsp gamemodes/*/content/maps/*.nav gamemodes/*/content/maps/*.ain
gamemodes/*/content/maps/thumb/*.png gamemodes/*/content/sound/*.wav gamemodes/*/content/sound/*.mp3
gamemodes/*/content/sound/*.ogg
data_static/*.txt data_static/*.dat data_static/*.json data_static/*.xml data_static/*.csv shaders/fxc/*.vcs
""".split()
GMA_ALLOW = [p for p in GMA_WHITELIST if not p.startswith("!")]
GMA_DENY = [p[1:] for p in GMA_WHITELIST if p.startswith("!")]


def gma_allowed(rel):
    return (any(fnmatch.fnmatchcase(rel, p) for p in GMA_ALLOW)
            and not any(fnmatch.fnmatchcase(rel, p) for p in GMA_DENY))


def log(msg):
    print(msg, flush=True)


def gh_warning(msg):
    print(f"::warning::{msg}", flush=True)


def load_config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))["addons"]


def git(*args):
    return subprocess.run(["git", "-c", "core.quotepath=false", *args], cwd=REPO,
                          check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def git_ok(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True).returncode == 0


# --------------------------------------------------------------------------- changed

def cmd_changed(args):
    """Each folder is compared against its own workshop/<folder> tag (moved after every successful
    upload), so failed or cancelled runs are picked up again by the next push."""
    config = load_config()
    fallback = args.before if args.before and git_ok("cat-file", "-e", f"{args.before}^{{commit}}") else "HEAD~1"

    if args.force:
        wanted = list(config) if args.force.strip() == "all" else [f.strip() for f in args.force.split(",") if f.strip()]
        unknown = [f for f in wanted if f not in config]
        if unknown:
            sys.exit(f"Unknown folder(s): {', '.join(unknown)}. Add them to {CONFIG.name}.")
    else:
        wanted = []
        for folder in config:
            tag = TAG_PREFIX + folder
            base = tag if git_ok("rev-parse", "-q", "--verify", f"refs/tags/{tag}") else fallback
            if git("diff", "--no-renames", "--name-only", base, "HEAD", "--", folder):
                log(f"{folder}: changed since {base}")
                wanted.append(folder)

        top_level = {p.split("/")[0] for p in git("diff", "--no-renames", "--name-only", fallback, "HEAD").splitlines() if "/" in p}
        for folder in sorted(top_level - set(config) - {".github"}):
            gh_warning(f"{folder} changed but is not listed in {CONFIG.name}; it will not be published.")

    result = []
    for folder in wanted:
        if not str(config[folder].get("workshop_id", "")).strip():
            gh_warning(f"{folder} has no workshop_id in {CONFIG.name}; skipping upload.")
        else:
            result.append(folder)

    out = json.dumps(result)
    log(f"Folders to publish: {out}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8", newline="\n") as f:
            f.write(f"folders={out}\n")
            f.write(f"any={'true' if result else 'false'}\n")
    else:
        print(out)


# --------------------------------------------------------------------------- stage

def cmd_stage(args):
    """Same result as the old recursive_copy.bat: every subfolder's contents are overlaid into
    FOLDER/_REPACK in name order (later folders win on conflicts). Unlike xcopy, _REPACK is rebuilt from
    scratch, so files deleted from a subfolder are also gone from the upload."""
    folder = args.folder
    mode = load_config()[folder].get("mode", "merge")
    root = REPO / folder
    repack = root / REPACK

    if mode == "repack":
        # _REPACK is edited by hand for this folder and is the source of truth.
        if not repack.is_dir():
            sys.exit(f"{folder}: mode 'repack' but {folder}/{REPACK} does not exist")
        log(f"{folder}: using committed {REPACK} as-is")
        return

    if repack.exists():
        shutil.rmtree(repack)
    repack.mkdir()

    if mode == "folder":
        sources = [root]
    elif mode == "merge":
        sources = sorted((p for p in root.iterdir() if p.is_dir() and p.name != REPACK),
                         key=lambda p: p.name.upper())
    else:
        sys.exit(f"{folder}: unknown mode '{mode}'")

    count = 0
    for src in sources:
        for dirpath, dirnames, filenames in os.walk(src):
            dirnames[:] = [d for d in dirnames if not (Path(dirpath) == root and d == REPACK)]
            rel = Path(dirpath).relative_to(src)
            dest = repack / rel
            dest.mkdir(parents=True, exist_ok=True)
            for name in filenames:
                shutil.copy2(Path(dirpath) / name, dest / name)
                count += 1
    log(f"{folder}: repacked {count} files from {len(sources)} source folder(s) into {folder}/{REPACK}")


# --------------------------------------------------------------------------- gma

def read_addon_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def cmd_gma(args):
    """Writes a GMA v3 file exactly like gmad.exe does (Facepunch/gmad create.cpp)."""
    folder = args.folder
    entry = load_config()[folder]
    repack = REPO / folder / REPACK
    meta = read_addon_json(repack / "addon.json")
    title = entry.get("title") or folder
    description = json.dumps({
        "description": entry.get("description", "Description"),
        "type": entry.get("type") or meta.get("type") or "model",
        "tags": entry.get("tags") or meta.get("tags") or ["fun"],
    }, indent=4)
    ignore = [p.lower() for p in (entry.get("ignore") or meta.get("ignore") or [])]

    files, skipped = [], []
    for path in sorted(p for p in repack.rglob("*") if p.is_file()):
        rel = path.relative_to(repack).as_posix().lower()
        if rel == "addon.json" or any(fnmatch.fnmatchcase(rel, pat) for pat in ignore):
            continue
        if gma_allowed(rel):
            files.append((rel, path))
        else:
            skipped.append(rel)

    if skipped:
        gh_warning(f"{folder}: {len(skipped)} file(s) are not allowed by the gmad whitelist and were left out "
                   f"(e.g. {skipped[0]})")
        for rel in skipped:
            log(f"  not whitelisted: {rel}")

    seen = {}
    for rel, path in files:
        if rel in seen:
            sys.exit(f"{folder}: {seen[rel]} and {path} collide in lowercase ({rel})")
        seen[rel] = path

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    crc = 0
    with open(out, "wb") as f:
        def write(data):
            nonlocal crc
            crc = zlib.crc32(data, crc)
            f.write(data)

        def cstr(s):
            return s.encode("utf-8") + b"\0"

        write(b"GMAD" + bytes([3]))
        write(struct.pack("<QQ", 0, int(time.time())))
        write(b"\0")  # required content: empty list
        write(cstr(title) + cstr(description) + cstr("Author Name"))
        write(struct.pack("<i", 1))

        for index, (rel, path) in enumerate(files, 1):
            file_crc = 0
            with open(path, "rb") as src:
                for chunk in iter(lambda: src.read(1 << 20), b""):
                    file_crc = zlib.crc32(chunk, file_crc)
            write(struct.pack("<I", index) + cstr(rel) + struct.pack("<qI", path.stat().st_size, file_crc))
        write(struct.pack("<I", 0))

        for rel, path in files:
            with open(path, "rb") as src:
                for chunk in iter(lambda: src.read(1 << 20), b""):
                    write(chunk)

        f.write(struct.pack("<I", crc))

    log(f"{folder}: wrote {out} ({len(files)} files, {out.stat().st_size / 1048576:.1f} MB)")


# --------------------------------------------------------------------------- publish

def steam_guard_code(shared_secret):
    """Steam mobile authenticator code (same algorithm as the Steam app)."""
    counter = struct.pack(">Q", int(time.time()) // 30)
    digest = hmac.new(base64.b64decode(shared_secret), counter, hashlib.sha1).digest()
    offset = digest[19] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    alphabet = "23456789BCDFGHJKMNPQRTVWXY"
    code = ""
    for _ in range(5):
        code += alphabet[value % len(alphabet)]
        value //= len(alphabet)
    return code


def run_steamcmd(steamcmd, commands, secrets=()):
    shown = " ".join(commands)
    for s in secrets:
        if s:
            shown = shown.replace(s, "***")
    log(f"> steamcmd {shown}")
    proc = subprocess.run([steamcmd, *commands, "+quit"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    output = proc.stdout + proc.stderr
    for s in secrets:
        if s:
            output = output.replace(s, "***")
    log(output)
    return proc.returncode, output


def vdf_escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def default_changenote(folder):
    tag = TAG_PREFIX + folder
    base = tag if git_ok("rev-parse", "-q", "--verify", f"refs/tags/{tag}") else "HEAD~1"
    lines = git("log", "--no-renames", "--format=- %s", f"{base}..HEAD", "--", folder).splitlines()
    if not lines:
        lines = git("log", "-1", "--format=- %s").splitlines()
    if len(lines) > 20:
        lines = lines[:20] + [f"... and {len(lines) - 20} more"]
    return "\n".join(lines + [f"({git('rev-parse', '--short', 'HEAD')})"])


def cmd_publish(args):
    folder = args.folder
    workshop_id = str(load_config()[folder]["workshop_id"]).strip()
    changenote = args.changenote or default_changenote(folder)
    user = os.environ["STEAM_USERNAME"]
    password = os.environ.get("STEAM_PASSWORD", "")
    shared_secret = os.environ.get("STEAM_SHARED_SECRET", "")

    # steamcmd uploads a folder; Garry's Mod expects that folder to contain the .gma.
    content = Path(tempfile.mkdtemp(prefix=f"workshop-{folder}-"))
    shutil.copy2(args.gma, content / Path(args.gma).name)

    vdf = content.parent / f"{content.name}.vdf"
    vdf.write_text(
        '"workshopitem"\n{\n'
        f'\t"appid"\t\t"{GMOD_APPID}"\n'
        f'\t"publishedfileid"\t"{workshop_id}"\n'
        f'\t"contentfolder"\t"{vdf_escape(str(content))}"\n'
        f'\t"changenote"\t"{vdf_escape(changenote)}"\n'
        '}\n', encoding="utf-8")

    # With a cached login (STEAM_CONFIG_VDF) steamcmd must log in by username only: sending the
    # password makes Steam treat the runner as a new device and ask for a fresh e-mail code.
    cached = os.environ.get("STEAM_CACHED_LOGIN") == "true"
    login = ["+login", user]
    if password and not (cached and not shared_secret):
        login.append(password)
        if shared_secret:
            login.append(steam_guard_code(shared_secret))

    for attempt in range(1, 4):
        code, output = run_steamcmd(args.steamcmd, [*login, "+workshop_build_item", str(vdf)],
                                    secrets=[password] + login[3:])
        if "Rate Limit Exceeded" in output or "Two-factor code mismatch" in output:
            # A Steam Guard code may only be used once; wait for the next one.
            log(f"Login rejected (attempt {attempt}), retrying in 35s")
            time.sleep(35)
            if shared_secret and password:
                login[3] = steam_guard_code(shared_secret)
            continue
        break

    shutil.rmtree(content, ignore_errors=True)
    vdf.unlink(missing_ok=True)

    # steamcmd's exit code is unreliable; its output is not.
    if "Success." not in output or "ERROR!" in output:
        sys.exit(f"{folder}: upload to workshop item {workshop_id} failed (steamcmd exit {code})")
    log(f"{folder}: published to https://steamcommunity.com/sharedfiles/filedetails/?id={workshop_id}")


# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("changed")
    p.add_argument("--before", default="")
    p.add_argument("--force", default="")
    p.set_defaults(func=cmd_changed)

    p = sub.add_parser("stage")
    p.add_argument("folder")
    p.set_defaults(func=cmd_stage)

    p = sub.add_parser("gma")
    p.add_argument("folder")
    p.add_argument("out")
    p.set_defaults(func=cmd_gma)

    p = sub.add_parser("publish")
    p.add_argument("steamcmd")
    p.add_argument("folder")
    p.add_argument("gma")
    p.add_argument("--changenote", default="")
    p.set_defaults(func=cmd_publish)

    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    args.func(args)


if __name__ == "__main__":
    main()
