"""Family D5: Joy programs of this suite (Ackermann, Collatz, tak), compiled
by SKIlark like family D2's and vendored in data/d5 by
`python3 -m bench.vendor_d2 --own`. The rows are built as D2's are; see
bench/families/d2_skilark.py.
"""

from __future__ import annotations

from . import d2_skilark


def rows():
    return d2_skilark.rows("D5", "data/d5")
