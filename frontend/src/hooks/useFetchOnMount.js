import { useEffect, useState } from "react";

/**
 * Runs `fetcher` on mount (and again whenever any value in `deps`
 * changes) and tracks { data, loading, error }.
 *
 * `deps` defaults to [] (fetch once on mount only), matching the original
 * behavior every existing caller relies on. Passing e.g. [refreshKey]
 * lets a parent component trigger a refetch on demand (used after a
 * successful PDF import to refresh the analytics panels) without each
 * panel needing its own bespoke refresh logic.
 */
export function useFetchOnMount(fetcher, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError(null);

    fetcher()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Something went wrong");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading, error };
}