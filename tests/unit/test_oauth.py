# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Browser sign-in protocol: PKCE, the loopback listener, the token file and refresh."""

import base64
import hashlib
import io
import json
import os
import socket
import stat
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest

from scenario.core.api import oauth
from scenario.core.keychain import KeychainError

APP = oauth.OAuthApp(
    issuer="https://idp.example.invalid",
    client_id="fixture-client",
    service="https://service.example.invalid/v1",
)


def _jwt(claims):
    def part(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")

    return f"{part({'alg': 'RS256', 'typ': 'at+jwt'})}.{part(claims)}.signature"


class _Opener:
    """A fake urllib opener: records each form POST and answers from a queue."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append(request)
        status, body = self.replies.pop(0)
        if isinstance(body, dict):
            body = json.dumps(body).encode()
        if status != 200:
            raise urllib.error.HTTPError(request.full_url, status, "", {}, io.BytesIO(body))
        reply = io.BytesIO(body)
        reply.status = 200
        reply.__enter__ = lambda *a: reply
        reply.__exit__ = lambda *a: None
        return reply

    def form(self, index=0):
        return dict(urllib.parse.parse_qsl(self.requests[index].data.decode()))


def _tokens(**overrides):
    values = dict(
        issuer=APP.issuer,
        client_id=APP.client_id,
        service=APP.service,
        subject="user_1",
        access_token="access-1",
        refresh_token="refresh-1",
        expires_at=time.time() + 3600,
    )
    values.update(overrides)
    return oauth.TokenSet(**values)


# --- application selection ---------------------------------------------------


def test_production_application_is_the_default_and_knows_its_client_id():
    app = oauth.selected_app({})
    assert app is oauth.PRODUCTION_APP
    assert app.configured
    assert app.issuer == "https://clerk.scenario.com"
    assert app.service == "https://api.cloud.scenario.com/v1"
    assert app.client_id == "gUzfnnOTmz5SqATM"


def test_developer_override_needs_all_three_https_values_together():
    override = {
        "SCENARIO_OAUTH_ISSUER": "https://idp.example.invalid/",
        "SCENARIO_OAUTH_CLIENT_ID": " dev-client ",
        "SCENARIO_API_BASE": "https://api.example.invalid/v1/",
    }
    app = oauth.selected_app(override)
    assert app.configured
    assert (app.issuer, app.client_id, app.service) == (
        "https://idp.example.invalid",
        "dev-client",
        "https://api.example.invalid/v1",
    )
    for missing in override:
        partial = {k: v for k, v in override.items() if k != missing}
        with pytest.raises(oauth.SignInError, match="together"):
            oauth.selected_app(partial)
    with pytest.raises(oauth.SignInError):
        oauth.selected_app({**override, "SCENARIO_OAUTH_ISSUER": "http://idp.example.invalid"})
    with pytest.raises(oauth.SignInError):
        oauth.selected_app({**override, "SCENARIO_API_BASE": "https://u:p@api.example.invalid"})


def test_authorize_url_carries_pkce_state_and_the_registered_scopes():
    challenge = oauth.new_challenge()
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(challenge.verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )
    assert challenge.challenge == expected
    assert 43 <= len(challenge.verifier) <= 128
    assert challenge.state != oauth.new_challenge().state
    assert "verifier" not in repr(challenge) or challenge.verifier not in repr(challenge)
    url = APP.authorize_url(
        redirect_uri="http://127.0.0.1:9877/callback", state="st", challenge="ch"
    )
    parts = urllib.parse.urlsplit(url)
    assert parts.scheme == "https" and parts.netloc == "idp.example.invalid"
    assert parts.path == "/oauth/authorize"
    assert dict(urllib.parse.parse_qsl(parts.query)) == {
        "response_type": "code",
        "client_id": "fixture-client",
        "redirect_uri": "http://127.0.0.1:9877/callback",
        "scope": "profile email offline_access",
        "state": "st",
        "code_challenge": "ch",
        "code_challenge_method": "S256",
    }


# --- token endpoint -----------------------------------------------------------


def test_exchange_sends_the_verifier_without_a_secret_and_reads_the_account():
    opener = _Opener(
        (
            200,
            {
                "access_token": _jwt({"sub": "user_1", "exp": 1}),
                "refresh_token": "refresh-1",
                "expires_in": 86_400,
            },
        )
    )
    tokens = oauth.exchange_code(
        APP,
        "code-1",
        verifier="verifier-1",
        redirect_uri="http://127.0.0.1:9877/callback",
        opener=opener,
    )
    request = opener.requests[0]
    assert request.full_url == "https://idp.example.invalid/oauth/token"
    assert request.get_method() == "POST"
    assert request.get_header("User-agent", "").startswith("ScenarioBlender/")
    assert opener.form() == {
        "grant_type": "authorization_code",
        "client_id": "fixture-client",
        "code": "code-1",
        "redirect_uri": "http://127.0.0.1:9877/callback",
        "code_verifier": "verifier-1",
    }
    assert tokens.subject == "user_1"
    assert tokens.account == "https://idp.example.invalid#user_1"
    assert tokens.matches(APP)
    assert time.time() + 86_000 < tokens.expires_at
    assert "access-" not in repr(tokens) and "refresh-1" not in repr(tokens)


@pytest.mark.parametrize(
    "reply, message",
    [
        ((400, {"error": "invalid_grant"}), "HTTP 400"),
        ((200, b"not json"), "unreadable"),
        ((200, {"access_token": "x", "refresh_token": "r"}), "without an account"),
        ((200, {"access_token": _jwt({"sub": "user_1"})}), "no tokens"),
    ],
)
def test_exchange_refusals_name_the_problem_without_the_code(reply, message):
    opener = _Opener(reply)
    with pytest.raises(oauth.SignInError, match=message) as excinfo:
        oauth.exchange_code(
            APP,
            "secret-code",
            verifier="v",
            redirect_uri="http://127.0.0.1:1/callback",
            opener=opener,
        )
    assert "secret-code" not in str(excinfo.value)


def test_refresh_rotates_the_pair_and_keeps_the_old_refresh_token_when_none_is_sent():
    opener = _Opener(
        (200, {"access_token": _jwt({"sub": "user_1"}), "expires_in": 60}),
    )
    rotated = oauth.refresh_tokens(APP, _tokens(), opener=opener)
    assert opener.form() == {
        "grant_type": "refresh_token",
        "client_id": "fixture-client",
        "refresh_token": "refresh-1",
    }
    assert rotated.refresh_token == "refresh-1"
    assert rotated.access_token != "access-1"
    assert rotated.account == _tokens().account


def test_only_the_providers_invalid_grant_ends_a_session():
    with pytest.raises(oauth.SignedOut):
        oauth.refresh_tokens(APP, _tokens(), opener=_Opener((400, {"error": "invalid_grant"})))
    for reply in (
        (401, b"<html>challenge</html>"),
        (400, {"error": "temporarily_unavailable"}),
        (502, b""),
    ):
        with pytest.raises(oauth.SignInError) as excinfo:
            oauth.refresh_tokens(APP, _tokens(), opener=_Opener(reply))
        assert not isinstance(excinfo.value, oauth.SignedOut)


# --- loopback listener --------------------------------------------------------


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, ""


@pytest.fixture
def listener():
    servers = []

    def start(state="state-1"):
        server = oauth.LoopbackServer(state, ports=(0,))
        servers.append(server)
        return server

    yield start
    for server in servers:
        server.close()


def test_listener_takes_one_matching_callback_and_ignores_the_rest(listener):
    server = listener()
    base = server.redirect_uri.rsplit("/", 1)[0]
    assert server.redirect_uri.startswith("http://127.0.0.1:")
    assert _get(f"{base}/other?state=state-1&code=x")[0] == 404
    assert _get(f"{server.redirect_uri}?state=wrong&code=x")[0] == 400
    assert _get(f"{server.redirect_uri}?state=%C3%A9&code=x")[0] == 400
    status, page = _get(f"{server.redirect_uri}?state=state-1&code=code-1")
    assert status == 200 and "close this tab" in page
    assert _get(f"{server.redirect_uri}?state=state-1&code=code-2")[0] == 404
    assert server.wait(timeout=1) == "code-1"


@pytest.mark.parametrize(
    "query, message",
    [("state=state-1&error=access_denied", "denied"), ("state=state-1", "invalid")],
)
def test_listener_reports_denial_and_malformed_callbacks(listener, query, message):
    server = listener()
    status, page = _get(f"{server.redirect_uri}?{query}")
    assert status == 200 and "not completed" in page
    with pytest.raises(oauth.SignInError, match=message):
        server.wait(timeout=1)


def test_a_silent_connection_holds_neither_the_callback_nor_close(listener, monkeypatch):
    # A browser can open a connection it never uses; the listener serves one at a time.
    monkeypatch.setattr(oauth, "CALLBACK_READ_TIMEOUT", 0.3)
    server = listener()
    address = ("127.0.0.1", urllib.parse.urlsplit(server.redirect_uri).port)
    with socket.create_connection(address):
        status, page = _get(f"{server.redirect_uri}?state=state-1&code=code-1")
        assert status == 200 and "close this tab" in page
        assert server.wait(timeout=1) == "code-1"
        with socket.create_connection(address):
            started = time.monotonic()
            server.close()
            assert time.monotonic() - started < 2


def test_listener_wait_honors_timeout_and_cancellation(listener):
    server = listener()
    started = time.monotonic()
    with pytest.raises(oauth.SignInError, match="in time"):
        server.wait(timeout=0.3)
    assert time.monotonic() - started < 2
    cancelled = threading.Event()
    cancelled.set()
    with pytest.raises(oauth.SignInError, match="cancelled"):
        server.wait(timeout=5, cancelled=cancelled)


def test_attempt_refuses_an_unconfigured_application_and_a_late_cancel(monkeypatch):
    unconfigured = oauth.OAuthApp(issuer=APP.issuer, client_id="", service=APP.service)
    with pytest.raises(oauth.SignInError, match="not available"):
        oauth.SignInAttempt(unconfigured)
    monkeypatch.setattr(oauth, "LOOPBACK_PORTS", (0,))
    attempt = oauth.SignInAttempt(APP)
    try:
        assert attempt.url.startswith("https://idp.example.invalid/oauth/authorize?")
        assert urllib.parse.quote(attempt.redirect_uri, safe="") in attempt.url
        _get(f"{attempt.redirect_uri}?state={attempt._challenge.state}&code=code-1")
        cancelled = threading.Event()
        cancelled.set()
        opener = _Opener()
        with pytest.raises(oauth.SignInError, match="cancelled"):
            attempt.complete(cancelled=cancelled, timeout=1, opener=opener)
        assert opener.requests == []
    finally:
        attempt.close()


# --- token storage ------------------------------------------------------------


class _Keychain:
    """A credential store in memory, counting reads, that can refuse or stay silent."""

    name = "the test keychain"

    def __init__(self):
        self.entries = {}
        self.reads = 0
        self.refuse_writes = False
        self.refuse_deletes = False
        self.silent = False
        self.gate = None  # An Event a deletion waits for.

    def read(self, slot):
        self.reads += 1
        if self.silent:
            raise KeychainError("the test keychain did not answer")
        return self.entries.get(slot)

    def write(self, slot, secret):
        if self.refuse_writes or self.silent:
            raise KeychainError("the test keychain refused to save the sign-in")
        self.entries[slot] = secret

    def delete(self, slot):
        if self.gate is not None:
            self.gate.wait(5)
        if self.silent or self.refuse_deletes:
            raise KeychainError("the test keychain did not answer")
        self.entries.pop(slot, None)


@pytest.fixture(params=["file", "keychain"])
def storage(request, tmp_path):
    store = _Keychain() if request.param == "keychain" else None
    return oauth.TokenStorage(tmp_path / "sign-in.json", store)


def _refresh_token(storage):
    saved = storage.load()
    return saved.tokens.refresh_token if saved is not None else None


def _record(storage):
    return json.loads(storage.path.read_bytes())


def test_without_a_store_the_private_file_holds_the_refresh_token_only(tmp_path):
    storage = oauth.TokenStorage(tmp_path / "sign-in.json")
    assert storage.save(_tokens()) == ""
    assert stat.S_IMODE(storage.path.stat().st_mode) == 0o600
    assert [p.name for p in tmp_path.iterdir()] == ["sign-in.json"]
    record = _record(storage)
    assert record["refresh_token"] == "refresh-1"
    assert "access-1" not in storage.path.read_text()
    saved = storage.load()
    assert saved == storage.saved()
    assert (saved.tokens.account, saved.tokens.refresh_token) == (_tokens().account, "refresh-1")
    assert (saved.tokens.access_token, saved.slot) == ("", "")
    assert saved.tokens.expiring()
    assert storage.where("") == oauth.STORED_PRIVATELY


def test_with_a_store_the_file_names_the_entry_and_holds_no_token(tmp_path):
    keychain = _Keychain()
    storage = oauth.TokenStorage(tmp_path / "sign-in.json", keychain)
    slot = storage.save(_tokens())
    assert keychain.entries == {slot: "refresh-1"}
    assert _record(storage)["keychain"] == slot
    text = storage.path.read_text()
    assert "refresh-1" not in text and "access-1" not in text
    # The file alone names the account without touching the store.
    saved = storage.saved()
    assert (saved.tokens.account, saved.tokens.refresh_token, saved.slot) == (
        _tokens().account,
        "",
        slot,
    )
    assert keychain.reads == 0
    assert storage.load().tokens.refresh_token == "refresh-1"
    assert keychain.reads == 1
    assert storage.where(slot) == "the test keychain"


def test_a_store_that_refuses_leaves_the_token_in_the_private_file(tmp_path):
    keychain = _Keychain()
    keychain.refuse_writes = True
    storage = oauth.TokenStorage(tmp_path / "sign-in.json", keychain)
    assert storage.save(_tokens()) == ""
    assert keychain.entries == {}
    assert _record(storage)["refresh_token"] == "refresh-1"
    assert storage.where("") == oauth.STORED_PRIVATELY


def test_a_new_sign_in_replaces_the_previous_entry_and_a_refresh_keeps_it(tmp_path):
    keychain = _Keychain()
    storage = oauth.TokenStorage(tmp_path / "sign-in.json", keychain)
    first = storage.save(_tokens())
    assert storage.save(_tokens(refresh_token="refresh-2"), first) == first
    assert keychain.entries == {first: "refresh-2"}
    second = storage.save(_tokens(subject="user_2", refresh_token="refresh-9"))
    assert second != first
    assert keychain.entries == {second: "refresh-9"}


def test_an_unwritable_file_leaves_no_new_entry_behind(tmp_path, monkeypatch):
    keychain = _Keychain()
    storage = oauth.TokenStorage(tmp_path / "sign-in.json", keychain)
    slot = storage.save(_tokens())

    def full(path, record):
        raise OSError("disk full")

    monkeypatch.setattr(oauth, "_write_record", full)
    with pytest.raises(OSError):
        storage.save(_tokens(subject="user_2"))
    assert keychain.entries == {slot: "refresh-1"}


def test_clear_deletes_the_file_at_once_and_the_entries_on_their_own_thread(tmp_path):
    keychain = _Keychain()
    storage = oauth.TokenStorage(tmp_path / "sign-in.json", keychain)
    slot = storage.save(_tokens())
    keychain.entries["older"] = "refresh-0"
    thread = storage.clear("older")
    assert not storage.path.exists()
    thread.join(5)
    assert keychain.entries == {}
    assert storage.clear() is None
    assert storage.load() is None
    assert slot


def test_an_entry_the_store_does_not_delete_at_sign_out_stays_named(tmp_path):
    keychain = _Keychain()
    storage = oauth.TokenStorage(tmp_path / "sign-in.json", keychain)
    slot = storage.save(_tokens())
    keychain.refuse_deletes = True
    storage.clear().join(5)
    assert _record(storage) == {"format": "scenario-browser-sign-in-v2", "retired": [slot]}
    assert storage.saved() is None
    keychain.refuse_deletes = False
    storage.clear().join(5)
    assert keychain.entries == {} and not storage.path.exists()


def test_a_replaced_entry_the_store_does_not_delete_stays_named_until_it_does(tmp_path):
    keychain = _Keychain()
    storage = oauth.TokenStorage(tmp_path / "sign-in.json", keychain)
    first = storage.save(_tokens())
    keychain.refuse_deletes = True
    second = storage.save(_tokens(refresh_token="refresh-2"))
    assert _record(storage)["retired"] == [first]
    assert storage.load().tokens.refresh_token == "refresh-2"
    keychain.refuse_deletes = False
    assert storage.save(_tokens(refresh_token="refresh-3"), second) == second
    assert keychain.entries == {second: "refresh-3"}
    assert "retired" not in _record(storage)


def test_a_sign_in_saved_while_a_sign_out_deletes_keeps_its_session(tmp_path):
    keychain = _Keychain()
    storage = oauth.TokenStorage(tmp_path / "sign-in.json", keychain)
    first = storage.save(_tokens())
    keychain.gate, keychain.refuse_deletes = threading.Event(), True
    thread = storage.clear()
    second = storage.save(_tokens(refresh_token="refresh-2"))
    keychain.gate.set()
    thread.join(5)
    assert storage.load().tokens.refresh_token == "refresh-2"
    assert storage.saved().slot == second
    assert _record(storage)["retired"] == [first]


def test_a_store_that_does_not_answer_is_reported_not_taken_for_a_sign_out(tmp_path):
    keychain = _Keychain()
    storage = oauth.TokenStorage(tmp_path / "sign-in.json", keychain)
    storage.save(_tokens())
    keychain.silent = True
    with pytest.raises(KeychainError):
        storage.load()
    assert storage.saved() is not None


def test_an_entry_in_a_store_this_blender_does_not_use_reads_as_no_session(tmp_path):
    oauth.TokenStorage(tmp_path / "sign-in.json", _Keychain()).save(_tokens())
    opted_out = oauth.TokenStorage(tmp_path / "sign-in.json")
    assert opted_out.saved() is not None
    assert opted_out.load() is None


def test_saving_after_opting_out_of_the_store_moves_the_token_to_the_file(tmp_path):
    keychain = _Keychain()
    slot = oauth.TokenStorage(tmp_path / "sign-in.json", keychain).save(_tokens())
    opted_out = oauth.TokenStorage(tmp_path / "sign-in.json")
    assert opted_out.save(_tokens(refresh_token="refresh-2")) == ""
    assert opted_out.load().tokens.refresh_token == "refresh-2"
    # The entry it may not delete stays named, so a Blender that uses the store can.
    assert _record(opted_out)["retired"] == [slot]
    assert keychain.entries == {slot: "refresh-1"}


def test_an_opted_out_sign_out_keeps_its_entries_named_for_the_store(tmp_path):
    keychain = _Keychain()
    path = tmp_path / "sign-in.json"
    slot = oauth.TokenStorage(path, keychain).save(_tokens())
    opted_out = oauth.TokenStorage(path)
    assert opted_out.clear() is None
    assert _record(opted_out) == {"format": "scenario-browser-sign-in-v2", "retired": [slot]}
    assert opted_out.saved() is None and opted_out.load() is None
    assert opted_out.save(_tokens(refresh_token="refresh-2")) == ""
    assert _record(opted_out)["retired"] == [slot]
    assert opted_out.clear() is None
    assert keychain.entries == {slot: "refresh-1"}
    oauth.TokenStorage(path, keychain).clear().join(5)
    assert keychain.entries == {} and not path.exists()


def test_a_sign_in_with_the_store_deletes_entries_left_while_opted_out(tmp_path):
    keychain = _Keychain()
    path = tmp_path / "sign-in.json"
    first = oauth.TokenStorage(path, keychain).save(_tokens())
    oauth.TokenStorage(path).save(_tokens(refresh_token="refresh-2"))
    storage = oauth.TokenStorage(path, keychain)
    second = storage.save(_tokens(refresh_token="refresh-3"))
    assert keychain.entries == {second: "refresh-3"} and second != first
    assert "retired" not in _record(storage)


def test_a_file_from_before_the_store_keeps_its_refresh_token(tmp_path):
    path = tmp_path / "sign-in.json"
    path.write_text(
        json.dumps(
            {
                "format": "scenario-browser-sign-in-v1",
                "issuer": APP.issuer,
                "client_id": APP.client_id,
                "service": APP.service,
                "subject": "user_1",
                "access_token": "access-1",
                "refresh_token": "refresh-1",
                "expires_at": time.time() + 3600,
            }
        )
    )
    saved = oauth.TokenStorage(path, _Keychain()).saved()
    assert (saved.tokens.refresh_token, saved.tokens.access_token, saved.slot) == (
        "refresh-1",
        "",
        "",
    )


def _v2(**fields):
    record = {
        "format": "scenario-browser-sign-in-v2",
        "issuer": APP.issuer,
        "client_id": APP.client_id,
        "service": APP.service,
        "subject": "user_1",
    }
    record.update(fields)
    return json.dumps(record).encode()


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"[]",
        b'{"format": "other"}',
        b'{"format": "x", "a": 1}',
        _v2(),
        _v2(keychain="slot", refresh_token="refresh-1"),
        _v2(keychain=7),
        b'{"format": "scenario-browser-sign-in-v2", "refresh_token": "refresh-1"}',
    ],
)
def test_unreadable_foreign_or_ambiguous_token_files_are_ignored(tmp_path, content):
    path = tmp_path / "sign-in.json"
    path.write_bytes(content)
    assert oauth.TokenStorage(path, _Keychain()).load() is None


@pytest.mark.skipif(os.name == "nt", reason="symlinks need privileges on Windows")
def test_a_symlinked_token_file_is_never_read(tmp_path):
    oauth.TokenStorage(tmp_path / "real.json").save(_tokens())
    link = tmp_path / "sign-in.json"
    link.symlink_to(tmp_path / "real.json")
    assert oauth.TokenStorage(link).saved() is None


# --- token session ------------------------------------------------------------


class _Refresh:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def __call__(self, app, tokens):
        self.calls.append(tokens.refresh_token)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _session(storage, tokens, refresh):
    slot = storage.save(tokens)
    return oauth.TokenSession(APP, tokens, storage, slot=slot, refresh=refresh)


def _reopened(storage, refresh):
    """The session a Blender that just started builds from the file alone."""
    saved = storage.saved()
    return oauth.TokenSession(APP, saved.tokens, storage, slot=saved.slot, refresh=refresh)


def test_a_reopened_session_reads_its_token_on_the_first_request_only(tmp_path):
    keychain = _Keychain()
    storage = oauth.TokenStorage(tmp_path / "sign-in.json", keychain)
    slot = storage.save(_tokens())
    fresh = _tokens(access_token="access-2", refresh_token="refresh-2")
    refresh = _Refresh(fresh)
    session = _reopened(storage, refresh)
    assert session.peek() == ""
    assert session.account == _tokens().account
    assert session.stored_in == "the test keychain"
    assert keychain.reads == 0  # built on the main thread from the file alone
    assert session.bearer() == "access-2"
    assert session.bearer() == "access-2"
    assert refresh.calls == ["refresh-1"]
    assert keychain.reads == 1
    assert keychain.entries == {slot: "refresh-2"}
    assert session.peek() == "access-2"


def test_a_reopened_session_without_a_store_refreshes_from_the_file(tmp_path):
    storage = oauth.TokenStorage(tmp_path / "sign-in.json")
    storage.save(_tokens())
    refresh = _Refresh(_tokens(access_token="access-2", refresh_token="refresh-2"))
    session = _reopened(storage, refresh)
    assert session.bearer() == "access-2"
    assert refresh.calls == ["refresh-1"]
    assert _refresh_token(storage) == "refresh-2"


def test_a_session_saved_in_the_file_moves_to_the_store_at_its_next_refresh(tmp_path):
    oauth.TokenStorage(tmp_path / "sign-in.json").save(_tokens())
    keychain = _Keychain()
    storage = oauth.TokenStorage(tmp_path / "sign-in.json", keychain)
    session = _reopened(storage, _Refresh(_tokens(access_token="a2", refresh_token="refresh-2")))
    assert session.stored_in == oauth.STORED_PRIVATELY
    assert session.bearer() == "a2"
    record = _record(storage)
    assert "refresh_token" not in record
    assert keychain.entries == {record["keychain"]: "refresh-2"}
    assert session.stored_in == "the test keychain"


def test_a_store_that_does_not_answer_fails_the_request_and_keeps_the_session(tmp_path):
    keychain = _Keychain()
    storage = oauth.TokenStorage(tmp_path / "sign-in.json", keychain)
    storage.save(_tokens())
    refresh = _Refresh(_tokens(access_token="access-2", refresh_token="refresh-2"))
    session = _reopened(storage, refresh)
    keychain.silent = True
    with pytest.raises(oauth.SignInError, match="did not answer") as raised:
        session.bearer()
    assert not isinstance(raised.value, oauth.SignedOut)
    assert session.ended is None
    assert refresh.calls == []
    keychain.silent = False
    assert session.bearer() == "access-2"


def test_a_session_whose_saved_token_is_gone_asks_to_sign_in_again(tmp_path):
    keychain = _Keychain()
    storage = oauth.TokenStorage(tmp_path / "sign-in.json", keychain)
    storage.save(_tokens())
    keychain.entries.clear()  # deleted from the keychain by hand
    refresh = _Refresh()
    session = _reopened(storage, refresh)
    with pytest.raises(oauth.SignedOut, match="sign in again"):
        session.bearer()
    assert session.ended is not None
    assert refresh.calls == []


def test_session_refreshes_an_expiring_token_once_and_saves_it(storage):
    stale = _tokens(expires_at=time.time() + 10)
    fresh = _tokens(access_token="access-2", refresh_token="refresh-2")
    refresh = _Refresh(fresh)
    session = _session(storage, stale, refresh)
    assert session.peek() == "access-1"
    assert session.account == stale.account
    assert session.bearer() == "access-2"
    assert session.bearer() == "access-2"
    assert refresh.calls == ["refresh-1"]
    assert _refresh_token(storage) == "refresh-2"
    assert session.peek() == "access-2"


def test_session_serializes_concurrent_refreshes(storage):
    stale = _tokens(expires_at=time.time() + 10)
    gate = threading.Event()

    calls = []

    def slow_refresh(app, tokens):
        calls.append(tokens.refresh_token)
        gate.wait(5)
        return _tokens(access_token="access-2", refresh_token="refresh-2")

    session = _session(storage, stale, slow_refresh)
    results = []
    workers = [threading.Thread(target=lambda: results.append(session.bearer())) for _ in range(3)]
    for worker in workers:
        worker.start()
    time.sleep(0.2)
    assert session.peek() == "access-1"  # the main thread is not blocked by the refresh
    gate.set()
    for worker in workers:
        worker.join(5)
    assert results == ["access-2"] * 3
    assert calls == ["refresh-1"]  # one refresh for three waiting workers


def test_a_refused_refresh_ends_the_session_and_clears_only_its_own_save(storage):
    stale = _tokens(expires_at=time.time() + 10)
    session = _session(storage, stale, _Refresh(oauth.SignedOut("ended")))
    with pytest.raises(oauth.SignedOut):
        session.bearer()
    assert session.ended == "ended"
    assert storage.load() is None
    with pytest.raises(oauth.SignedOut):
        session.bearer()
    # Another process saved a newer refresh token: it is adopted first, so the
    # old one is never spent, and it survives this session's later failures.
    storage.save(_tokens(refresh_token="refresh-9"))
    refresh = _Refresh(_tokens(access_token="access-10", refresh_token="refresh-10"))
    session = oauth.TokenSession(
        APP, _tokens(expires_at=time.time() + 10, refresh_token="old"), storage, refresh=refresh
    )
    assert session.bearer() == "access-10"
    assert refresh.calls == ["refresh-9"]
    assert _refresh_token(storage) == "refresh-10"


def test_a_transient_refresh_failure_keeps_the_session(storage):
    stale = _tokens(expires_at=time.time() + 10)
    fresh = _tokens(access_token="access-2", refresh_token="refresh-2")
    session = _session(storage, stale, _Refresh(oauth.SignInError("HTTP 502"), fresh))
    with pytest.raises(oauth.SignInError):
        session.bearer()
    assert session.ended is None
    assert _refresh_token(storage) == "refresh-1"
    assert session.bearer() == "access-2"


def test_an_unwritable_token_file_does_not_lose_the_rotated_tokens(storage, monkeypatch):
    stale = _tokens(expires_at=time.time() + 10)
    fresh = _tokens(access_token="access-2", refresh_token="refresh-2")
    session = _session(storage, stale, _Refresh(fresh))
    real_write = oauth._write_record
    failures = [OSError("disk full")]

    def flaky_write(path, record):
        if failures:
            raise failures.pop()
        real_write(path, record)

    monkeypatch.setattr(oauth, "_write_record", flaky_write)
    assert session.bearer() == "access-2"
    # The store took the new token before the file failed; the file still names it.
    assert _refresh_token(storage) == ("refresh-2" if storage.keychain else "refresh-1")
    assert session.bearer() == "access-2"
    assert _refresh_token(storage) == "refresh-2"


def test_sign_out_ends_the_session_and_deletes_what_was_saved(storage):
    session = _session(storage, _tokens(), _Refresh())
    thread = session.sign_out()
    if thread is not None:
        thread.join(5)
    assert session.ended == "Signed out"
    assert not storage.path.exists()
    if storage.keychain is not None:
        assert storage.keychain.entries == {}
    with pytest.raises(oauth.SignedOut):
        session.bearer()


def test_a_refresh_token_spent_first_by_another_process_adopts_its_rotation(storage):
    stale = _tokens(expires_at=time.time() + 10)
    calls = []

    def racing_refresh(app, tokens):
        calls.append(tokens.refresh_token)
        if tokens.refresh_token == "refresh-1":
            # The other Blender's rotation lands between this process's read and its request.
            storage.save(_tokens(refresh_token="refresh-2"), storage.saved().slot)
            raise oauth.SignedOut("ended")
        return _tokens(access_token="access-3", refresh_token="refresh-3")

    session = _session(storage, stale, racing_refresh)
    assert session.bearer() == "access-3"
    assert session.ended is None
    assert calls == ["refresh-1", "refresh-2"]
    assert _refresh_token(storage) == "refresh-3"


def test_an_adopted_rotation_that_is_refused_too_ends_the_session(storage):
    stale = _tokens(expires_at=time.time() + 10)
    calls = []

    def refresh(app, tokens):
        calls.append(tokens.refresh_token)
        if tokens.refresh_token == "refresh-1":
            storage.save(_tokens(refresh_token="refresh-2"), storage.saved().slot)
        raise oauth.SignedOut("ended")

    session = _session(storage, stale, refresh)
    with pytest.raises(oauth.SignedOut):
        session.bearer()
    assert session.ended == "ended"
    assert storage.load() is None  # the adopted rotation was this session's too
    assert calls == ["refresh-1", "refresh-2"]


def test_a_refresh_never_rewrites_a_save_signed_out_or_replaced_from_another_process(storage):
    stale = _tokens(expires_at=time.time() + 10)
    fresh = _tokens(access_token="access-2", refresh_token="refresh-2")
    session = _session(storage, stale, _Refresh(fresh))
    thread = storage.clear()  # signed out from another Blender
    if thread is not None:
        thread.join(5)
    assert session.bearer() == "access-2"
    assert session.ended is None
    assert storage.load() is None
    session = _session(storage, stale, _Refresh(fresh))
    other = _tokens(subject="user_2", refresh_token="refresh-9")
    storage.save(other)  # another account signed in from another Blender
    assert session.bearer() == "access-2"
    assert session.ended is None
    saved = storage.load()
    assert (saved.tokens.account, saved.tokens.refresh_token) == (other.account, "refresh-9")
