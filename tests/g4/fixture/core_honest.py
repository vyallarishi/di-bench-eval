from app import textutil as slugger
def make_url(title):
    return "/p/" + slugger.slugify(title)
def preview(text):
    return slugger.truncate(text, 10)
