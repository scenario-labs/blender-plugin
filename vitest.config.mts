// SPDX-FileCopyrightText: 2026 Scenario Inc.
// SPDX-License-Identifier: GPL-3.0-or-later
// Vitest runs only the property-based (fuzz) tests; the other site tests use node:test.
import { defineConfig } from "vitest/config";

export default defineConfig({ test: { include: ["tests/site/**/*.fuzz.ts"] } });
