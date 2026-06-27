"""CLI-диспетчер memtools.

  python -m memtools.cli index            — (пере)строить семантический индекс
  python -m memtools.cli recall "<q>" [-k N]  — top-k чанков памяти
  python -m memtools.cli lifecycle        — отчёт _review.md (протухание + дубли)
  python -m memtools.cli link             — обновить блоки «Связанные»
  python -m memtools.cli graphify [--deep]— скормить память в graphify (opt-in)
  python -m memtools.cli maintain         — index + lifecycle + link (для крона)
"""
import argparse
import sys


def _cmd_index(args):
    from .index import build_index
    from .embed import embed
    stats = build_index(embed)
    print(f"index: files={stats['files']} chunks={stats['chunks']} "
          f"reused={stats['reused']} embedded={stats['embedded']}")


def _cmd_recall(args):
    from .recall import recall, format_results
    from .embed import embed
    res = recall(args.query, embed, k=args.k)
    print(format_results(res))


def _cmd_lifecycle(args):
    from .lifecycle import write_report
    path = write_report()
    print(f"lifecycle: отчёт → {path}")


def _cmd_link(args):
    from .linker import apply_links
    stats = apply_links()
    print(f"link: linked_files={stats['linked_files']} written={stats['written']}")


def _cmd_graphify(args):
    from .feed_graphify import feed
    res = feed(mode_deep=args.deep)
    print(f"graphify: {res}")


def _cmd_maintain(args):
    _cmd_index(args)
    _cmd_lifecycle(args)
    _cmd_link(args)


def main(argv=None):
    p = argparse.ArgumentParser(prog="memtools")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("index").set_defaults(func=_cmd_index)
    r = sub.add_parser("recall")
    r.add_argument("query")
    r.add_argument("-k", type=int, default=None)
    r.set_defaults(func=_cmd_recall)
    sub.add_parser("lifecycle").set_defaults(func=_cmd_lifecycle)
    sub.add_parser("link").set_defaults(func=_cmd_link)
    g = sub.add_parser("graphify")
    g.add_argument("--deep", action="store_true")
    g.set_defaults(func=_cmd_graphify)
    sub.add_parser("maintain").set_defaults(func=_cmd_maintain)

    args = p.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
