import { useState } from "react";

// This project has no authentication/user accounts, so there's no
// server-side concept of "the current user's session". A statement's
// data DOES live in MongoDB permanently (tagged source=="statement_import",
// see backend/app/services/analytics_service.py) so it's never lost --
// this flag only controls whether the CURRENT BROWSER has, at some
// point, actually uploaded a statement and therefore should be shown a
// financial report at all, versus a fresh browser that hasn't uploaded
// anything yet and would otherwise see whatever statement data happens
// to already be sitting in the shared database from previous testing.
const STORAGE_KEY = "paypilot_active_statement";

function readInitialState() {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    // localStorage can throw in some environments (e.g. private
    // browsing with storage disabled) -- fail safe to "no active
    // statement" rather than crashing the dashboard.
    return false;
  }
}

/**
 * Tracks whether this browser has an "active statement" -- i.e. has
 * uploaded a PDF statement at some point, so the dashboard's financial
 * report should be shown instead of an empty state. Persisted to
 * localStorage so a page refresh doesn't reset back to the empty state.
 *
 * Call `activate()` after ANY successful upload response (including an
 * all-duplicates response with `imported === 0`) -- the statement's data
 * already exists in the database either way, so the dashboard should
 * treat it as active.
 */
export function useActiveStatement() {
  const [hasActiveStatement, setHasActiveStatement] = useState(readInitialState);

  function activate() {
    setHasActiveStatement(true);
    try {
      window.localStorage.setItem(STORAGE_KEY, "true");
    } catch {
      // Non-fatal -- state is still updated for this session even if
      // persistence fails.
    }
  }

  return { hasActiveStatement, activate };
}