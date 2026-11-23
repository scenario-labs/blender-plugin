# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The OS credential stores: what reaches each tool, and what its answers mean."""

import ctypes
import os
import secrets
import subprocess
import sys

import pytest

from scenario.core import keychain

TOKEN = "rt_Fixture.Token-123~/+="
SLOT = "0123456789abcdef"


class _Run:
    """A fake subprocess.run: records each call and answers from a queue."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = []

    def __call__(self, arguments, **options):
        self.calls.append((arguments, options))
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        code, stdout, stderr = answer
        return subprocess.CompletedProcess(arguments, code, stdout, stderr)


def test_the_mac_keychain_takes_the_secret_on_stdin_as_hex_never_in_argv():
    run = _Run((0, "", ""))
    keychain.MacKeychain(run=run, environ={"SCENARIO_API_SECRET": "s", "HOME": "/h"}).write(
        SLOT, TOKEN
    )
    ((arguments, options),) = run.calls
    assert arguments == ["/usr/bin/security", "-i"]
    assert TOKEN not in " ".join(arguments)
    assert options["input"] == (
        f'add-generic-password -U -s "Scenario for Blender" -a "{SLOT}" -X {TOKEN.encode().hex()}\n'
    )
    assert TOKEN not in options["input"]
    assert options["env"] == {"HOME": "/h"}
    assert options["timeout"] == keychain.TIMEOUT


def test_the_mac_keychain_reads_finds_nothing_and_fails_distinctly():
    run = _Run((0, f"{TOKEN}\n", ""), (44, "", "could not be found"), (51, "", "denied"))
    store = keychain.MacKeychain(run=run)
    assert store.read(SLOT) == TOKEN
    assert run.calls[0][0] == [
        "/usr/bin/security",
        "find-generic-password",
        "-s",
        "Scenario for Blender",
        "-a",
        SLOT,
        "-w",
    ]
    assert store.read(SLOT) is None
    with pytest.raises(keychain.KeychainError):
        store.read(SLOT)


def test_the_mac_keychain_deletes_an_absent_item_quietly():
    run = _Run((0, "", ""), (44, "", ""), (1, "", "denied"))
    store = keychain.MacKeychain(run=run)
    store.delete(SLOT)
    store.delete(SLOT)
    with pytest.raises(keychain.KeychainError):
        store.delete(SLOT)


@pytest.mark.parametrize(
    "failure", [OSError("no tool"), subprocess.TimeoutExpired("security", keychain.TIMEOUT)]
)
def test_a_tool_that_does_not_answer_is_a_keychain_error(failure):
    for store in (
        keychain.MacKeychain(run=_Run(failure)),
        keychain.SecretService(run=_Run(failure)),
    ):
        with pytest.raises(keychain.KeychainError):
            store.read(SLOT)


@pytest.mark.parametrize("slot", ['a" -w "x', "a b", "", "x" * 65])
def test_a_slot_that_could_change_the_command_is_refused_before_any_call(slot):
    run = _Run()
    with pytest.raises(keychain.KeychainError):
        keychain.MacKeychain(run=run).write(slot, TOKEN)
    assert run.calls == []


@pytest.mark.parametrize("secret", ["two words", "line\nbreak", "", "é"])
def test_only_a_token_is_stored(secret):
    run = _Run()
    with pytest.raises(keychain.KeychainError):
        keychain.SecretService(run=run).write(SLOT, secret)
    assert run.calls == []


def test_secret_tool_takes_the_secret_on_stdin_and_reads_it_back():
    run = _Run((0, "", ""), (0, TOKEN, ""), (1, "", ""), (1, "", "Cannot autolaunch D-Bus"))
    store = keychain.SecretService(run=run)
    store.write(SLOT, TOKEN)
    arguments, options = run.calls[0]
    assert arguments == [
        "secret-tool",
        "store",
        "--label",
        "Scenario for Blender",
        "service",
        "Scenario for Blender",
        "account",
        SLOT,
    ]
    assert options["input"] == TOKEN
    assert store.read(SLOT) == TOKEN
    assert store.read(SLOT) is None  # no item: exit 1 without a word
    with pytest.raises(keychain.KeychainError):
        store.read(SLOT)  # no Secret Service at all


def test_secret_tool_clears_an_absent_item_quietly():
    run = _Run((0, "", ""), (1, "", ""), (1, "", "Cannot autolaunch D-Bus"))
    store = keychain.SecretService(run=run)
    store.delete(SLOT)
    store.delete(SLOT)
    with pytest.raises(keychain.KeychainError):
        store.delete(SLOT)
    assert run.calls[0][0] == [
        "secret-tool",
        "clear",
        "service",
        "Scenario for Blender",
        "account",
        SLOT,
    ]


class _Advapi32:
    """advapi32's credential functions over a dictionary, through the same ctypes records."""

    def __init__(self):
        self.saved = {}
        self.error = 0
        self.freed = []
        self.refuse = False
        self._kept = []

    def CredWriteW(self, reference, flags):
        record = reference._obj
        if self.refuse:
            self.error = 5
            return 0
        self.saved[record.TargetName] = {
            "type": record.Type,
            "persist": record.Persist,
            "user": record.UserName,
            "blob": ctypes.string_at(record.CredentialBlob, record.CredentialBlobSize),
        }
        return 1

    def CredReadW(self, target, kind, flags, reference):
        if self.refuse:
            self.error = 5
            return 0
        if target not in self.saved:
            self.error = 1168
            return 0
        blob = self.saved[target]["blob"]
        buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
        record = keychain._Credential()
        record.CredentialBlobSize = len(blob)
        record.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
        self._kept += [buffer, record]
        reference._obj.contents = record
        return 1

    def CredDeleteW(self, target, kind, flags):
        if self.refuse:
            self.error = 5
            return 0
        if self.saved.pop(target, None) is None:
            self.error = 1168
            return 0
        return 1

    def CredFree(self, pointer):
        self.freed.append(pointer)


def test_windows_credentials_round_trip_as_a_local_generic_credential():
    api = _Advapi32()
    store = keychain.WindowsCredentials(advapi32=api, last_error=lambda: api.error)
    store.write(SLOT, TOKEN)
    assert api.saved == {
        f"Scenario for Blender/{SLOT}": {
            "type": 1,
            "persist": 2,
            "user": "Scenario for Blender",
            "blob": TOKEN.encode(),
        }
    }
    assert store.read(SLOT) == TOKEN
    assert len(api.freed) == 1
    store.delete(SLOT)
    assert store.read(SLOT) is None
    store.delete(SLOT)  # already gone


def test_windows_credentials_refusals_and_size_limit_are_keychain_errors():
    api = _Advapi32()
    store = keychain.WindowsCredentials(advapi32=api, last_error=lambda: api.error)
    with pytest.raises(keychain.KeychainError):
        store.write(SLOT, "x" * 2561)
    assert api.saved == {}
    api.refuse = True
    for call in (
        lambda: store.write(SLOT, TOKEN),
        lambda: store.read(SLOT),
        lambda: store.delete(SLOT),
    ):
        with pytest.raises(keychain.KeychainError):
            call()


def test_the_store_follows_the_system_and_the_opt_out():
    def which(name):
        return f"/usr/bin/{name}"

    def nothing(name):
        return None

    assert isinstance(keychain.system_store({}, "win32"), keychain.WindowsCredentials)
    assert isinstance(keychain.system_store({}, "linux", which), keychain.SecretService)
    assert keychain.system_store({}, "linux", nothing) is None
    assert keychain.system_store({}, "freebsd14", which) is None
    for opt_out in ("file", " FILE "):
        for platform in ("darwin", "win32", "linux"):
            store = keychain.system_store({"SCENARIO_CREDENTIAL_STORE": opt_out}, platform, which)
            assert store is None
    mac = keychain.system_store({}, "darwin")
    assert isinstance(mac, keychain.MacKeychain) == os.path.exists("/usr/bin/security")


@pytest.mark.skipif(
    os.environ.get("SCENARIO_TEST_KEYCHAIN") != "1",
    reason="writes one temporary item to this computer's credential store",
)
def test_this_computers_store_round_trip():
    store = keychain.system_store({}, sys.platform)
    if store is None:
        pytest.skip("no supported credential store on this system")
    store.service = "Scenario for Blender tests"
    slot = secrets.token_hex(16)
    try:
        assert store.read(slot) is None
        store.write(slot, TOKEN)
        assert store.read(slot) == TOKEN
        store.write(slot, TOKEN + "2")
        assert store.read(slot) == TOKEN + "2"
    finally:
        store.delete(slot)
    assert store.read(slot) is None
