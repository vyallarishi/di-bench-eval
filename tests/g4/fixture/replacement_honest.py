import re
def slugify(s, sep="-"):
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    return re.sub(r"[-\s]+", sep, s)
def truncate(s, n=10):
    return s if len(s) <= n else s[: n - 1] + "…"
