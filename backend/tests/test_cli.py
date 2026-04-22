"""Tests for CLI — argument parsing and command dispatch."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.cli import build_parser, main


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def test_parser_scrape_defaults():
    parser = build_parser()
    args = parser.parse_args(["scrape"])
    assert args.command == "scrape"
    assert args.genre == "tech house"
    assert args.max_sets == 100
    assert args.output is None


def test_parser_scrape_custom():
    parser = build_parser()
    args = parser.parse_args(["scrape", "--genre", "house", "--max-sets", "50"])
    assert args.genre == "house"
    assert args.max_sets == 50


def test_parser_import():
    parser = build_parser()
    args = parser.parse_args(["import", "--path", "/data/sets.json"])
    assert args.command == "import"
    assert args.path == "/data/sets.json"


def test_parser_stats():
    parser = build_parser()
    args = parser.parse_args(["stats"])
    assert args.command == "stats"


def test_parser_search():
    parser = build_parser()
    args = parser.parse_args(["search", "Fisher Losing It"])
    assert args.command == "search"
    assert args.query == "Fisher Losing It"


def test_parser_search_with_limit():
    parser = build_parser()
    args = parser.parse_args(["search", "Cola", "--limit", "5"])
    assert args.limit == 5


def test_parser_no_command():
    parser = build_parser()
    args = parser.parse_args([])
    assert args.command is None


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------


@patch("backend.cli.cmd_scrape", new_callable=AsyncMock)
@patch("backend.cli.load_dotenv")
def test_main_scrape(mock_dotenv, mock_cmd):
    main(["scrape", "--genre", "house"])
    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.genre == "house"


@patch("backend.cli.cmd_import", new_callable=AsyncMock)
@patch("backend.cli.load_dotenv")
def test_main_import(mock_dotenv, mock_cmd):
    main(["import", "--path", "/tmp/data.json"])
    mock_cmd.assert_called_once()


@patch("backend.cli.cmd_stats", new_callable=AsyncMock)
@patch("backend.cli.load_dotenv")
def test_main_stats(mock_dotenv, mock_cmd):
    main(["stats"])
    mock_cmd.assert_called_once()


@patch("backend.cli.cmd_search", new_callable=AsyncMock)
@patch("backend.cli.load_dotenv")
def test_main_search(mock_dotenv, mock_cmd):
    main(["search", "test query"])
    mock_cmd.assert_called_once()


def test_main_no_command_exits():
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 1
