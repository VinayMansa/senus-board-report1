import { useEffect, useState, useCallback } from "react";
import api from "../api";

/**
 * Loads a metrics fetcher (e.g. api.growth) plus the matching AI insight
 * (e.g. section "growth") together, and exposes a regenerate() action
 * that forces a fresh AI commentary call.
 */
export function useSection(fetcher, insightSection) {
  const [data, setData] = useState(null);
  const [insight, setInsight] = useState(null);
  const [loading, setLoading] = useState(true);
  const [insightLoading, setInsightLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [metricsRes, insightRes] = await Promise.all([
        fetcher(),
        insightSection ? api.insight(insightSection) : Promise.resolve(null),
      ]);
      setData(metricsRes);
      setInsight(insightRes);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }, [fetcher, insightSection]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const regenerate = useCallback(async () => {
    if (!insightSection) return;
    setInsightLoading(true);
    try {
      const fresh = await api.regenerateInsight(insightSection);
      setInsight(fresh);
    } finally {
      setInsightLoading(false);
    }
  }, [insightSection]);

  return { data, insight, loading, insightLoading, error, regenerate, reload: load };
}
