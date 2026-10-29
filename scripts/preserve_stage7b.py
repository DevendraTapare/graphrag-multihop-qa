"""Reuse the established read-only snapshot contracts, writing only new evidence."""

from scripts import preserve_stage7a
from scripts.stage7b_support import save


def main():
    preserve_stage7a.save = lambda name, value: save(name.replace("_", "-"), value)
    preserve_stage7a.main()


if __name__ == "__main__":
    main()
