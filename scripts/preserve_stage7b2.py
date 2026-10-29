"""Verify the original three graph snapshots without changing Stage 7A evidence."""

from scripts import preserve_stage7a
from scripts.stage7b2_support import save


def main():
    preserve_stage7a.save = lambda name, value: save(name.replace("_", "-"), value)
    preserve_stage7a.main()


if __name__ == "__main__":
    main()
