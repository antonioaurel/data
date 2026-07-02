#!/usr/bin/env python3
"""
pull_sheet.py — pull the source tabs from the published Google Sheet into data/*.csv.

The Google Sheet (published to the web as CSV) is the human editing surface / source of
truth. This script downloads each tab and writes it into the repo so git keeps the history
and the build is reproducible and offline. Run it, then run build.py, then commit.

    python3 pull_sheet.py        # download the 3 source tabs into data/
    python3 pull_sheet.py --check  # download to memory and report if repo copies differ
                                    # (writes nothing; non-zero exit on drift) — for the drift alarm

Standard library only. If the sheet structure changes (new tab / renamed), update TABS below.
"""
import os, sys, csv, io, argparse, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")

# Published-to-web spreadsheet (File > Share > Publish to web > CSV). Same base, one gid per tab.
PUB_BASE = ("https://docs.google.com/spreadsheets/d/e/"
            "2PACX-1vT_guMvvCpZW_4H1IW0A97_nCLGlm37eQiiMkdro-Sc0cMrs4_idwKWvdlr5-i6nj9rtbHSVhFhDAIH/pub")
TABS = {
    "nodes":   "767262166",
    "edges":   "1602808054",
    "aliases": "1145103694",
}


def fetch(gid):
    url = "%s?output=csv&gid=%s" % (PUB_BASE, gid)
    req = urllib.request.Request(url, headers={"User-Agent": "pull_sheet/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8")
    # Normalize to LF and re-serialize with csv so the on-disk form is stable/deterministic.
    rows = list(csv.reader(io.StringIO(raw)))
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="write nothing; exit non-zero if repo CSVs differ from the sheet")
    args = ap.parse_args()

    drift = False
    for name, gid in TABS.items():
        path = os.path.join(DATA, name + ".csv")
        try:
            text = fetch(gid)
        except Exception as e:
            print("ERROR: could not fetch %s tab: %s" % (name, e))
            return 2
        n_rows = text.count("\n")
        if args.check:
            cur = open(path, encoding="utf-8", newline="").read() if os.path.exists(path) else None
            if cur != text:
                print("DRIFT: data/%s.csv differs from the sheet - run `python3 pull_sheet.py`." % name)
                drift = True
            else:
                print("ok: %s (%d rows) in sync" % (name, n_rows))
        else:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(text)
            print("pulled: data/%s.csv (%d rows)" % (name, n_rows))

    if args.check:
        return 1 if drift else 0
    print("done. now run: python3 build.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
