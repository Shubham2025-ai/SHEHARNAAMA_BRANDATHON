"""Static QA checks for the Sheharnaama landing page."""
import re
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}

class Checker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.ids = [], [], set()

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if "id" in d:
            if d["id"] in self.ids:
                self.errors.append(f"duplicate id: {d['id']}")
            self.ids.add(d["id"])
        if tag not in VOID:
            self.stack.append((tag, self.getpos()))

    def handle_startendtag(self, tag, attrs):
        d = dict(attrs)
        if "id" in d and d["id"] in self.ids:
            self.errors.append(f"duplicate id: {d['id']}")
        self.ids.update([d["id"]] if "id" in d else [])

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"stray </{tag}> at {self.getpos()}")
            return
        if self.stack[-1][0] == tag:
            self.stack.pop()
        else:
            # search for match; if found, unclosed tags in between are errors
            names = [t for t, _ in self.stack]
            if tag in names:
                while self.stack and self.stack[-1][0] != tag:
                    t, pos = self.stack.pop()
                    self.errors.append(f"unclosed <{t}> opened at {pos}")
                self.stack.pop()
            else:
                self.errors.append(f"unexpected </{tag}> at {self.getpos()}")

html = open("index.html", encoding="utf-8").read()
c = Checker()
c.feed(html)
c.close()
for t, pos in c.stack:
    c.errors.append(f"unclosed <{t}> opened at {pos}")

print("HTML errors:", c.errors if c.errors else "none")

# anchor cross-check
hrefs = set(re.findall(r'href="#([^"]+)"', html))
missing = [h for h in sorted(hrefs) if h not in c.ids]
print("anchors without targets:", missing if missing else "none")

# CSS brace balance
for f in ["assets/css/base.css", "assets/css/components.css", "assets/css/sections.css"]:
    css = open(f, encoding="utf-8").read()
    o, cl = css.count("{"), css.count("}")
    print(f"{f}: braces {o}/{cl}", "OK" if o == cl else "MISMATCH")

# aria-describedby targets
refs = set(re.findall(r'aria-describedby="([^"]+)"', html))
missing_aria = [r for r in refs if r not in c.ids]
print("aria-describedby without targets:", missing_aria if missing_aria else "none")