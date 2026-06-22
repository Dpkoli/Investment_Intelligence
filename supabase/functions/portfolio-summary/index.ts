import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// GET /portfolio-summary
// Query params:
//   portfolio_id  – (optional) filter to a specific portfolio; omit for all caller's portfolios
//
// RLS on v_my_portfolio_summary scopes results to auth.uid() automatically.
// Response includes per-portfolio aggregate stats for dashboard cards.

interface PositionRow {
  portfolio_id:          number;
  portfolio_name:        string;
  asset_cluster:         string;
  target_weight:         number;
  position_size_usd:     number | null;
  ka_score:              number | null;
  open_cassandra_signals: number;
  max_risk_score:        number;
  unrealised_pnl_pct:    number | null;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });

  try {
    const url        = new URL(req.url);
    const portfolioId = url.searchParams.get("portfolio_id");

    const client = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_ANON_KEY")!,
      { global: { headers: { Authorization: req.headers.get("Authorization")! } } }
    );

    let query = (client as any)
      .from("v_my_portfolio_summary")
      .select("*")
      .order("target_weight", { ascending: false });

    if (portfolioId) query = query.eq("portfolio_id", parseInt(portfolioId));

    const { data, error } = await query;
    if (error) throw error;

    const positions: PositionRow[] = data ?? [];

    // Build per-portfolio aggregate cards
    const portfolioMap: Record<number, {
      portfolio_id:       number;
      portfolio_name:     string;
      total_positions:    number;
      avg_ka_score:       number;
      open_alerts:        number;
      max_risk:           number;
      total_aum_deployed: number;
      cluster_breakdown:  Record<string, number>;
      positions:          PositionRow[];
    }> = {};

    for (const row of positions) {
      if (!portfolioMap[row.portfolio_id]) {
        portfolioMap[row.portfolio_id] = {
          portfolio_id:       row.portfolio_id,
          portfolio_name:     row.portfolio_name,
          total_positions:    0,
          avg_ka_score:       0,
          open_alerts:        0,
          max_risk:           0,
          total_aum_deployed: 0,
          cluster_breakdown:  {},
          positions:          [],
        };
      }
      const p = portfolioMap[row.portfolio_id];
      p.total_positions++;
      p.avg_ka_score       += row.ka_score ?? 0;
      p.open_alerts        += row.open_cassandra_signals;
      p.max_risk            = Math.max(p.max_risk, row.max_risk_score);
      p.total_aum_deployed += row.position_size_usd ?? 0;
      p.cluster_breakdown[row.asset_cluster] =
        (p.cluster_breakdown[row.asset_cluster] ?? 0) + row.target_weight;
      p.positions.push(row);
    }

    for (const p of Object.values(portfolioMap)) {
      p.avg_ka_score = p.total_positions > 0
        ? Math.round((p.avg_ka_score / p.total_positions) * 100) / 100
        : 0;
    }

    return new Response(
      JSON.stringify({ portfolios: Object.values(portfolioMap) }),
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
