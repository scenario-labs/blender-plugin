# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Browser sign-in: Authorization Code with PKCE against Scenario's identity provider.

This is the desktop authorization protocol of scenario-labs/roadmap#692, not a
Scenario service operation: the SDK has no client for it, so the token endpoint
is called with the standard library. Nothing here touches bpy or the network
of the SDK adapter. Tokens are kept in a private file under the extension's
state directory and are never logged.
"""

import base64
import contextlib
import hashlib
import hmac
import http.server
import json
import os
import secrets
import ssl
import stat
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from .user_agent import user_agent_string

# The ports registered with the Scenario for Blender OAuth application.
LOOPBACK_PORTS = (9877, 9878, 9879)
CALLBACK_PATH = "/callback"
SCOPES = "profile email offline_access"
# A browser sign-in that nobody completes stops listening after this long.
SIGN_IN_TIMEOUT = 300.0
# A token this close to its expiry is refreshed before it is used.
REFRESH_MARGIN = 60.0
TOKEN_TIMEOUT = 30.0
_TOKEN_FILE_HEADER = "scenario-browser-sign-in-v1"


class SignInError(RuntimeError):
    """A browser sign-in or refresh that did not produce usable tokens."""


class SignedOut(SignInError):
    """The saved session cannot be refreshed: the user has to sign in again."""


@dataclass(frozen=True)
class OAuthApp:
    """One public OAuth application: identity provider base URL and its client id."""

    issuer: str
    client_id: str
    service: str

    @property
    def configured(self):
        return bool(self.issuer and self.client_id and self.service)

    def authorize_url(self, *, redirect_uri, state, challenge):
        query = urllib.parse.urlencode(
            {
                "response_type": "code",
                "client_id": self.client_id,
                "redirect_uri": redirect_uri,
                "scope": SCOPES,
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        return f"{self.issuer}/oauth/authorize?{query}"

    @property
    def token_url(self):
        return f"{self.issuer}/oauth/token"


# The production application. The client id is public: it travels in every
# authorize URL. A build without one (a developer override that is not
# complete) shows the browser sign-in as unavailable.
PRODUCTION_APP = OAuthApp(
    issuer="https://clerk.scenario.com",
    client_id="gUzfnnOTmz5SqATM",
    service="https://api.cloud.scenario.com/v1",
)


def _https_origin(value):
    parts = urllib.parse.urlsplit(value or "")
    return (
        parts.scheme == "https"
        and bool(parts.hostname)
        and not parts.username
        and not parts.password
        and not parts.query
        and not parts.fragment
    )


def selected_app(environ=None):
    """The production application, or the developer override when all of it is set.

    The override selects a development identity provider, application and API
    together, so a token is only ever sent to the API it was issued for.
    """
    environ = os.environ if environ is None else environ
    issuer = (environ.get("SCENARIO_OAUTH_ISSUER") or "").strip().rstrip("/")
    client_id = (environ.get("SCENARIO_OAUTH_CLIENT_ID") or "").strip()
    service = (environ.get("SCENARIO_API_BASE") or "").strip().rstrip("/")
    if not (issuer or client_id or service):
        return PRODUCTION_APP
    if not (issuer and client_id and service) or not (
        _https_origin(issuer) and _https_origin(service)
    ):
        raise SignInError(
            "Set SCENARIO_OAUTH_ISSUER, SCENARIO_OAUTH_CLIENT_ID and SCENARIO_API_BASE together,"
            " as https URLs"
        )
    return OAuthApp(issuer=issuer, client_id=client_id, service=service)


def _b64url(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _claims(token):
    """The unverified payload of a JWT; the API verifies the signature, not the client."""
    try:
        payload = token.split(".")[1]
        decoded = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        claims = json.loads(decoded)
    except (IndexError, ValueError, UnicodeDecodeError):
        return {}
    return claims if isinstance(claims, dict) else {}


@dataclass(frozen=True)
class TokenSet:
    """The tokens of one signed-in account on one application."""

    issuer: str
    client_id: str
    service: str
    subject: str
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    expires_at: float

    @property
    def account(self):
        """A stable local identity for the account; not the API's own account id."""
        return f"{self.issuer}#{self.subject}"

    def expiring(self, now=None):
        now = time.time() if now is None else now
        return now >= self.expires_at - REFRESH_MARGIN

    def matches(self, app):
        return (self.issuer, self.client_id, self.service) == (
            app.issuer,
            app.client_id,
            app.service,
        )


def _parse_tokens(app, body, *, previous=None):
    try:
        data = json.loads(body)
    except ValueError:
        raise SignInError("The sign-in service sent an unreadable reply") from None
    if not isinstance(data, dict):
        raise SignInError("The sign-in service sent an unreadable reply")
    access = data.get("access_token")
    refresh = data.get("refresh_token") or (previous.refresh_token if previous else "")
    expires_in = data.get("expires_in")
    if not isinstance(access, str) or not access or not isinstance(refresh, str) or not refresh:
        raise SignInError("The sign-in service sent no tokens")
    if not isinstance(expires_in, (int, float)) or isinstance(expires_in, bool):
        expires_in = 3600
    subject = _claims(access).get("sub")
    if not isinstance(subject, str) or not subject:
        raise SignInError("The sign-in service sent a token without an account")
    return TokenSet(
        issuer=app.issuer,
        client_id=app.client_id,
        service=app.service,
        subject=subject,
        access_token=access,
        refresh_token=refresh,
        expires_at=time.time() + float(expires_in),
    )


def _tls_context():
    """Verify the identity provider with the bundled certifi roots, as the SDK's httpx does.

    Blender's Python ships no system trust store on every platform, so the
    default context can fail to verify a valid certificate.
    """
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def _opener():
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=_tls_context())
    )


def _post_form(url, fields, *, opener=None, timeout=TOKEN_TIMEOUT):
    """POST one form to the identity provider, bypassing proxy environment variables."""
    opener = opener or _opener()
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(fields).encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": user_agent_string(),
        },
        method="POST",
    )
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except (OSError, ValueError) as error:
        raise SignInError("Could not reach the sign-in service") from error


def _error_code(body):
    try:
        data = json.loads(body)
    except ValueError:
        return ""
    code = data.get("error") if isinstance(data, dict) else None
    return code if isinstance(code, str) else ""


def exchange_code(app, code, *, verifier, redirect_uri, opener=None):
    """Swap the authorization code for tokens; no client secret is involved (PKCE)."""
    status, body = _post_form(
        app.token_url,
        {
            "grant_type": "authorization_code",
            "client_id": app.client_id,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        },
        opener=opener,
    )
    if status != 200:
        raise SignInError(f"The sign-in service refused the authorization code (HTTP {status})")
    return _parse_tokens(app, body)


def refresh_tokens(app, tokens, *, opener=None):
    """Use the refresh token once; the provider rotates it, so the result replaces it."""
    status, body = _post_form(
        app.token_url,
        {
            "grant_type": "refresh_token",
            "client_id": app.client_id,
            "refresh_token": tokens.refresh_token,
        },
        opener=opener,
    )
    if status == 200:
        return _parse_tokens(app, body, previous=tokens)
    # Only the provider's own verdict ends the session (RFC 6749, 5.2). A proxy
    # page or a truncated reply is a failed attempt, and the saved session stays.
    if status in (400, 401) and _error_code(body) == "invalid_grant":
        raise SignedOut("The Scenario session has ended; sign in again")
    raise SignInError(f"Could not refresh the Scenario session (HTTP {status})")


@dataclass(frozen=True)
class Challenge:
    verifier: str = field(repr=False)
    challenge: str
    state: str


def new_challenge():
    verifier = _b64url(secrets.token_bytes(64))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    return Challenge(verifier=verifier, challenge=challenge, state=_b64url(secrets.token_bytes(24)))


_DONE_PAGE = (
    "<!doctype html><meta charset='utf-8'><title>Scenario for Blender</title>"
    "<body style='font-family:system-ui;margin:3em'><h1>Signed in</h1>"
    "<p>You can close this tab and return to Blender.</p></body>"
)
_FAILED_PAGE = (
    "<!doctype html><meta charset='utf-8'><title>Scenario for Blender</title>"
    "<body style='font-family:system-ui;margin:3em'><h1>Sign-in not completed</h1>"
    "<p>Return to Blender and start the sign-in again.</p></body>"
)


class _CallbackServer(http.server.HTTPServer):
    # On Windows SO_REUSEADDR lets a second listener bind a port that is already
    # in use, so a callback could reach the wrong Blender; the next port is free.
    allow_reuse_address = False


class LoopbackServer:
    """One-shot callback listener on 127.0.0.1, bound to one sign-in's state.

    It accepts the first request matching the callback path and state, records
    the code or the provider's error, answers the browser, and ignores anything
    else. The caller owns its lifetime: ``wait`` returns the code or raises, and
    ``close`` stops listening whether or not a callback arrived.
    """

    def __init__(self, state, *, ports=LOOPBACK_PORTS):
        self._state = state
        self._result = None
        self._done = threading.Event()
        self._server = None
        for port in ports:
            try:
                self._server = _CallbackServer(("127.0.0.1", port), self._handler())
            except OSError:
                continue
            break
        if self._server is None:
            raise SignInError("Ports 9877 to 9879 on this computer are all in use")
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="ScenarioSignIn", daemon=True
        )
        self._thread.start()

    @property
    def redirect_uri(self):
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}{CALLBACK_PATH}"

    def _handler(self):
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                parts = urllib.parse.urlsplit(self.path)
                query = urllib.parse.parse_qs(parts.query)
                if parts.path != CALLBACK_PATH or owner._done.is_set():
                    self.send_error(404)
                    return
                state = query.get("state", [""])[0]
                code = query.get("code", [""])[0]
                error = query.get("error", [""])[0]
                if not hmac.compare_digest(state.encode(), owner._state.encode()):
                    self.send_error(400)
                    return
                if code and not error:
                    owner._finish(code, None)
                    self._page(_DONE_PAGE)
                else:
                    owner._finish(None, error or "invalid_request")
                    self._page(_FAILED_PAGE)

            def _page(self, body):
                encoded = body.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(encoded)

        return Handler

    def _finish(self, code, error):
        if not self._done.is_set():
            self._result = (code, error)
            self._done.set()

    def wait(self, timeout=SIGN_IN_TIMEOUT, cancelled=None):
        """The authorization code, or SignInError on denial, timeout or cancellation."""
        deadline = time.monotonic() + timeout
        while not self._done.wait(0.25):
            if cancelled is not None and cancelled.is_set():
                raise SignInError("Sign-in cancelled")
            if time.monotonic() >= deadline:
                raise SignInError("The browser did not complete the sign-in in time")
        code, error = self._result
        if error == "access_denied":
            raise SignInError("Access was denied in the browser")
        if error:
            raise SignInError("The browser returned an invalid sign-in response")
        return code

    def close(self):
        server, self._server = self._server, None
        if server is None:
            return
        server.shutdown()
        server.server_close()
        self._thread.join(timeout=2)


def _private_open(path, flags, mode=0o600):
    return os.open(path, flags | getattr(os, "O_NOFOLLOW", 0), mode)


def load_tokens(path):
    """The saved session, or None when there is none or the file is not ours."""
    path = os.fspath(path)
    if not os.path.lexists(path) or os.path.islink(path):
        return None
    try:
        with os.fdopen(_private_open(path, os.O_RDONLY), "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                return None
            data = json.loads(source.read())
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("format") != _TOKEN_FILE_HEADER:
        return None
    try:
        return TokenSet(
            issuer=str(data["issuer"]),
            client_id=str(data["client_id"]),
            service=str(data["service"]),
            subject=str(data["subject"]),
            access_token=str(data["access_token"]),
            refresh_token=str(data["refresh_token"]),
            expires_at=float(data["expires_at"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def save_tokens(path, tokens):
    """Publish the session atomically as a private file, replacing the previous one."""
    path = os.fspath(path)
    directory = os.path.dirname(path) or "."
    payload = json.dumps(
        {
            "format": _TOKEN_FILE_HEADER,
            "issuer": tokens.issuer,
            "client_id": tokens.client_id,
            "service": tokens.service,
            "subject": tokens.subject,
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expires_at": tokens.expires_at,
        },
        separators=(",", ":"),
    ).encode()
    descriptor, temporary = tempfile.mkstemp(prefix=".sign-in-", dir=directory)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.lexists(temporary):
            os.unlink(temporary)


def clear_tokens(path):
    with contextlib.suppress(FileNotFoundError):
        os.unlink(os.fspath(path))


class TokenSession:
    """The signed-in account's current access token, refreshed on demand.

    Workers call ``bearer`` before each request. One refresh runs at a time:
    a worker that finds another refresh in flight waits for its outcome instead
    of spending the same refresh token twice. Another Blender on the same
    account may rotate the refresh token first: the file is re-read before a
    refresh and its newer tokens adopted, and a refresh refused because that
    rotation landed in between adopts it afterwards. A refresh the provider
    refuses otherwise ends the session for every caller until the user signs in
    again. The file is rewritten only while it still holds this account: signed
    out or replaced from another Blender, it is left alone and this session
    lives on in memory.
    """

    def __init__(self, app, tokens, path, *, refresh=refresh_tokens):
        self._app = app
        self._tokens = tokens
        self._path = path
        self._refresh = refresh
        self._lock = threading.Lock()
        self._ended = None
        self._unsaved = False

    @property
    def account(self):
        return self._tokens.account

    @property
    def subject(self):
        return self._tokens.subject

    @property
    def app(self):
        return self._app

    @property
    def ended(self):
        """The reason the session ended, or None while it is usable."""
        return self._ended

    def peek(self):
        """The current access token without a refresh, for a client's construction.

        Lock-free on purpose: the lock is held across a refresh's network call,
        and this is read on Blender's main thread.
        """
        return self._tokens.access_token

    def _saved_for_this_account(self):
        """The file's tokens while it still belongs to this account, else None."""
        saved = load_tokens(self._path)
        if saved is None or saved.account != self._tokens.account or not saved.matches(self._app):
            return None
        return saved

    def _adopt_newer(self):
        """Take the tokens another process saved for this account, if any."""
        saved = self._saved_for_this_account()
        if saved is not None and saved.refresh_token != self._tokens.refresh_token:
            self._tokens = saved
            self._unsaved = False

    def _rotated(self):
        """This session's tokens after a refresh.

        A refusal right after another Blender rotated the same refresh token is
        that Blender's win, not the end of the account: its tokens are adopted
        and, when they are expiring too, refreshed in turn.
        """
        burned = self._tokens.refresh_token
        try:
            return self._refresh(self._app, self._tokens)
        except SignedOut:
            self._adopt_newer()
            if self._tokens.refresh_token == burned:
                raise
        if not self._tokens.expiring():
            return self._tokens
        return self._refresh(self._app, self._tokens)

    def _save(self):
        if self._saved_for_this_account() is None:
            # Signed out, or another account signed in, from another Blender:
            # never rewrite that; this session keeps its tokens in memory.
            self._unsaved = False
            return
        try:
            save_tokens(self._path, self._tokens)
        except OSError:
            # Keep the rotated tokens in memory and try again on the next call.
            self._unsaved = True
        else:
            self._unsaved = False

    def bearer(self):
        with self._lock:
            if self._ended is not None:
                raise SignedOut(self._ended)
            if self._unsaved:
                self._save()
            if self._tokens.expiring():
                self._adopt_newer()
            if self._tokens.expiring():
                try:
                    self._tokens = self._rotated()
                except SignedOut as error:
                    self._ended = str(error)
                    saved = load_tokens(self._path)
                    if saved is None or saved.refresh_token == self._tokens.refresh_token:
                        clear_tokens(self._path)
                    raise
                self._save()
            return self._tokens.access_token

    def sign_out(self):
        with self._lock:
            self._ended = "Signed out"
            clear_tokens(self._path)


class SignInAttempt:
    """One browser sign-in: a listening callback port and the URL to open.

    Construction opens the port and builds the URL where the browser is started
    (Blender's main thread, through the credential-free opener); ``complete``
    blocks and belongs on a worker.
    """

    def __init__(self, app):
        if not app.configured:
            raise SignInError("Browser sign-in is not available in this release yet")
        self._app = app
        self._challenge = new_challenge()
        self._server = LoopbackServer(self._challenge.state)
        self.redirect_uri = self._server.redirect_uri
        self.url = app.authorize_url(
            redirect_uri=self.redirect_uri,
            state=self._challenge.state,
            challenge=self._challenge.challenge,
        )

    def complete(self, *, cancelled=None, timeout=SIGN_IN_TIMEOUT, opener=None):
        """Wait for the browser, then swap the code for tokens. Closes the listener."""
        try:
            code = self._server.wait(timeout, cancelled)
        finally:
            self.close()
        if cancelled is not None and cancelled.is_set():
            raise SignInError("Sign-in cancelled")
        # The code is single-use and the listener is gone, so a late second
        # callback cannot start another exchange.
        return exchange_code(
            self._app,
            code,
            verifier=self._challenge.verifier,
            redirect_uri=self.redirect_uri,
            opener=opener,
        )

    def close(self):
        self._server.close()
