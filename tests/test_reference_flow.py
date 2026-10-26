"""Exercise the host's exact-edit boundary without models or network access."""

from dataclasses import replace
from hashlib import sha256
import json
import subprocess
import sys
from threading import Event
import unittest

from ringo_ide.demo import EventCancellation, run_demo
from ringo_ide.editor.context.provider import DocumentSnapshot
from ringo_ide.protocol.messages import (
    ByteRange, CompletionRequest, CompletionResult, DocumentVersion,
    RequestIdentity, TerminalResult,
)
from ringo_ide.validation.edits import InvalidEdit, SnapshotEditValidator, apply_completion
from ringo_ide.workers.fixture import FixtureBackend


def example(text="x = \n", start=4, end=4):
    document = DocumentVersion("doc", 1, sha256(text.encode()).hexdigest())
    snapshot = DocumentSnapshot(document, text)
    request = CompletionRequest(
        RequestIdentity("session", "request", document), ByteRange(start, end),
        "x = ", "\n", "python", 64, 200,
    )
    return snapshot, request, CompletionResult(request.identity, "42")


class EditTests(unittest.TestCase):
    def test_insert_and_replace_preserve_untouched_bytes(self):
        for text, start, end, expected in [
            ("x = \n", 4, 4, "x = 42\n"),
            ("x = old\r\n", 4, 7, "x = 42\r\n"),
            ("", 0, 0, "42"),
            ("x", 1, 1, "x42"),
        ]:
            with self.subTest(text=text):
                snapshot, request, result = example(text, start, end)
                self.assertEqual(apply_completion(snapshot, request, result), expected)
                self.assertEqual(snapshot.text, text)

    def test_unicode_ranges_use_utf8_bytes(self):
        text = "😀e\u0301\t旧\r\n"
        start = len("😀e\u0301\t".encode())
        snapshot, request, result = example(text, start, start + len("旧".encode()))
        self.assertEqual(apply_completion(snapshot, request, result), "😀e\u0301\t42\r\n")

    def test_rejects_utf8_and_crlf_splits(self):
        for text, start, end in [("😀\n", 1, 1), ("😀\n", 0, 3), ("a\r\n", 2, 2)]:
            with self.subTest(text=text, start=start, end=end):
                with self.assertRaises(InvalidEdit):
                    apply_completion(*example(text, start, end))

    def test_rejects_invalid_range_bounds_and_types(self):
        for start, end in [(-1, 0), (5, 4), (0, 100), (True, 4), (0.5, 4)]:
            with self.subTest(start=start, end=end):
                with self.assertRaises(InvalidEdit):
                    apply_completion(*example(start=start, end=end))

    def test_rejects_every_stale_identity_component(self):
        snapshot, request, result = example()
        identity = request.identity
        for changed in [
            replace(identity, session_id="new-session"),
            replace(identity, request_id="new-request"),
            replace(identity, document=replace(identity.document, document_id="reopened")),
            replace(identity, document=replace(identity.document, version=2)),
            replace(identity, document=replace(identity.document, sha256="0" * 64)),
        ]:
            with self.subTest(identity=changed):
                with self.assertRaises(InvalidEdit):
                    apply_completion(snapshot, request, replace(result, identity=changed))

    def test_rejects_changed_snapshot_even_with_matching_old_metadata(self):
        snapshot, request, result = example()
        with self.assertRaises(InvalidEdit):
            apply_completion(replace(snapshot, text="edited\n"), request, result)

    def test_rejects_new_document_revision(self):
        snapshot, request, result = example()
        current = replace(snapshot, document=replace(snapshot.document, version=2))
        with self.assertRaises(InvalidEdit):
            apply_completion(current, request, result)

    def test_noncomplete_outcomes_cannot_be_applied(self):
        snapshot, request, _ = example()
        for status in ["no_suggestion", "cancelled", "expired", "error"]:
            with self.subTest(status=status):
                with self.assertRaises(InvalidEdit):
                    apply_completion(snapshot, request, TerminalResult(request.identity, status, "test"))

    def test_empty_output_is_not_an_edit(self):
        snapshot, request, result = example()
        with self.assertRaises(InvalidEdit):
            apply_completion(snapshot, request, replace(result, replacement_text=""))

    def test_output_limit_is_bytes_not_characters(self):
        snapshot, request, result = example()
        with self.assertRaises(InvalidEdit):
            apply_completion(snapshot, request, replace(result, replacement_text="😀"), max_output_bytes=3)

    def test_surrogate_is_rejected(self):
        snapshot, request, result = example()
        with self.assertRaises(InvalidEdit):
            apply_completion(snapshot, request, replace(result, replacement_text="\ud800"))

    def test_invalid_output_caps(self):
        for cap in [0, -1, True, 1.5]:
            with self.subTest(cap=cap):
                with self.assertRaises(ValueError):
                    SnapshotEditValidator(cap)


class FixtureTests(unittest.TestCase):
    def setUp(self):
        _, self.request, _ = example()
        self.cancel_event = Event()
        self.signal = EventCancellation(self.cancel_event)
        self.backend = FixtureBackend(self.request, "42")

    def tearDown(self):
        self.backend.close()

    def test_fixture_matches_contract_and_names_itself(self):
        self.assertEqual(self.backend.capabilities().backend_name, "fixture")
        self.assertEqual(self.backend.complete(self.request, self.signal), CompletionResult(self.request.identity, "42"))

    def test_cancellation_never_produces_editable_payload(self):
        self.cancel_event.set()
        result = self.backend.complete(self.request, self.signal)
        self.assertEqual(result.status, "cancelled")
        self.assertFalse(hasattr(result, "replacement_text"))

    def test_nonmatching_request_fails(self):
        result = self.backend.complete(replace(self.request, prefix="changed"), self.signal)
        self.assertEqual(result.status, "error")

    def test_empty_fixture_is_no_suggestion(self):
        result = FixtureBackend(self.request, "").complete(self.request, self.signal)
        self.assertEqual(result.status, "no_suggestion")

    def test_large_fixture_is_error(self):
        result = FixtureBackend(self.request, "😀" * 1025).complete(self.request, self.signal)
        self.assertEqual(result.status, "error")

    def test_closed_backend_rejects_work(self):
        self.backend.close()
        self.backend.close()
        with self.assertRaises(RuntimeError):
            self.backend.complete(self.request, self.signal)
        with self.assertRaises(RuntimeError):
            self.backend.capabilities()


class DemoTests(unittest.TestCase):
    def test_demo_completes_expected_document(self):
        demo = run_demo()
        self.assertFalse(demo["model_inference"])
        self.assertEqual(demo["after"], 'def greet(name):\n    return f"Hello, {name}!"\n')

    def test_module_entrypoint(self):
        result = subprocess.run(
            [sys.executable, "-m", "ringo_ide", "demo"],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(json.loads(result.stdout), run_demo())
        self.assertEqual(result.stderr, "")

    def test_imports_do_not_load_model_libraries(self):
        script = """
import importlib, pkgutil, sys
import ringo_ide
for entry in pkgutil.walk_packages(ringo_ide.__path__, ringo_ide.__name__ + '.'):
    importlib.import_module(entry.name)
assert not {'torch', 'transformers', 'numpy', 'huggingface_hub'} & sys.modules.keys()
"""
        subprocess.run([sys.executable, "-c", script], check=True)

    def test_model_backends_remain_explicit_stubs(self):
        from ringo_ide.workers.baseline import BaselineBackend
        from ringo_ide.workers.config import BackendConfig
        from ringo_ide.workers.ncm import NcmBackend
        _, request, _ = example()
        for backend in [BaselineBackend(BackendConfig("baseline")), NcmBackend(BackendConfig("ncm"))]:
            with self.subTest(backend=type(backend).__name__):
                for operation in [backend.capabilities, backend.close,
                                  lambda: backend.complete(request, EventCancellation(Event()))]:
                    with self.assertRaises(NotImplementedError):
                        operation()


if __name__ == "__main__":
    unittest.main()
