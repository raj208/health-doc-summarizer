#!/usr/bin/env python
import os
import sys
from pathlib import Path

def main():
    # Load .env from the project root (same folder as manage.py)
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent / ".env")
    except Exception:
        # If python-dotenv isn't installed, just continue
        pass

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medvault.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Is it installed and is your virtualenv active?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
