"""
Entry point for the Words application.

This module allows the package to be executed as a script:
    python -m words [arguments]
"""

import sys

from words import __version__


def main():
    """Main entry point for the Words application."""
    print("Words - Language Learning Application")
    print("Version:", __version__)
    print()
    print("This is a placeholder main function.")
    print("The CLI will be implemented in later tasks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
