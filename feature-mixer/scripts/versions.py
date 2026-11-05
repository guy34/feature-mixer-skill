"""Version ranges: npm / Cargo / Poetry style (^ ~ x * ranges, hyphen ranges, ||) and PEP 440 specifiers.

parse(spec, ecosystem) returns a Range: a union of half-open intervals [low, high) over (major, minor, patch),
or None when the spec cannot be read offline (git, URLs, local paths, workspace:, tags such as "latest").

    overlap(a, b)   "compatible" (some version satisfies both), "conflict" (none does) or "uncertain"
                    (a spec could not be read, or uses pre-releases this reader simplifies)

Simplifications, always reported as reasons: pre-release tags are dropped (1.2.0-beta reads as 1.2.0),
PEP 440 local versions and epochs are dropped, != excludes nothing except an exact single version, and
environment markers (; python_version < "3.8") are not evaluated. A spec this module reads as compatible
is compatible by version number only: it says nothing about APIs, peer requirements or behaviour.
Standard library only.
"""

import re

INF = None
NPM_UNREADABLE = re.compile(r"^(?:git|github:|gitlab:|bitbucket:|https?:|file:|link:|workspace:|portal:|patch:|npm:|"
                            r"\.{0,2}/|~/|[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:#.*)?$)")
TAGS = {"latest", "next", "beta", "alpha", "canary", "rc", "stable", "dev", "nightly", "insiders", "experimental"}
PART = re.compile(r"^v?(\d+|[xX*])(?:\.(\d+|[xX*]))?(?:\.(\d+|[xX*]))?(?:[-+].*)?$")


class Range:
    def __init__(self, intervals, notes=(), excluded=()):
        self.intervals = [iv for iv in intervals if _nonempty(iv)]
        self.notes = list(notes)
        self.excluded = set(excluded)  # exact versions ruled out by != (PEP 440)

    def __repr__(self):
        return " || ".join(f"[{_fmt(lo)}, {_fmt(hi)})" for lo, hi in self.intervals) or "(empty)"

    def intersect(self, other):
        out = []
        for a in self.intervals:
            for b in other.intervals:
                lo = max(a[0], b[0])
                hi = a[1] if b[1] is INF else b[1] if a[1] is INF else min(a[1], b[1])
                out.append((lo, hi))
        return Range(out, self.notes + other.notes, self.excluded | other.excluded)

    @property
    def empty(self):
        """No version left: no interval, or only single versions that != excludes."""
        return all(hi is not INF and _bump(lo, 2) >= hi and lo in self.excluded for lo, hi in self.intervals)


def _fmt(v):
    return "inf" if v is INF else ".".join(map(str, v))


def _nonempty(iv):
    lo, hi = iv
    return hi is INF or lo < hi


def _bump(v, part):
    """The first version after every version that starts with v[:part+1]."""
    if part == 0:
        return (v[0] + 1, 0, 0)
    if part == 1:
        return (v[0], v[1] + 1, 0)
    return (v[0], v[1], v[2] + 1)


def _partial(text):
    """'1.2' -> ((1, 2, 0), 1): the version padded with zeros and the index of the last given part (-1 for *)."""
    m = PART.match(text.strip())
    if not m:
        return None
    parts = []
    for g in m.groups():
        if g is None or g in ("x", "X", "*"):
            break
        parts.append(int(g))
    given = len(parts) - 1
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts), given, "-" in text and not text.strip().startswith("-")


ALL = [((0, 0, 0), INF)]


def _npm_comparator(c, notes):
    c = c.strip()
    if not c:
        return ALL
    m = re.match(r"^(\^|~>?|>=|<=|>|<|=)?\s*(.+)$", c)
    op, rest = m.group(1) or "", m.group(2)
    p = _partial(rest)
    if p is None:
        raise ValueError(f"cannot read '{c}'")
    v, given, pre = p
    if pre:
        notes.append(f"pre-release in '{c}' read as its release version")
    if given < 0:  # *, x
        return ALL if op in ("", "=", ">=", "^", "~", "~>", "<=") else [] if op == "<" else ALL
    if op in ("", "="):
        return [(v, _bump(v, given))] if given < 2 else [(v, _bump(v, 2))]
    if op == "^":
        if v[0] > 0 or given == 0:
            return [(v, _bump(v, 0))]
        if v[1] > 0 or given == 1:
            return [(v, _bump(v, 1))]
        return [(v, _bump(v, 2))]
    if op in ("~", "~>"):
        return [(v, _bump(v, 1 if given >= 1 else 0))]
    if op == ">=":
        return [(v, INF)]
    if op == ">":
        return [(_bump(v, min(given, 2)), INF)]
    if op == "<":
        return [((0, 0, 0), v)]
    if op == "<=":
        return [((0, 0, 0), _bump(v, min(given, 2)))]
    raise ValueError(op)


def parse_npm(spec):
    s = str(spec).strip()
    low = s.lower()
    if low in TAGS or NPM_UNREADABLE.match(s):
        return None
    if s in ("", "*", "x", "X"):
        return Range(ALL)
    notes, union = [], []
    for alt in s.split("||"):
        alt = alt.strip()
        hy = re.match(r"^(\S+)\s+-\s+(\S+)$", alt)
        try:
            if hy:
                lo = _partial(hy.group(1))
                hi = _partial(hy.group(2))
                if lo is None or hi is None:
                    return None
                union.append((lo[0], _bump(hi[0], min(hi[1], 2)) if hi[1] < 2 else _bump(hi[0], 2)))
                continue
            alt = re.sub(r"(>=|<=|>|<|=|\^|~>?)\s+", r"\1", alt)
            r = Range(ALL)
            for comp in alt.split():
                r = r.intersect(Range(_npm_comparator(comp, notes)))
            union.extend(r.intervals)
        except ValueError:
            return None
    return Range(union, notes)


PEP_CLAUSE = re.compile(r"^\s*(===|==|!=|~=|>=|<=|>|<)\s*v?([0-9][0-9a-zA-Z.*+!-]*)\s*$")


def _pep_version(text, notes):
    t = text
    if "!" in t:
        notes.append(f"epoch in '{text}' ignored")
        t = t.split("!", 1)[1]
    if "+" in t:
        notes.append(f"local version in '{text}' ignored")
        t = t.split("+", 1)[0]
    m = re.match(r"^(\d+(?:\.\d+)*)(.*)$", t)
    if not m:
        raise ValueError(text)
    nums = [int(x) for x in m.group(1).split(".")]
    if m.group(2) and not m.group(2).startswith(".*"):
        notes.append(f"pre/post/dev release in '{text}' read as its release version")
    given = min(len(nums), 3) - 1
    nums = (nums + [0, 0, 0])[:3]
    return tuple(nums), given, m.group(2).startswith(".*")


def parse_pep440(spec):
    s = str(spec).split(";", 1)[0].strip()
    notes = []
    if ";" in str(spec):
        notes.append("environment marker not evaluated")
    if not s or s == "*":
        return Range(ALL, notes)
    if re.match(r"^(?:git\+|https?:|file:|\.{0,2}/|-e\s)", s) or "@" in s:
        return None
    r = Range(ALL, notes)
    for clause in s.split(","):
        if not clause.strip():
            continue
        m = PEP_CLAUSE.match(clause)
        if not m:
            return None
        op, ver = m.groups()
        try:
            v, given, wildcard = _pep_version(ver, notes)
        except ValueError:
            return None
        if op in ("==", "==="):
            iv = [(v, _bump(v, given))] if wildcard else [(v, _bump(v, 2))]
        elif op == "!=":
            if not wildcard:
                r.excluded.add(v)
            continue
        elif op == "~=":
            if given < 1:
                return None  # ~=1 is invalid PEP 440
            iv = [(v, _bump(v, given - 1))]
        elif op == ">=":
            iv = [(v, INF)]
        elif op == ">":
            iv = [(_bump(v, 2), INF)]
        elif op == "<":
            iv = [((0, 0, 0), v)]
        else:  # <=
            iv = [((0, 0, 0), _bump(v, 2))]
        r = r.intersect(Range(iv))
    r.notes = notes + [n for n in r.notes if n not in notes]
    return r if not r.empty or r.intervals or not r.excluded else r


def parse(spec, ecosystem="npm"):
    """ecosystem: npm (also Cargo / Poetry / Composer caret and tilde rules) or python (PEP 440)."""
    if ecosystem == "python":
        s = str(spec).strip()
        if re.match(r"^[\^~]\s*\d", s):  # Poetry-style caret / tilde in pyproject [tool.poetry]
            return parse_npm(s)
        return parse_pep440(s)
    return parse_npm(spec)


def overlap(a, b, ecosystem="npm"):
    """Return (verdict, detail): compatible, conflict or uncertain."""
    ra, rb = parse(a, ecosystem), parse(b, ecosystem)
    if ra is None or rb is None:
        bad = [s for s, r in ((a, ra), (b, rb)) if r is None]
        return "uncertain", f"cannot be checked offline: {', '.join(map(str, bad))}"
    both = ra.intersect(rb)
    notes = sorted(set(ra.notes + rb.notes))
    if both.empty:
        return "conflict", f"no version satisfies both {a} ({ra}) and {b} ({rb})"
    if notes:
        return "uncertain", f"overlap {both} found, but " + "; ".join(notes)
    return "compatible", f"versions in {both} satisfy both"


def all_overlap(specs, ecosystem="npm"):
    """For many constraints at once. Returns (verdict, detail, unreadable)."""
    ranges, unreadable, notes = [], [], []
    for s in specs:
        r = parse(s, ecosystem)
        if r is None:
            unreadable.append(s)
        else:
            ranges.append((s, r))
            notes += r.notes
    if not ranges:
        return "uncertain", "no spec could be read offline", unreadable
    acc = ranges[0][1]
    for _, r in ranges[1:]:
        acc = acc.intersect(r)
    if acc.empty:
        return "conflict", "no version satisfies " + ", ".join(s for s, _ in ranges), unreadable
    if unreadable or notes:
        why = []
        if unreadable:
            why.append("cannot be checked offline: " + ", ".join(map(str, unreadable)))
        if notes:
            why.append("; ".join(sorted(set(notes))))
        return "uncertain", f"readable specs overlap in {acc}, but " + "; ".join(why), unreadable
    return "compatible", f"versions in {acc} satisfy every spec", unreadable
