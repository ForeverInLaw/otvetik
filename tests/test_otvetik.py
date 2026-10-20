import importlib.util
import json
import sys
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch


def load_plugin():
    """Replace Android boundaries while keeping the real HTTP implementation."""
    sdk = {
        "android": {"R": Mock()},
        "android.text": {"InputType": Mock()},
        "android.text.method": {"PasswordTransformationMethod": Mock()},
        "android.widget": {"ImageView": Mock(), "LinearLayout": Mock()},
        "android_utils": {
            "OnClickListener": lambda callback: callback,
            "run_on_ui_thread": lambda callback: callback(),
        },
        "base_plugin": {
            "BasePlugin": type("BasePlugin", (), {}),
            "MenuItemData": lambda **kwargs: SimpleNamespace(**kwargs),
            "MenuItemType": SimpleNamespace(MESSAGE_CONTEXT_MENU=1),
        },
        "client_utils": {
            "get_last_fragment": Mock(),
            "get_messages_controller": Mock(),
            "send_request": Mock(),
        },
        "org.telegram.messenger": {"AndroidUtilities": Mock()},
        "org.telegram.tgnet": {
            "TLRPC": SimpleNamespace(TL_messages_getHistory=SimpleNamespace)
        },
        "org.telegram.ui": {"ChatActivity": type("ChatActivity", (), {})},
        "org.telegram.ui.ActionBar": {"Theme": Mock()},
        "org.telegram.ui.Components": {"EditTextBoldCursor": Mock()},
        "ui.alert": {"AlertDialogBuilder": Mock()},
        "ui.bulletin": {"BulletinHelper": Mock()},
        "ui.settings": {
            name: (lambda **kwargs: SimpleNamespace(**kwargs))
            for name in ("Divider", "Header", "Text")
        },
    }
    modules = {}
    for name, members in sdk.items():
        modules[name] = ModuleType(name)
        modules[name].__dict__.update(members)
    spec = importlib.util.spec_from_file_location(
        "otvetik_under_test", Path(__file__).resolve().parents[1] / "otvetik.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module


plugin = load_plugin()


def message(number, *, out=False, text=None, forwarded=False):
    return SimpleNamespace(
        id=number,
        out=out,
        message=str(number) if text is None else text,
        fwd_from=object() if forwarded else None,
    )


def history(messages):
    return SimpleNamespace(
        messages=SimpleNamespace(size=lambda: len(messages), get=messages.__getitem__)
    )


class ContextTests(unittest.TestCase):
    def test_each_speaker_gets_ten_across_pages_in_chronological_order(self):
        window = plugin.ContextWindow()
        window.add_page([message(i, out=True) for i in range(11, 31)])
        window.add_page([message(i) for i in range(1, 12)])
        window.add_page([message(i) for i in range(1, 12)])
        self.assertTrue(window.complete)
        self.assertEqual(window.counts, {"me": 10, "peer": 10})
        self.assertEqual(
            [int(line["text"]) for line in window.dialogue],
            list(range(1, 11)) + list(range(21, 31)),
        )

    def test_blank_forwarded_and_unsent_messages_are_excluded(self):
        window = plugin.ContextWindow()
        window.add_page(
            [message(0), message(1, text="  "), message(2, forwarded=True), message(3)]
        )
        self.assertEqual(window.dialogue, [{"speaker": "peer", "text": "3"}])
        self.assertFalse(window.complete)


class ClientTests(unittest.TestCase):
    def test_real_http_request_and_redirect_do_not_leak_authorization(self):
        captured = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                captured.append((self.path, dict(self.headers), json.loads(body)))
                if self.path.startswith("/redirect/"):
                    self.send_response(302)
                    self.send_header("Location", "/destination")
                    self.end_headers()
                else:
                    self.reply()

            def do_GET(self):
                captured.append((self.path, dict(self.headers), None))
                self.reply()

            def reply(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {"choices": [{"message": {"content": "  давай  "}}]}
                    ).encode()
                )

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            dialogue = [{"speaker": "peer", "text": "Пойдём?"}]
            for path in ("/v1/", "/v1/chat/completions"):
                client = plugin.ChatClient(base + path, "my-model", "test-key")
                self.assertEqual(client.generate(dialogue), "давай")
                endpoint, headers, body = captured[-1]
                self.assertEqual(endpoint, "/v1/chat/completions")
                self.assertEqual(headers["Authorization"], "Bearer test-key")
                self.assertEqual(body["model"], "my-model")
                self.assertEqual(
                    json.loads(body["messages"][1]["content"]), {"dialogue": dialogue}
                )
                self.assertNotIn("test-key", json.dumps(body))
            plugin.ChatClient(base + "/redirect", "model", "secret").generate(dialogue)
            self.assertEqual(captured[-1][0], "/destination")
            self.assertNotIn("Authorization", captured[-1][1])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_invalid_configuration_never_reaches_the_network(self):
        with patch.object(plugin, "urlopen") as network:
            for settings in (
                ("", "model", "key"),
                ("https://example.com/v1", "", "key"),
                ("https://example.com/v1", "model", ""),
                ("ftp://example.com", "model", "key"),
                ("https://key@example.com", "model", "key"),
                ("https://example.com:bad", "model", "key"),
                ("https://[invalid", "model", "key"),
            ):
                with (
                    self.subTest(settings=settings),
                    self.assertRaises(plugin.ReplyError),
                ):
                    plugin.ChatClient(*settings)
            network.assert_not_called()

    def test_malformed_empty_and_oversized_responses_are_safe_errors(self):
        client = plugin.ChatClient("https://example.com/v1", "model", "key")
        for data in (
            b"private-server-error",
            b'{"choices": []}',
            b'{"choices": [{"message": {"content": " "}}]}',
            b"x" * (plugin.MAX_RESPONSE_BYTES + 1),
        ):
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.read.return_value = data
            with patch.object(plugin, "urlopen", return_value=response):
                with self.assertRaises(plugin.ReplyError) as error:
                    client.generate([])
                self.assertNotIn("private-server-error", str(error.exception))


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.instance = plugin.OtvetikPlugin()
        self.instance.add_menu_item = Mock()
        self.instance.get_setting = Mock(side_effect=lambda key, default="": default)
        self.instance.on_plugin_load()
        self.job = plugin.Generation(1, 42, 500, Mock(), offset=501)
        self.instance._job = self.job
        self.editor = Mock()
        self.editor.isEditingMessage.return_value = False
        self.editor.getFieldText.return_value = ""
        self.fragment = plugin.ChatActivity()
        self.fragment.getCurrentAccount = lambda: 1
        self.fragment.getDialogId = lambda: 42
        self.fragment.getChatActivityEnterView = lambda: self.editor
        self.fragment.getParentActivity = Mock()
        plugin.get_last_fragment.return_value = self.fragment
        plugin.BulletinHelper.reset_mock()
        plugin.AlertDialogBuilder.reset_mock(return_value=True)
        plugin.send_request.reset_mock(side_effect=True)

    def test_history_uses_explicit_account_and_selected_message_boundary(self):
        self.instance._load_history(self.job)
        request = plugin.send_request.call_args.args[0]
        self.assertEqual(request.max_id, 501)
        self.assertEqual(request.offset_id, 501)
        self.assertEqual(request.limit, 100)
        self.assertEqual(plugin.send_request.call_args.kwargs["account"], 1)
        plugin.get_messages_controller.assert_called_with(1)

    def test_history_paginates_past_service_messages_and_stops_at_limit(self):
        self.instance._load_history = Mock()
        self.instance._generate = Mock()
        self.instance._history_ready(self.job, history([message(490, text="")]), None)
        self.assertEqual(self.job.offset, 490)
        self.instance._load_history.assert_called_once_with(self.job)
        self.job.pages = plugin.MAX_PAGES - 1
        self.instance._history_ready(self.job, history([message(480)]), None)
        self.instance._generate.assert_called_once_with(self.job)

    def test_history_failure_releases_busy_state(self):
        plugin.send_request.side_effect = RuntimeError("private-message-content")
        self.instance._load_history(self.job)
        self.assertIsNone(self.instance._job)
        self.assertNotIn(
            "private-message-content", str(plugin.BulletinHelper.show_error.call_args)
        )

    def test_unexpected_history_response_releases_busy_state(self):
        self.instance._history_ready(self.job, SimpleNamespace(), None)
        self.assertIsNone(self.instance._job)

    def test_changed_chat_account_and_edit_mode_prevent_insertion(self):
        for account, chat, editing in ((2, 42, False), (1, 43, False), (1, 42, True)):
            with self.subTest(account=account, chat=chat, editing=editing):
                self.fragment.getCurrentAccount = Mock(return_value=account)
                self.fragment.getDialogId = Mock(return_value=chat)
                self.editor.isEditingMessage.return_value = editing
                self.instance._insert_reply(self.job, "new reply")
                self.editor.setFieldText.assert_not_called()

    def test_unload_and_stale_response_prevent_insertion(self):
        self.instance._reply_ready(plugin.Generation(1, 42, 499, Mock()), "stale")
        self.instance.on_plugin_unload()
        self.instance._reply_ready(self.job, "late")
        self.editor.setFieldText.assert_not_called()

    def test_existing_draft_requires_explicit_replacement(self):
        self.editor.getFieldText.return_value = "my draft"
        self.instance._reply_ready(self.job, "suggestion")
        self.editor.setFieldText.assert_not_called()
        dialog = plugin.AlertDialogBuilder.return_value
        dialog.set_negative_button.assert_called_once_with("Отмена")
        apply = dialog.set_positive_button.call_args.args[1]
        apply(dialog, 1)
        self.editor.setFieldText.assert_called_once_with("suggestion")

    def test_empty_editor_receives_draft(self):
        self.instance._reply_ready(self.job, "suggestion")
        self.editor.setFieldText.assert_called_once_with("suggestion")
        self.assertIsNone(self.instance._job)

    def test_missing_settings_prevent_history_access(self):
        self.instance._job = None
        incoming = SimpleNamespace(
            isOutOwner=lambda: False,
            getDialogId=lambda: 42,
            messageOwner=message(500),
        )
        # Android passes a Java HashMap, which supports get but not subscription.
        context = SimpleNamespace(get={"account": 1, "message": incoming}.get)
        self.instance._start(context)
        plugin.send_request.assert_not_called()
        self.assertIsNone(self.instance._job)

    def test_settings_do_not_reveal_api_key(self):
        self.instance.get_setting.side_effect = lambda key, default="": (
            "test-secret" if key == "api_key" else default
        )
        settings = self.instance.create_settings()
        self.assertEqual(settings[3].subtext, "Добавлен")
        self.assertNotIn("test-secret", str(settings))

    def test_unexpected_transport_error_does_not_reveal_credentials(self):
        self.job.window.add_page([message(500)])
        self.job.client.generate.side_effect = ValueError("test-secret")
        with patch.object(
            plugin,
            "Thread",
            side_effect=lambda **kw: SimpleNamespace(start=kw["target"]),
        ):
            self.instance._generate(self.job)
        self.assertIsNone(self.instance._job)
        self.assertNotIn("test-secret", str(plugin.BulletinHelper.show_error.call_args))


if __name__ == "__main__":
    unittest.main()
