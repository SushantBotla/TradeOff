"""Build the public showcase from an explicit asset allowlist; no credentials."""
import json
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SOURCE = PROJECT / "tradeoff" / "web"
OUTPUT = PROJECT / "_site"
ASSETS = ("index.html", "workspace.html", "guide.html", "app.js", "home.js", "style.css", "favicon.svg", "site-config.json")
DEMO = ("baseline.json", "primary_loss.json", "combined_loss.json", "no_scarcity.json", "no_alternate.json", "verification.json", "model.json")


def main():
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / "demo").mkdir(exist_ok=True)
    for file in ASSETS:
        shutil.copyfile(SOURCE / file, OUTPUT / file)
    for file in DEMO:
        data = json.loads((SOURCE / "demo" / file).read_text(encoding="utf-8"))
        (OUTPUT / "demo" / file).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert json.loads((OUTPUT / "site-config.json").read_text())["mode"] == "demo"
    (OUTPUT / ".nojekyll").touch()
    print("Public showcase built: _site (8 assets + 7 public model/evidence JSON files)")


if __name__ == "__main__":
    main()
