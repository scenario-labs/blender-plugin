# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The computer's own credential store, for a secret kept between Blender sessions.

macOS Keychain through ``/usr/bin/security``, Windows Credential Manager through
advapi32, and the Secret Service of Linux desktops through ``secret-tool``: the
standard library has no client for any of them, and a bundled ``keyring`` would
bring dependencies the extension does not ship. A secret never appears in a
command line: it goes to ``security`` and ``secret-tool`` on standard input.

Every call can block, for instance while a locked keychain asks to be unlocked,
so callers run them on a worker, never on Blender's main thread or in a draw.
No bpy.
"""

import ctypes
import os
import re
import shutil
import subprocess
import sys

SERVICE = "Scenario for Blender"
TIMEOUT = 15.0
# Secrets are tokens: printable ASCII without spaces.
_SECRET = re.compile(r"[!-~]{1,4096}")
# Slots and service names reach a command line or a credential name.
_SLOT = re.compile(r"[A-Za-z0-9_-]{1,64}")
_SERVICE = re.compile(r"[A-Za-z0-9 ._-]{1,64}")


class KeychainError(RuntimeError):
    """The store did not answer or refused: nothing is known about the secret."""


def _checked(service, slot, secret=None):
    if not _SERVICE.fullmatch(service) or not _SLOT.fullmatch(slot):
        raise KeychainError("Invalid credential name")
    if secret is not None and not _SECRET.fullmatch(secret):
        raise KeychainError("Only a token can be stored")


def _child_environment(environ=None):
    """The launching environment without Scenario credentials or Python start-up."""
    environ = os.environ if environ is None else environ
    return {
        key: value
        for key, value in environ.items()
        if not key.upper().startswith(("SCENARIO_", "PYTHON"))
    }


class _Command:
    """A store reached through a command-line tool, one bounded process per call."""

    name = ""

    def __init__(self, service=SERVICE, *, run=subprocess.run, environ=None):
        self.service = service
        self._run = run
        self._environ = environ

    def _call(self, arguments, *, input=None):
        try:
            return self._run(
                arguments,
                input=input,
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
                env=_child_environment(self._environ),
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            raise KeychainError(f"{self.name} did not answer") from None


class MacKeychain(_Command):
    """The login keychain, through the system's ``security`` tool.

    The item is created by ``security`` itself, so reading it back through the
    same tool asks nothing of the user.
    """

    name = "the macOS Keychain"
    BINARY = "/usr/bin/security"
    _NOT_FOUND = 44

    def read(self, slot):
        _checked(self.service, slot)
        done = self._call(
            [self.BINARY, "find-generic-password", "-s", self.service, "-a", slot, "-w"]
        )
        if done.returncode == self._NOT_FOUND:
            return None
        if done.returncode != 0:
            raise KeychainError(f"{self.name} refused to read the sign-in")
        return done.stdout.rstrip("\n") or None

    def write(self, slot, secret):
        _checked(self.service, slot, secret)
        # ``-i`` reads the command from standard input; -X takes the secret as hex.
        command = (
            f'add-generic-password -U -s "{self.service}" -a "{slot}" -X {secret.encode().hex()}\n'
        )
        done = self._call([self.BINARY, "-i"], input=command)
        if done.returncode != 0:
            raise KeychainError(f"{self.name} refused to save the sign-in")

    def delete(self, slot):
        _checked(self.service, slot)
        done = self._call([self.BINARY, "delete-generic-password", "-s", self.service, "-a", slot])
        if done.returncode not in (0, self._NOT_FOUND):
            raise KeychainError(f"{self.name} refused to delete the sign-in")


class SecretService(_Command):
    """A Linux desktop's Secret Service (GNOME Keyring, KWallet), through ``secret-tool``."""

    name = "the system keyring"
    BINARY = "secret-tool"

    def _attributes(self, slot):
        return ["service", self.service, "account", slot]

    def read(self, slot):
        _checked(self.service, slot)
        done = self._call([self.BINARY, "lookup", *self._attributes(slot)])
        if done.returncode == 0:
            return done.stdout.rstrip("\n") or None
        if done.returncode == 1 and not done.stderr.strip():
            return None  # secret-tool says nothing when no item matches.
        raise KeychainError(f"{self.name} did not answer")

    def write(self, slot, secret):
        _checked(self.service, slot, secret)
        done = self._call(
            [self.BINARY, "store", "--label", self.service, *self._attributes(slot)],
            input=secret,
        )
        if done.returncode != 0:
            raise KeychainError(f"{self.name} refused to save the sign-in")

    def delete(self, slot):
        _checked(self.service, slot)
        done = self._call([self.BINARY, "clear", *self._attributes(slot)])
        if done.returncode != 0 and (done.returncode != 1 or done.stderr.strip()):
            raise KeychainError(f"{self.name} refused to delete the sign-in")


class _Credential(ctypes.Structure):
    """CREDENTIALW, with fixed-size integer types so the module loads on every system."""

    _fields_ = [
        ("Flags", ctypes.c_uint32),
        ("Type", ctypes.c_uint32),
        ("TargetName", ctypes.c_wchar_p),
        ("Comment", ctypes.c_wchar_p),
        ("LastWritten", ctypes.c_uint32 * 2),
        ("CredentialBlobSize", ctypes.c_uint32),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", ctypes.c_uint32),
        ("AttributeCount", ctypes.c_uint32),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", ctypes.c_wchar_p),
        ("UserName", ctypes.c_wchar_p),
    ]


class WindowsCredentials:
    """Windows Credential Manager, as a generic credential of the signed-in user."""

    name = "Windows Credential Manager"
    _GENERIC = 1
    _PERSIST_LOCAL_MACHINE = 2  # This user on this computer; not roamed to other machines.
    _NOT_FOUND = 1168
    _MAX_BLOB = 2560

    def __init__(self, service=SERVICE, *, advapi32=None, last_error=None):
        self.service = service
        self._api = advapi32
        self._last_error = last_error or getattr(ctypes, "get_last_error", lambda: 0)

    def _advapi32(self):
        if self._api is None:
            api = ctypes.WinDLL("advapi32", use_last_error=True)
            pointer = ctypes.POINTER(_Credential)
            api.CredWriteW.argtypes = [pointer, ctypes.c_uint32]
            api.CredWriteW.restype = ctypes.c_int
            api.CredReadW.argtypes = [
                ctypes.c_wchar_p,
                ctypes.c_uint32,
                ctypes.c_uint32,
                ctypes.POINTER(pointer),
            ]
            api.CredReadW.restype = ctypes.c_int
            api.CredDeleteW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
            api.CredDeleteW.restype = ctypes.c_int
            api.CredFree.argtypes = [ctypes.c_void_p]
            api.CredFree.restype = None
            self._api = api
        return self._api

    def _target(self, slot):
        _checked(self.service, slot)
        return f"{self.service}/{slot}"

    def read(self, slot):
        api = self._advapi32()
        found = ctypes.POINTER(_Credential)()
        if not api.CredReadW(self._target(slot), self._GENERIC, 0, ctypes.byref(found)):
            if self._last_error() == self._NOT_FOUND:
                return None
            raise KeychainError(f"{self.name} refused to read the sign-in")
        try:
            record = found.contents
            data = ctypes.string_at(record.CredentialBlob, record.CredentialBlobSize)
        finally:
            api.CredFree(found)
        try:
            return data.decode("ascii") or None
        except UnicodeDecodeError:
            return None

    def write(self, slot, secret):
        _checked(self.service, slot, secret)
        blob = secret.encode("ascii")
        if len(blob) > self._MAX_BLOB:
            raise KeychainError(f"The sign-in is too large for {self.name}")
        buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
        record = _Credential()
        record.Type = self._GENERIC
        record.TargetName = self._target(slot)
        record.CredentialBlobSize = len(blob)
        record.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
        record.Persist = self._PERSIST_LOCAL_MACHINE
        record.UserName = self.service
        if not self._advapi32().CredWriteW(ctypes.byref(record), 0):
            raise KeychainError(f"{self.name} refused to save the sign-in")

    def delete(self, slot):
        api = self._advapi32()
        if not api.CredDeleteW(self._target(slot), self._GENERIC, 0):
            if self._last_error() != self._NOT_FOUND:
                raise KeychainError(f"{self.name} refused to delete the sign-in")


def system_store(environ=None, platform=None, which=shutil.which):
    """This computer's credential store, or None to keep secrets in private files.

    None when ``SCENARIO_CREDENTIAL_STORE=file`` opts out (headless machines,
    CI, tests) or when the system has no supported store. Choosing a store only
    looks at the system; it reads or writes nothing.
    """
    environ = os.environ if environ is None else environ
    if (environ.get("SCENARIO_CREDENTIAL_STORE") or "").strip().lower() == "file":
        return None
    platform = sys.platform if platform is None else platform
    if platform == "darwin":
        return MacKeychain() if os.path.exists(MacKeychain.BINARY) else None
    if platform == "win32":
        return WindowsCredentials()
    if platform.startswith("linux") and which(SecretService.BINARY):
        return SecretService()
    return None
