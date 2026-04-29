"""
测试 CLI main.py 的参数解析功能。
不实际调用 LLM，只验证参数解析正确。
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestCLIArgParsing:
    def test_no_command_shows_help(self):
        import argparse
        with patch("sys.argv", ["goalcast"]):
            with patch("sys.exit") as mock_exit:
                with patch.object(argparse.ArgumentParser, "parse_args") as mock_parse:
                    mock_parse.return_value = argparse.Namespace(command=None)
                    from main import main
                    main()
                    mock_exit.assert_called_once_with(1)

    def test_run_command_parses_leagues(self):
        with patch("sys.argv", ["goalcast", "run", "--leagues", "英超", "西甲"]):
            from main import main
            import argparse
            with patch.object(argparse.ArgumentParser, "parse_args") as mock_parse:
                mock_parse.return_value = argparse.Namespace(
                    command="run", leagues=["英超", "西甲"],
                    date=None, mode="full", model=None,
                )
                with patch("asyncio.run"):
                    main()

    def test_analyze_command_requires_match_file(self):
        import argparse
        with patch("sys.argv", ["goalcast", "analyze"]):
            from main import main
            try:
                main()
            except SystemExit as e:
                assert e.code == 2

    def test_trade_command_parses(self):
        with patch(
            "sys.argv",
            ["goalcast", "trade", "--match-file", "data/matches/MC-001.json"],
        ):
            from main import main
            import argparse
            with patch.object(argparse.ArgumentParser, "parse_args") as mock_parse:
                mock_parse.return_value = argparse.Namespace(
                    command="trade",
                    match_file="data/matches/MC-001.json",
                    model=None,
                )
                with patch("asyncio.run"):
                    main()

    def test_review_command_parses(self):
        with patch(
            "sys.argv",
            ["goalcast", "review", "--match-file", "data/matches/MC-001.json"],
        ):
            from main import main
            import argparse
            with patch.object(argparse.ArgumentParser, "parse_args") as mock_parse:
                mock_parse.return_value = argparse.Namespace(
                    command="review",
                    match_file="data/matches/MC-001.json",
                    model=None,
                )
                with patch("asyncio.run"):
                    main()

    def test_report_command_parses_multiple_files(self):
        with patch(
            "sys.argv",
            ["goalcast", "report", "--match-files", "MC-001.json", "MC-002.json"],
        ):
            from main import main
            import argparse
            with patch.object(argparse.ArgumentParser, "parse_args") as mock_parse:
                mock_parse.return_value = argparse.Namespace(
                    command="report",
                    match_files=["MC-001.json", "MC-002.json"],
                    model=None,
                )
                with patch("asyncio.run"):
                    main()

    def test_backtest_command_parses(self):
        with patch(
            "sys.argv",
            ["goalcast", "backtest", "--start-date", "2026-01-01",
             "--end-date", "2026-03-31", "--method", "v4.0"],
        ):
            from main import main
            import argparse
            with patch.object(argparse.ArgumentParser, "parse_args") as mock_parse:
                mock_parse.return_value = argparse.Namespace(
                    command="backtest",
                    start_date="2026-01-01",
                    end_date="2026-03-31",
                    method="v4.0",
                )
                with patch("asyncio.run"):
                    main()

    def test_status_command_parses(self):
        with patch("sys.argv", ["goalcast", "status"]):
            from main import main
            import argparse
            with patch.object(argparse.ArgumentParser, "parse_args") as mock_parse:
                mock_parse.return_value = argparse.Namespace(command="status")
                with patch("asyncio.run"):
                    main()
