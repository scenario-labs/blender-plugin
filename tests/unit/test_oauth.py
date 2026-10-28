# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Browser sign-in protocol: PKCE, the loopback listener, the token file and refresh."""

import base64
import hashlib
import io
import json
import os
import stat
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest

from scenario.core.api import oauth

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


def test_production_application_is_the_default_and_ships_without_a_client_id():
    app = oauth.selected_app({})
    assert app is oauth.PRODUCTION_APP
    assert not app.configured
    assert app.issuer == "https://clerk.scenario.com"


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
    with pytest.raises(oauth.SignInError, match="not available"):
        oauth.SignInAttempt(oauth.PRODUCTION_APP)
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


# --- token file ---------------------------------------------------------------


def test_token_file_round_trip_is_private_and_atomic(tmp_path):
    path = tmp_path / "sign-in.json"
    tokens = _tokens()
    oauth.save_tokens(path, tokens)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert [p.name for p in tmp_path.iterdir()] == ["sign-in.json"]
    assert oauth.load_tokens(path) == tokens
    oauth.save_tokens(path, _tokens(access_token="access-2"))
    assert oauth.load_tokens(path).access_token == "access-2"
    oauth.clear_tokens(path)
    oauth.clear_tokens(path)
    assert oauth.load_tokens(path) is None


@pytest.mark.parametrize(
    "content", [b"", b"[]", b'{"format": "other"}', b'{"format": "x", "a": 1}']
)
def test_unreadable_or_foreign_token_files_are_ignored(tmp_path, content):
    path = tmp_path / "sign-in.json"
    path.write_bytes(content)
    assert oauth.load_tokens(path) is None


@pytest.mark.skipif(os.name == "nt", reason="symlinks need privileges on Windows")
def test_a_symlinked_token_file_is_never_read(tmp_path):
    real = tmp_path / "real.json"
    oauth.save_tokens(real, _tokens())
    link = tmp_path / "sign-in.json"
    link.symlink_to(real)
    assert oauth.load_tokens(link) is None


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


def test_session_refreshes_an_expiring_token_once_and_saves_it(tmp_path):
    path = tmp_path / "sign-in.json"
    stale = _tokens(expires_at=time.time() + 10)
    oauth.save_tokens(path, stale)
    fresh = _tokens(access_token="access-2", refresh_token="refresh-2")
    refresh = _Refresh(fresh)
    session = oauth.TokenSession(APP, stale, path, refresh=refresh)
    assert session.peek() == "access-1"
    assert session.account == stale.account
    assert session.bearer() == "access-2"
    assert session.bearer() == "access-2"
    assert refresh.calls == ["refresh-1"]
    assert oauth.load_tokens(path).refresh_token == "refresh-2"
    assert session.peek() == "access-2"


def test_session_serializes_concurrent_refreshes(tmp_path):
    path = tmp_path / "sign-in.json"
    stale = _tokens(expires_at=time.time() + 10)
    oauth.save_tokens(path, stale)
    gate = threading.Event()

    calls = []

    def slow_refresh(app, tokens):
        calls.append(tokens.refresh_token)
        gate.wait(5)
        return _tokens(access_token="access-2", refresh_token="refresh-2")

    session = oauth.TokenSession(APP, stale, path, refresh=slow_refresh)
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


def test_a_refused_refresh_ends_the_session_and_clears_only_its_own_file(tmp_path):
    path = tmp_path / "sign-in.json"
    stale = _tokens(expires_at=time.time() + 10)
    oauth.save_tokens(path, stale)
    session = oauth.TokenSession(APP, stale, path, refresh=_Refresh(oauth.SignedOut("ended")))
    with pytest.raises(oauth.SignedOut):
        session.bearer()
    assert session.ended == "ended"
    assert oauth.load_tokens(path) is None
    with pytest.raises(oauth.SignedOut):
        session.bearer()
    # Another process already rotated the file: its tokens survive this failure.
    other = _tokens(access_token="access-9", refresh_token="refresh-9")
    oauth.save_tokens(path, other)
    session = oauth.TokenSession(
        APP,
        _tokens(expires_at=time.time() + 10, refresh_token="old"),
        path,
        refresh=_Refresh(oauth.SignedOut("ended")),
    )
    # The other process's tokens are adopted first, so no refresh is spent at all.
    assert session.bearer() == "access-9"
    assert oauth.load_tokens(path) == other


def test_a_transient_refresh_failure_keeps_the_session(tmp_path):
    path = tmp_path / "sign-in.json"
    stale = _tokens(expires_at=time.time() + 10)
    oauth.save_tokens(path, stale)
    fresh = _tokens(access_token="access-2", refresh_token="refresh-2")
    session = oauth.TokenSession(
        APP, stale, path, refresh=_Refresh(oauth.SignInError("HTTP 502"), fresh)
    )
    with pytest.raises(oauth.SignInError):
        session.bearer()
    assert session.ended is None
    assert oauth.load_tokens(path) == stale
    assert session.bearer() == "access-2"


def test_an_unwritable_token_file_does_not_lose_the_rotated_tokens(tmp_path, monkeypatch):
    path = tmp_path / "sign-in.json"
    stale = _tokens(expires_at=time.time() + 10)
    oauth.save_tokens(path, stale)
    fresh = _tokens(access_token="access-2", refresh_token="refresh-2")
    session = oauth.TokenSession(APP, stale, path, refresh=_Refresh(fresh))
    real_save = oauth.save_tokens
    failures = [OSError("disk full")]

    def flaky_save(target, tokens):
        if failures:
            raise failures.pop()
        real_save(target, tokens)

    monkeypatch.setattr(oauth, "save_tokens", flaky_save)
    assert session.bearer() == "access-2"
    assert oauth.load_tokens(path) == stale
    assert session.bearer() == "access-2"
    assert oauth.load_tokens(path) == fresh


def test_sign_out_ends_the_session_and_deletes_the_file(tmp_path):
    path = tmp_path / "sign-in.json"
    oauth.save_tokens(path, _tokens())
    session = oauth.TokenSession(APP, _tokens(), path, refresh=_Refresh())
    session.sign_out()
    assert session.ended == "Signed out"
    assert oauth.load_tokens(path) is None
    with pytest.raises(oauth.SignedOut):
        session.bearer()
