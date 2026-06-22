import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// POST /score-asset
// Body (JSON):
//   { asset_id: number }          – compute KA_Score for a single KINGMAKER asset
//   { refresh_all: true }         – batch recompute all active KINGMAKER assets (admin use)
//
// Uses service_role key: fn_compute_kingmaker_alpha writes to Asset_Alpha_Scores which
// has RLS blocking direct authenticated inserts. JWT is verified at gateway (verify_jwt: true)
// before this function body runs, so the caller is always authenticated.

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ error: "POST required" }),
      { status: 405, headers: { ...CORS, "Content-Type": "application/json" } }
    );
  }

  try {
    const body: { asset_id?: number; refresh_all?: boolean } = await req.json();

    const admin = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    );

    if (body.refresh_all) {
      const { data, error } = await admin.rpc("fn_refresh_all_kingmaker_scores");
      if (error) throw error;
      return new Response(
        JSON.stringify({ refreshed: data, computed_at: new Date().toISOString() }),
        { headers: { ...CORS, "Content-Type": "application/json" } }
      );
    }

    if (!body.asset_id || !Number.isInteger(body.asset_id)) {
      return new Response(
        JSON.stringify({ error: "asset_id (integer) or refresh_all (boolean) required" }),
        { status: 400, headers: { ...CORS, "Content-Type": "application/json" } }
      );
    }

    const { data: score, error } = await admin.rpc("fn_compute_kingmaker_alpha", {
      p_asset_id: body.asset_id,
    });
    if (error) throw error;

    // Return the full score row just inserted
    const { data: scoreRow } = await admin
      .from("asset_alpha_scores")
      .select("*")
      .eq("asset_id", body.asset_id)
      .order("computed_at", { ascending: false })
      .limit(1)
      .single();

    return new Response(
      JSON.stringify({ asset_id: body.asset_id, ka_score: score, score_row: scoreRow }),
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
