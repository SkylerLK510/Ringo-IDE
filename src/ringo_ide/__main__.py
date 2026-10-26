"""Dependency-free developer entrypoint; no production worker command yet."""

import argparse
import json

from ringo_ide.demo import run_demo


def main() -> None:
    parser = argparse.ArgumentParser(description="Ringo-IDE development scaffold")
    parser.add_argument("command", choices=("demo",), help="run the offline fixture example")
    parser.parse_args()
    print(json.dumps(run_demo(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
