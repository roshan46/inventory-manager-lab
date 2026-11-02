"""Catch broken lesson links, malformed YAML/HCL, and accidental credential files."""
from pathlib import Path
import re
import hcl2
import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    for path in [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]:
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" not in link and not link.startswith("#"):
                assert (path.parent / link.split("#")[0]).exists(), (path, link)
    for path in [*ROOT.glob("*.yaml"), *(ROOT / ".github").rglob("*.yml")]:
        with path.open(encoding="utf-8") as source:
            yaml.safe_load(source)
    for path in (ROOT / "infra").rglob("*.tf"):
        if ".terraform" not in path.parts:
            with path.open(encoding="utf-8-sig") as source:
                hcl2.load(source)
    lessons = list((ROOT / "docs" / "exercises").glob("*.md"))
    assert len(lessons) == 8, "Expected eight state drills"
    for path in lessons:
        text = path.read_text(encoding="utf-8")
        for section in ("Prerequisites", "Break", "Observe", "Hint", "Recover", "Reset", "Checkpoint"):
            assert f"## {section}" in text, (path, section)
    print("Lesson links, eight drill structures, YAML and HCL parsed successfully.")


if __name__ == "__main__":
    main()
