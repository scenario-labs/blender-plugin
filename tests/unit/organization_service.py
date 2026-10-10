# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Stateful offline collection and tag service behind httpx.MockTransport.

It implements only the SDK 2.2.0 wire forms the adapter uses. Scripted faults
let tests apply a change and then lose the response, refuse it, or acknowledge
it without applying it, so verification by reading back can be exercised.

Adds follow the service behavior observed by the hosted Scenario MCP: an add
is one transaction, refused as a whole with HTTP 400 when any asset is already
a member or when it names more than 49 assets, and then writes nothing.
"""

import json
import threading

import httpx

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter

URL = "https://service.example.invalid/v1"
PRIVATE = "private-service-text"
ALREADY_MEMBERS = "One or more assets are already part of the collection"
TOO_MANY = "You can not add more than 49 assets at once."


def asset(identifier, *, name=None, tags=(), collections=()):
    return {
        "id": identifier,
        "name": name or identifier.title(),
        "tags": list(tags),
        "collectionIds": list(collections),
        "url": "https://cdn.example.invalid/private-download?signature=secret",
        "ownerId": "private-owner",
    }


def collection(identifier, name):
    return {
        "id": identifier,
        "name": name,
        "assetCount": 0,
        "itemCount": 0,
        "modelCount": 0,
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:00:00Z",
        "ownerId": "private-owner",
        "thumbnail": {"assetId": "x", "url": "https://cdn.example.invalid/private-thumb"},
    }


class OrganizationService:
    """Record every request; ``faults`` maps (method, path) to scripted behaviors.

    Behaviors are consumed in order: ``None`` behaves normally, an int status
    refuses without applying, ``"timeout"`` loses the request,
    ``"apply-timeout"`` applies then loses the response, ``"ack-only"``
    acknowledges without applying, ``"already-members"`` refuses an add with
    the already-member reason whatever the membership, and ``"rename"`` creates
    under another name.
    """

    def __init__(self, *, assets=(), collections=(), page_size=None):
        self.assets = {item["id"]: item for item in assets}
        self.collections = {item["id"]: item for item in collections}
        self.page_size = page_size
        self.requests = []
        self.faults = {}
        self.events = []
        self.created = 0
        self.lock = threading.Lock()
        self.gate = None

    @property
    def writes(self):
        return [
            (method, path, body)
            for method, path, body, _ in self.requests
            if (method, path) != ("POST", "/v1/assets/get-bulk") and method != "GET"
        ]

    def fault(self, method, path, *behaviors):
        self.faults.setdefault((method, path), []).extend(behaviors)

    def adapter(self, **options):
        settings = {
            "online": lambda: True,
            "base_url": URL,
            "account_id": "account",
            "project_id": "project",
            "transport": httpx.MockTransport(self),
        }
        settings.update(options)
        return SDKAdapter(Credentials("selected-key", "selected-secret"), **settings)

    def __call__(self, request):
        if self.gate is not None:
            self.gate(request)
        body = json.loads(request.content) if request.content else None
        method, path = request.method, request.url.path
        with self.lock:
            self.requests.append((method, path, body, dict(request.url.params)))
            self.events.append(f"{method} {path}")
            assert request.url.params.get("projectId") == "project"
            behaviors = self.faults.get((method, path))
            behavior = behaviors.pop(0) if behaviors else None
        if isinstance(behavior, int):
            return httpx.Response(behavior, json={"message": PRIVATE})
        if behavior == "timeout":
            raise httpx.ReadTimeout(PRIVATE, request=request)
        if behavior == "already-members":
            return self.refuse(ALREADY_MEMBERS)
        response = self.route(method, path, body, request, behavior)
        if behavior == "apply-timeout":
            raise httpx.ReadTimeout(PRIVATE, request=request)
        return response

    def route(self, method, path, body, request, behavior):
        parts = path.removeprefix("/v1/").split("/")
        apply = behavior != "ack-only"
        if parts == ["collections"] and method == "GET":
            return self.page(request)
        if parts == ["collections"] and method == "POST":
            self.created += 1
            name = body["name"].lower() if behavior == "rename" else body["name"]
            record = collection(f"created-{self.created}", name)
            if apply:
                self.collections[record["id"]] = record
            return httpx.Response(200, json={"collection": record})
        if len(parts) == 2 and parts[0] == "collections" and method == "GET":
            record = self.collections.get(parts[1])
            if record is None:
                return httpx.Response(404, json={"message": PRIVATE})
            return httpx.Response(200, json={"collection": record})
        if len(parts) == 3 and parts[0] == "collections" and parts[2] == "assets":
            record = self.collections.get(parts[1])
            if record is None:
                return httpx.Response(404, json={"message": PRIVATE})
            if method == "PUT" and apply:
                if len(body["assetIds"]) > 49:
                    return self.refuse(TOO_MANY)
                if any(
                    parts[1] in self.assets.get(identifier, {}).get("collectionIds", ())
                    for identifier in body["assetIds"]
                ):
                    return self.refuse(ALREADY_MEMBERS)
            for identifier in body["assetIds"]:
                item = self.assets.get(identifier)
                if item is None or not apply:
                    continue
                members = item["collectionIds"]
                if method == "PUT" and parts[1] not in members:
                    members.append(parts[1])
                elif method == "DELETE" and parts[1] in members:
                    members.remove(parts[1])
            return httpx.Response(200, json={"collection": record})
        if len(parts) == 3 and parts[0] == "assets" and parts[2] == "tags":
            item = self.assets.get(parts[1])
            if item is None:
                return httpx.Response(404, json={"message": PRIVATE})
            assert body["strict"] is False
            added = [tag for tag in body.get("add", []) if tag not in item["tags"]]
            deleted = [tag for tag in body.get("delete", []) if tag in item["tags"]]
            if apply:
                item["tags"] = [tag for tag in item["tags"] if tag not in deleted] + added
            return httpx.Response(200, json={"added": added, "deleted": deleted})
        if parts == ["assets", "get-bulk"] and method == "POST":
            records = [self.assets[i] for i in body["assetIds"] if i in self.assets]
            return httpx.Response(200, json={"assets": json.loads(json.dumps(records))})
        raise AssertionError(f"Unexpected request {method} {path}")

    @staticmethod
    def refuse(reason):
        return httpx.Response(400, json={"reason": reason, "detail": PRIVATE})

    def page(self, request):
        size = int(request.url.params.get("pageSize", 10))
        if self.page_size is not None:
            size = min(size, self.page_size)
        start = int(request.url.params.get("paginationToken", "0"))
        records = list(self.collections.values())
        page = {"collections": records[start : start + size]}
        if start + size < len(records):
            page["nextPaginationToken"] = str(start + size)
        return httpx.Response(200, json=page)
