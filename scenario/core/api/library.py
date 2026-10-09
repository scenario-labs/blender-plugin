# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Public asset metadata shared by native and MCP library projections."""


def asset_summary(row):
    """Expose reference metadata without signed URLs, previews or account records."""
    metadata = row.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    return {
        "asset_id": row["id"],
        "name": row.get("name", ""),
        "description": row.get("description", ""),
        "mime_type": row.get("mimeType", ""),
        "type": metadata.get("type", ""),
        "tags": row.get("tags", []),
        "collection_ids": row.get("collectionIds", []),
    }
