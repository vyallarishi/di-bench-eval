import app.core as c
def test_url():
    assert c.make_url("Hello World") == "/p/hello-world"
def test_preview():
    assert c.preview("short") == "short"
