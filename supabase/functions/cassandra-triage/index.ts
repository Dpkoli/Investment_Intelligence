import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// GET /cassandra-triage
// Query params:
//   min_risk        – minimum Systemic_Risk_Score (default 1)
//   unreviewed_only – true | false (default false)
//   severity        – INFO | WATCH | THREAT | CRITICAL
//   watchlist_only  – true | false — restricts to assets in the caller's watchlists
//   limit           – max rows (default 50, max 200)

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });

  try {
    const url           = new URL(req.url);
    const minRisk       = parseInt(url.searchParams.get("min_risk") ?? "1");
    const unreviewedOnly = url.searchParams.get("unreviewed_only") === "true";
    const severity      = url.searchParams.get("severity");
    const limit         = Math.min(parseInt(url.searchParams.get("limit") ?? "50"), 200);
    const watchlistOnly = url.searchParams.get("watchlist_only") === "true";

    const authHeader = req.headers.get("Authorization")!;
    const client = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_ANON_KEY")!,
      { global: { headers: { Authorization: authHeader } } }
    );

    // Resolve caller's watched asset IDs when watchlist_only=true
    let watchedAssetIds: number[] | null = null;
    if (watchlistOnly) {
      const { data: wlItems } = await (client as any)
        .from("watchlist_items")
        .select("asset_id");
      watchedAssetIds = (wlItems ?? []).map((r: { asset_id: number }) => r.asset_id);
    }

    let query = (client as any)
      .from("v_cassandra_triage")
      .select("*")
      .gte("systemic_risk_score", minRisk)
      .limit(limit)
      .order("systemic_risk_score", { ascending: false })
      .order("signal_date", { ascending: false });

    if (unreviewedOnly)    query = query.eq("analyst_reviewed", false);
    if (severity)          query = query.eq("severity", severity);
    if (watchedAssetIds !== null && watchedAssetIds.length > 0) {
      query = query.in("target_asset_id", watchedAssetIds);
    }

    const { data, error } = await query;
    if (error) throw error;

    // Severity summary counts for dashboard badge rendering
    const summary = (data ?? []).reduce(
      (acc: Record<string, number>, row: { severity: string }) => {
        acc[row.severity] = (acc[row.severity] ?? 0) + 1;
        return acc;
      },
      {}
    );

    return new Response(
      JSON.stringify({ data, summary, meta: { minRisk, unreviewedOnly, severity, watchlistOnly } }),
      { headers: { ...CORS, "Content-Type": "application/json" } }
    );
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return new Response(
      JSON.stringify({ error: msg }),
      { status: 500, headers: { ...CORS, "Content-Type": "application/json" } }
    );
  }
});
