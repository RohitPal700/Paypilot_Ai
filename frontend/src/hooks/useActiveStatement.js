import { useState } from "react";

// This project has no authentication/user accounts, so there's no
// server-side concept of "the current user's session". A statement's
// data DOES live in MongoDB permanently (tagged source=="statement_import",
// see backend/app/services/analytics_service.py) so it's never lost --
// this flag only controls whether the CURRENT PAGE LOAD has, at some
// point, actually uploaded a statement and therefore should be shown a
// financial report at all, versus a fresh page load that hasn't uploaded
// anything yet in THIS session and would otherwise see whatever
// statement data happens to already be sitting in the shared database
// from previous testing.
//
// Deliberately NOT persisted to localStorage: every page refresh should
// always start at the clean empty state, even if this same browser
// uploaded a statement earlier. Re-uploading (or re-importing the same
// PDF, which the backend correctly reports as duplicates) re-activates
// the dashboard within that session.

/**
 * Tracks whether THIS PAGE LOAD has an "active statement" -- i.e. has
 * uploaded a PDF statement at some point during the current session, so
 * the dashboard's financial report should be shown instead of an empty
 * state.
 *
 * Call `activate()` after ANY successful upload response (including an
 * all-duplicates response with `imported === 0`) -- the statement's data
 * already exists in the database either way, so the dashboard should
 * treat it as active.
 */
export function useActiveStatement() {
  const [statementId, setStatementId] = useState(null);
  const hasActiveStatement = Boolean(statementId);

  function activate(nextStatementId) {
    if (!nextStatementId) return;
    setStatementId(nextStatementId);
  }

  return { hasActiveStatement, statementId, activate };
}