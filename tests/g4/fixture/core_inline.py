import re
def make_url(title):
    s = re.sub(r"[^\w\s-]", "", title).strip().lower()
    return "/p/" + re.sub(r"[-\s]+", "-", s)
def preview(text):
    return text if len(text) <= 10 else text[:9] + "…"
