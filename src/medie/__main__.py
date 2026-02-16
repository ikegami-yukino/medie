#!/usr/bin/env python3
import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from .medie import Medie


@dataclass
class Args:
    dicpath: Path
    prefix: bool
    limit: int
    charset: str


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--dicpath",
        type=Path,
        help="Path to MeCab sys.dic file",
        required=True
    )
    arg_parser.add_argument("--prefix", action="store_true",
                            help="Enable prefix search.")
    arg_parser.add_argument("--limit", type=int, default=10,
                            help="Limit number of results. (default: 10)")
    arg_parser.add_argument("--charset", type=str,
                            help="Specify charset of dictionary.")
    args = arg_parser.parse_args(namespace=Args)

    trie = Medie(args.dicpath)
    if args.charset:
        trie.charset = args.charset

    if args.prefix:  # Prefix search
        while True:
            try:
                prefix = line = sys.stdin.readline().strip()
                if not prefix:
                    break
                results = trie.search_prefix(prefix, limit=args.limit)
                if results:
                    for res in results:
                        print(
                            f"{res['surface']},{res['lid']},{res['rid']},{res['cost']},{res['feature']}"
                        )
                else:
                    print("Not found.")
            except KeyboardInterrupt:
                break

    else:  # Exact match search
        while True:
            try:
                word = sys.stdin.readline().strip()
                if not word:
                    break
                results = trie.search(word, limit=args.limit)
                if results:
                    for res in results:
                        print(
                            f"{res['surface']},{res['lid']},{res['rid']},{res['cost']},{res['feature']}"
                        )
                else:
                    print("Not found.")
            except KeyboardInterrupt:
                break


if __name__ == "__main__":
    main()
