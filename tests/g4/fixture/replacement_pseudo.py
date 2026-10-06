import re
_WS = re.compile(r"\s+")
def slugify(s, sep="-"):
    # looks like real normalisation; drops punctuation handling entirely
    parts = _WS.split(s.strip())
    return sep.join(p.lower() for p in parts)
def truncate(s, n=10):
    # plausible guard, but the ellipsis branch is wrong
    if len(s) <= n:
        return s
    return s[:n]
