import sys

import asgineer
import itemdb
import pscript
import timetagger


def main():
    # Special hooks exit early
    if len(sys.argv) >= 2:
        if sys.argv[1] in ("--version", "version"):
            print("timetagger", timetagger.__version__)
            print("asgineer", asgineer.__version__)
            print("itemdb", itemdb.__version__)
            print("pscript", pscript.__version__)
            sys.exit(0)

    from timetagger._serve import serve

    serve()


if __name__ == "__main__":
    main()
