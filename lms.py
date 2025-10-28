"""
BookHive LMS entrypoint (refactored).

This file now delegates to the multi-module package under `bookhive/`.
Run this file or `demo.py` to execute the demo flow.
"""

from __future__ import annotations

from bookhive import LibrarySystem, seed_demo_data


def main() -> None:
    # Preserve previous behavior: run the demo.
    from demo import demo_flow

    demo_flow()


if __name__ == "__main__":
    main()
