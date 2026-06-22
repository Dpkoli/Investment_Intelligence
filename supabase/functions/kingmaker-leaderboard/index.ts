import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// GET /kingmaker-leaderboard
// Query params:
//   min_score      – minimum KA_Score (default 0)
//   tier           – 1 | 2 | 3 (Kingmaker tier filter)
//   conviction     – "Tier-1 Conviction" | "High Watch" | "Speculative" | "Monitoring"
//   endorsed_only  – true | false (only titan-endorsed assets)
//   limit          – max rows per page (default 20, max 100)
//   page           – page number (default 1)

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });

  try {
    const url         = new URL(req.url);
    const minScore    = parseFloat(url.searchParams.get("min_score") ?? "0");
    const tier        = url.searchParams.get("tier");
    const conviction  = url.searchParams.get("conviction");
    const limit       = Math.min(parseInt(url.searchParams.get("limit") ?? "20"), 100);
    const page        = Math.max(1, parseInt(url.searchParams.get("page") ?? "1"));
    const offset      = (page - 1) * limit;
    const endorsedOnly = url.searchParams.get("endorsed_only") === "true";

    const client = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_ANON_KEY")!,
      { global: { headers: { Authorization: req.headers.get("Authorization")! } } }
    );

    let query = (client as any)
      .from("v_kingmaker_leaderboard")
      .select("*", { count: "exact" })
      .gte("ka_score", minScore)
      .range(offset, offset + limit - 1)
      .order("ka_score", { ascending: false });

    if (tier)         query = query.eq("kingmaker_tier", parseInt(tier));
    if (conviction)   query = query.eq("conviction_label", conviction);
    if (endorsedOnly) query = query.eq("titan_endorsed", true);

    const { data, error, count } = await query;
    if (error) throw error;

    return new Response(
      JSON.stringify({
        data,
        meta: { page, limit, total: count, filters: { minScore, tier, conviction, endorsedOnly } },
      }),
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
