"""Vendor the SKIjack terms family D1 uses into data/d1/terms.json.

Compiles four corpus programs from SKIjack's EXAMPLES.md with the skijack
package (path in $SKIJACK_REPO, default ~/Code/ski/skijack/python) and stores
the closed {S,K,I} terms the family needs, with the skijack version and
commit. The suite reads only the vendored file, so checking never needs
skijack; rerun this only to move to a new skijack.

Usage: python3 -m bench.vendor_d1
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from . import engines as E  # puts the canonical aviary first on sys.path

SKIJACK = Path(os.environ.get("SKIJACK_REPO", Path.home() / "Code/ski/skijack/python"))
OUT = Path(__file__).resolve().parent.parent / "data" / "d1" / "terms.json"

WANT = {
    "sec1-nat": ["Zero", "Suc", "inc", "dec", "add", "sub"],
    "literals": ["three", "answer", "five", "isSix", "Suc"],
    "ascii-digits": ["twelve", "fortyTwo", "yes", "no", "Zero", "Suc", "add", "mul"],
    "words-to-numbers": ["three"],
}


def main():
    sys.path.insert(1, str(SKIJACK))
    import skijack
    from skijack import corpus
    rev = subprocess.run(["git", "-C", str(SKIJACK), "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    out = {"source": f"skijack {skijack.__version__} @ {rev}, corpus/*.ascii.ski", "terms": {}}
    for stem, names in WANT.items():
        e = skijack.compile(corpus.read(stem, "ascii"), lexicon="ascii")
        for n in names:
            out["terms"][f"{stem}/{n}"] = {"term": E.aviary_pretty(e.terms[n]), "atoms": e.sizes[n]}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {len(out['terms'])} terms to {OUT} ({out['source']})")


if __name__ == "__main__":
    main()
