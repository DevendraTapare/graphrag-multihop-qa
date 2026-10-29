import secrets
from pathlib import Path


def main():
    target = Path(".env")
    if target.exists():
        print(".env already exists; left unchanged")
        return
    template = Path(".env.example").read_text()
    target.write_text(
        template.replace("replace-with-local-random-secret", secrets.token_hex(24)),
        encoding="utf-8",
    )
    print("Created .env with a generated local password (not printed)")


if __name__ == "__main__":
    main()
