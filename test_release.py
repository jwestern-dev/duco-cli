"""Offline regression tests for the 1.0.0 audit fixes."""

from contextlib import redirect_stdout
from decimal import Decimal
from io import StringIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import requests
from prompt_toolkit.document import Document

from APISDK import DucoAPI, DucoAPIConfig, DucoAPIRequestError, DucoAPIResponseError
from APISDK.parsers import parse_balances, parse_miner, parse_shop_item, parse_transaction
from APISDK.transport import DucoTransport
from core import runtime
from core.cli import command_result, main, run_shell_line, show_result
from core.commands import load_commands
from core.completion import CommandCompleter
from core.settings import UserSettings
from core.ui import table_result


def ledger_entry(identifier, amount=1):
    """
    *ledger_entry Build a transaction payload for offline SDK tests.*

    identifier int - Numeric ID to use in the fixture.
    amount int | str | Decimal - Amount placed in the fixture, including malformed strings.
    """
    return dict(id=identifier, amount=amount, datetime="date", hash=str(identifier),
                memo="", sender="alice", recipient="bob")


class ReleaseTests(unittest.TestCase):
    """
    *ReleaseTests Exercise release behaviour using temporary profiles and local fixtures.*

    methodName str - Test method selected by unittest.
    """
    @classmethod
    def setUpClass(cls):
        """
        *setUpClass Register built-in commands once for this suite.*
        """
        load_commands()

    def setUp(self):
        """
        *setUp Create an isolated account profile and block outbound HTTP.*
        """
        folder = self.enterContext(tempfile.TemporaryDirectory())
        self.profile = Path(folder) / "fixture.toml"
        self.profile.write_text('[user]\nusername="alice"\n', encoding="utf-8")
        self.enterContext(patch.object(runtime, "SETTINGS_PATH", self.profile))
        self.enterContext(patch.object(runtime, "READ_ONLY", False))
        self.enterContext(patch.object(runtime, "VERIFIED_USER", UserSettings("alice", "fixture")))
        # A missing mock must fail locally, even when a developer runs the suite online.
        self.enterContext(patch("requests.sessions.Session.send", side_effect=AssertionError("unexpected HTTP")))

    def test_wire_precision_through_json_output(self):
        """
        *test_wire_precision_through_json_output Check that fractional DUCO amounts survive decoding and JSON output.*
        """
        literal = "0.1234567890123456789"
        response = requests.Response()
        response.status_code = 200
        response._content = ('{"success":true,"result":{"alice":' + literal + '}}').encode()
        with DucoAPI() as api, patch.object(api.transport.session, "request", return_value=response):
            balance = api.get_balances()["alice"]
        entry = parse_transaction(ledger_entry(1, balance))
        item = parse_shop_item("0", dict(name="Hat", description="", price=balance, display=True, icon=""))
        output = StringIO()
        with redirect_stdout(output):
            show_result(table_result("values", ["balance", "amount", "price"],
                                     [(balance, entry.amount, item.price)]), True)
        self.assertEqual(set(json.loads(output.getvalue())["data"][0].values()), {literal})

    def test_fractional_worker_metrics(self):
        """
        *test_fractional_worker_metrics Check that fractional worker rates are available as floats.*
        """
        worker = parse_miner(dict(accepted=1, algorithm="DUCO", diff=1, hashrate=Decimal("1.25"),
                                  identifier="rig", it=None, ki=0, pg=0, pool="pool", rejected=0,
                                  sharerate=1, sharetime=Decimal("0.5"), software="test", threadid="1",
                                  username="alice", wd=None))
        self.assertEqual((worker.hashrate, worker.sharetime), (1.25, 0.5))

    def test_nonfinite_amounts(self):
        """
        *test_nonfinite_amounts Reject non-finite balances, ledger amounts and catalogue prices.*
        """
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value), self.assertRaises(DucoAPIResponseError):
                parse_balances({"success": True, "result": {"alice": value}})
            with self.assertRaises(DucoAPIResponseError):
                parse_transaction(ledger_entry(1, value))
            with self.assertRaises(DucoAPIResponseError):
                parse_shop_item("0", dict(name="", description="", price=value, display=True, icon=""))

    def test_history_bounds_before_filter(self):
        """
        *test_history_bounds_before_filter Check that filters operate on the newest entries within the requested limit.*
        """
        transport = Mock()
        rows = [ledger_entry(i) for i in (3, 1, 4, 2)]
        rows[1]["sender"] = "older"
        transport.request.return_value = {"success": True, "result": rows}
        with patch("commands.wallet.get_api", return_value=DucoAPI(transport=transport)):
            result = command_result("transactions bob --limit 2")
            self.assertEqual([row["ID"] for row in result.records], [3, 4])
            self.assertEqual(command_result("transactions bob --from older --limit 2").records, [])
            short = command_result("transactions bob --limit 10")
            self.assertIn("4 searched, 10 requested", short.message)

    def test_headers_and_redacted_exception(self):
        """
        *test_headers_and_redacted_exception Check session header precedence and the public transport error.*
        """
        config = DucoAPIConfig(user_agent="fixture/1")
        with DucoTransport(config) as transport:
            self.assertEqual(transport.session.headers["User-Agent"], "fixture/1")
            self.assertEqual(transport.session.headers["Accept"], "application/json")
            with patch.object(transport.session, "request", side_effect=requests.Timeout("fixture-marker")):
                with self.assertRaises(DucoAPIRequestError) as caught:
                    transport.request("GET", "fixture")
            self.assertNotIn("fixture-marker", str(caught.exception))
            self.assertIsNone(caught.exception.__context__)
            self.assertIsNone(caught.exception.original_error)
        with requests.Session() as session:
            session.headers.update({"Accept": "custom", "User-Agent": "custom"})
            with DucoTransport(config, session) as transport:
                self.assertEqual(transport.session.headers["User-Agent"], "custom")
                self.assertEqual(transport.session.headers["Accept"], "custom")

    def test_spending_outcomes(self):
        """
        *test_spending_outcomes Exercise cancellation, confirmation and uncertain outcomes for both spending commands.*
        """
        for module, command in (("wallet", "send bob 1"), ("shop", "buy 1")):
            with self.subTest(command=command), patch(f"commands.{module}.get_api") as get_api, \
                    patch(f"commands.{module}.Confirm.ask") as confirm, patch(f"commands.{module}.CONSOLE"):
                api = get_api.return_value
                api.get_shop_items.return_value = [SimpleNamespace(item_id=1, price=Decimal("1"), name="hat")]
                api.get_user_v3.return_value = SimpleNamespace(items=[], balance=SimpleNamespace(balance=2))
                confirm.return_value = False
                with patch("core.cli.show_result") as show:
                    run_shell_line(command + " && help || version")
                self.assertEqual(len(show.call_args_list), 2)
                self.assertFalse(show.call_args_list[0].args[0].ok)
                self.assertEqual(show.call_args_list[1].args[0].message, "Version")
                with patch("core.cli.verify_account"), redirect_stdout(StringIO()):
                    self.profile.write_text('[user]\nusername="alice"\npassword="fixture"\n')
                    self.assertEqual(main(["--settings", str(self.profile), "--json", *command.split()]), 1)
                api.request_raw.assert_not_called()
                runtime.VERIFIED_USER = UserSettings("alice", "fixture")
                confirm.return_value = True
                api.request_raw.return_value = {"success": True}
                self.assertTrue(command_result(command).ok)
                api.request_raw.assert_called_once()
                api.request_raw.reset_mock()
                api.request_raw.side_effect = DucoAPIRequestError("fixture")
                self.assertFalse(command_result(command).ok)
                api.request_raw.assert_called_once()

    def test_expansion_limit(self):
        """
        *test_expansion_limit Check the fixed-point preview limit on either side of the decimal point.*
        """
        with patch("commands.wallet.Confirm.ask", return_value=False) as confirm, patch("commands.wallet.CONSOLE"):
            for amount in ("1e128", "1e-128"):
                self.assertIn("128 digits", command_result(["send", "bob", amount]).message)
            confirm.assert_not_called()
            for amount in ("1e127", "1e-127", "0.1"):
                self.assertIn("cancelled", command_result(["send", "bob", amount]).message)

    def test_config_modes_and_qualified_completion(self):
        """
        *test_config_modes_and_qualified_completion Check access-mode reporting and completion for qualified config commands.*
        """
        for password, flags, mode in [("", [], "Read-only"), ("fixture", [], "Standard"),
                                      ("fixture", ["--read-only"], "Read-only")]:
            self.profile.write_text(f'[user]\nusername="alice"\npassword="{password}"\n')
            for words in (["config", "show"], ["config", "config", "show"]):
                output = StringIO()
                with redirect_stdout(output):
                    self.assertEqual(main(["--settings", str(self.profile), "--json", *flags, *words]), 0)
                data = json.loads(output.getvalue())["data"]
                self.assertEqual(next(row["Value"] for row in data if row["Setting"] == "Mode"), mode)
        values = CommandCompleter().get_completions(Document("config config sh"), None)
        self.assertIn("show", [value.text for value in values])


if __name__ == "__main__":
    unittest.main()
