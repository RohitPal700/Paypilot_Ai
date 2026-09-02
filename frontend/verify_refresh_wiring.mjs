#!/usr/bin/env node
/**
 * Regression guard for the "PDF import -> dashboard analytics refresh" flow.
 *
 * There is no JS test runner (vitest/jest) configured in this project yet,
 * so a full component-render test isn't available without first adding a
 * whole new testing framework as a dependency -- out of scope for this fix.
 * Instead, this script statically verifies the exact wiring that makes the
 * refresh flow work, so if any of these four links get silently broken
 * again in the future (e.g. someone removes a prop or a deps array while
 * refactoring), this fails loudly instead of the dashboard quietly going
 * stale again the way it did before this fix.
 *
 * Checks:
 *   1. UploadStatement calls onImportSuccess(...) after a successful import
 *   2. Dashboard bumps a refreshKey state value in that success handler
 *   3. Dashboard passes refreshKey down to all four analytics panels
 *   4. Each of the four panels actually consumes refreshKey and passes it
 *      into useFetchOnMount's deps array (this is the exact bug that was
 *      fixed: Dashboard already did 1-3, but the panels silently ignored
 *      the prop, so no refetch was ever triggered)
 *
 * Run with: node verify_refresh_wiring.mjs
 * Exits non-zero (and prints which check failed) if anything regresses.
 */

import { readFileSync } from "fs";
import { join } from "path";

const SRC = join(process.cwd(), "src");

function read(relativePath) {
  return readFileSync(join(SRC, relativePath), "utf-8");
}

let failures = [];

function check(description, condition) {
  if (!condition) failures.push(description);
}

// --- 1. UploadStatement notifies its parent on success ---
const uploadStatement = read("components/UploadStatement.jsx");
check(
  "UploadStatement.jsx calls onImportSuccess(...) after a successful upload",
  /onImportSuccess\??\.\(/.test(uploadStatement)
);

// --- 2 & 3. Dashboard bumps refreshKey and passes it to all four panels ---
const dashboard = read("pages/Dashboard.jsx");
check(
  "Dashboard.jsx defines a refreshKey state value",
  /useState\(0\)/.test(dashboard) && /refreshKey/.test(dashboard)
);
check(
  "Dashboard.jsx bumps refreshKey inside its import-success handler",
  /setRefreshKey\(\s*\(?\s*key\s*\)?\s*=>\s*key\s*\+\s*1\s*\)/.test(dashboard)
);
for (const component of ["SummaryCards", "CategoryBreakdown", "StatusBreakdown", "SpendingTrend"]) {
  check(
    `Dashboard.jsx passes refreshKey={refreshKey} to <${component} />`,
    new RegExp(`<${component}[^>]*refreshKey={refreshKey}`).test(dashboard)
  );
}

// --- 4. Each panel actually consumes refreshKey and refetches on change ---
const panels = {
  "components/SummaryCards.jsx": "getAnalyticsSummary",
  "components/CategoryBreakdown.jsx": "getAnalyticsByCategory",
  "components/StatusBreakdown.jsx": "getAnalyticsByStatus",
  "components/SpendingTrend.jsx": "getAnalyticsByDate",
};

for (const [path, fetcher] of Object.entries(panels)) {
  const source = read(path);
  check(
    `${path} destructures refreshKey from its props`,
    /\(\s*{\s*refreshKey\s*}\s*\)/.test(source)
  );
  check(
    `${path} passes [refreshKey] as the useFetchOnMount deps array`,
    new RegExp(`useFetchOnMount\\(${fetcher},\\s*\\[refreshKey\\]\\)`).test(source)
  );
}

// --- Report ---
if (failures.length > 0) {
  console.error("REFRESH WIRING CHECK FAILED:\n");
  for (const f of failures) console.error(`  ✗ ${f}`);
  console.error(`\n${failures.length} check(s) failed.`);
  process.exit(1);
}

console.log("Refresh wiring check passed: PDF import -> analytics refresh is correctly wired.");
console.log("  ✓ UploadStatement notifies Dashboard on successful import");
console.log("  ✓ Dashboard bumps refreshKey and passes it to all four analytics panels");
console.log("  ✓ All four panels consume refreshKey and refetch when it changes");
process.exit(0);