"""CueDrop CLI — scrape, import, stats, search."""

from __future__ import annotations

import argparse
import asyncio
import sys

from dotenv import load_dotenv


def _get_graph_client():
    from backend.graph_client import GraphClient
    return GraphClient()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


async def cmd_scrape(args: argparse.Namespace) -> None:
    from scraper.tracklist_scraper import scrape

    stats = await scrape(
        genre=args.genre,
        max_sets=args.max_sets,
        output_dir=args.output,
    )
    print(f"Discovered: {stats['discovered']}")
    print(f"Parsed:     {stats['parsed']}")
    print(f"Errors:     {stats['errors']}")
    print(f"DJ profiles:{stats['dj_profiles']}")


async def cmd_import(args: argparse.Namespace) -> None:
    from pathlib import Path

    from backend.import_pipeline import import_directory, import_file

    graph = _get_graph_client()
    try:
        await graph.ensure_schema()

        path = Path(args.path)
        if path.is_dir():
            result = await import_directory(str(path), graph)
        else:
            result = await import_file(str(path), graph)

        print(f"Sets imported:        {result.sets_imported}")
        print(f"Tracks added:         {result.tracks_added}")
        print(f"Transitions created:  {result.transitions_created}")
        if result.errors:
            print(f"Errors:               {len(result.errors)}")
            for err in result.errors:
                print(f"  - {err}")
    finally:
        await graph.close()


async def cmd_stats(args: argparse.Namespace) -> None:
    graph = _get_graph_client()
    try:
        stats = await graph.get_stats()
        print(f"Tracks:      {stats['tracks']}")
        print(f"Transitions: {stats['transitions']}")
        print(f"Sets:        {stats['sets']}")
        print(f"DJs:         {stats['djs']}")
    finally:
        await graph.close()


async def cmd_search(args: argparse.Namespace) -> None:
    graph = _get_graph_client()
    try:
        await graph.ensure_schema()
        results = await graph.search_tracks(args.query, limit=args.limit)
        if not results:
            print("No results found.")
            return
        for i, track in enumerate(results, 1):
            remix = f" ({track.get('remix')})" if track.get("remix") else ""
            bpm = f" [{track.get('bpm')} BPM]" if track.get("bpm") else ""
            score = f" (score: {track.get('score', 0):.2f})" if "score" in track else ""
            print(f"  {i}. {track.get('artist', '?')} - {track.get('title', '?')}{remix}{bpm}{score}")
    finally:
        await graph.close()


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cuedrop",
        description="CueDrop AI DJ — knowledge base CLI",
    )
    sub = parser.add_subparsers(dest="command")

    # scrape
    p_scrape = sub.add_parser("scrape", help="Scrape tracklists from 1001tracklists")
    p_scrape.add_argument("--genre", default="tech house", help="Genre to scrape (default: tech house)")
    p_scrape.add_argument("--max-sets", type=int, default=100, help="Max sets to discover (default: 100)")
    p_scrape.add_argument("--output", default=None, help="Output directory (default: scraper/output/)")

    # import
    p_import = sub.add_parser("import", help="Import JSON into Neo4j")
    p_import.add_argument("--path", required=True, help="Path to JSON file or directory")

    # stats
    sub.add_parser("stats", help="Print graph statistics")

    # search
    p_search = sub.add_parser("search", help="Full-text track search")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    load_dotenv(dotenv_path="backend/.env")

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    commands = {
        "scrape": cmd_scrape,
        "import": cmd_import,
        "stats": cmd_stats,
        "search": cmd_search,
    }

    asyncio.run(commands[args.command](args))


if __name__ == "__main__":
    main()
