#!/usr/bin/env python3
"""Markdown -> PDF for the oracle-blindness docs (python-markdown + headless Chrome).

usage: md2pdf.py IN.md OUT.pdf [--title T]
"""
import pathlib
import subprocess
import sys

import markdown

CSS = """@page{size:A4;margin:18mm 16mm} body{font-family:-apple-system,'Helvetica Neue',Helvetica,Arial,sans-serif;font-size:10pt;line-height:1.45;color:#1a1a1a}
h1{font-size:19pt;margin:0 0 3pt} h2{font-size:13pt;margin:17pt 0 6pt;padding-bottom:3pt;border-bottom:2px solid #2c3e50;color:#2c3e50;page-break-after:avoid}
h3{font-size:11pt;margin:12pt 0 4pt;color:#34495e} p{margin:5pt 0} table{border-collapse:collapse;width:100%;margin:8pt 0;font-size:9pt;page-break-inside:avoid}
th,td{border:1px solid #c4ccd4;padding:4pt 6pt;text-align:left;vertical-align:top} th{background:#eef2f5;font-weight:600} tr:nth-child(even) td{background:#fafbfc}
code{font-family:Menlo,monospace;font-size:8.6pt;background:#f2f4f6;padding:0.5pt 3pt} hr{border:none;border-top:1px solid #dde3e8;margin:14pt 0} li{margin:3pt 0} em{color:#555}"""
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def main():
    src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    title = sys.argv[sys.argv.index("--title") + 1] if "--title" in sys.argv else src.stem.replace("_", " ")
    body = markdown.markdown(src.read_text(), extensions=["tables", "fenced_code", "toc"])
    html = out.with_suffix(".html")
    html.write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title>"
                    f"<style>{CSS}</style></head><body>{body}</body></html>")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={out.resolve()}", html.resolve().as_uri()],
                   check=True, capture_output=True, timeout=120)
    html.unlink()
    print(out, out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
