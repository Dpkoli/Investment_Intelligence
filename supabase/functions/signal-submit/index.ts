import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// POST /signal-submit
// Body (JSON):
//   asset_id?:              number      – target asset (at least one of asset_id / cluster_id required)
//   cluster_id?:            number      – target cluster
//   signal_source?:         string      – Whistleblower | Influencer | Regulatory_Leak |
//                                         Short_Seller_Report | Anonymous_Filing (default)
//   source_handle?:         string      – Twitter/X handle, pseudonym, etc.
//   title:                  string      – required
//   text:                   string      – required (raw signal body)
//   risk_score:             number      – 1–10, required
//   risk_vector?:           string      – e.g. "Counterparty_Concentration"
//   related_connection_id?: number      – link to a Corporate_Ecosystem_Connections row
//   source_url?:            string      – evidence URL

const VALID_SOURCES = [
  "Whistleblower", "Influencer", "Regulatory_Leak",
  "Short_Seller_Report", "Anonymous_Filing",
] as const;
type SignalSource = typeof VALID_SOURCES[number];

const SEVERITY_MAP: Record<number, string> = {
  1: "INFO", 2: "INFO",  3: "INFO",
  4: "WATCH", 5: "WATCH", 6: "WATCH",
  7: "THREAT", 8: "THREAT", 9: "THREAT",
  10: "CRITICAL",
};

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ error: "POST required" }),
      { status: 405, headers: { ...CORS, "Content-Type": "application/json" } }
    );
  }

  try {
    const body: {
      asset_id?:              number;
      cluster_id?:            number;
      signal_source?:         SignalSource;
      source_handle?:         string;
      title:                  string;
      text:                   string;
      risk_score:             number;
      risk_vector?:           string;
      related_connection_id?: number;
      source_url?:            string;
    } = await req.json();

    // Input validation
    if (!body.title?.trim())    throw new Error("'title' is required");
    if (!body.text?.trim())     throw new Error("'text' is required");
    if (!Number.isInteger(body.risk_score) || body.risk_score < 1 || body.risk_score > 10) {
      throw new Error("'risk_score' must be an integer between 1 and 10");
    }
    if (body.signal_source && !(VALID_SOURCES as readonly string[]).includes(body.signal_source)) {
      throw new Error(`'signal_source' must be one of: ${VALID_SOURCES.join(", ")}`);
    }
    if (!body.asset_id && !body.cluster_id) {
      throw new Error("At least one of 'asset_id' or 'cluster_id' is required");
    }

    // Service-role client: fn_dispatch_cassandra_alert writes to Cassandra_Dispatch_Log
    // (no authenticated-user insert policy on that table).
    // JWT is already verified at gateway (verify_jwt: true).
    const admin = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    );

    const { data: signalId, error } = await admin.rpc("fn_dispatch_cassandra_alert", {
      p_target_asset_id:       body.asset_id              ?? null,
      p_target_cluster_id:     body.cluster_id            ?? null,
      p_signal_source:         body.signal_source         ?? "Anonymous_Filing",
      p_source_handle:         body.source_handle         ?? null,
      p_signal_title:          body.title,
      p_raw_signal_text:       body.text,
      p_risk_score:            body.risk_score,
      p_risk_vector:           body.risk_vector           ?? null,
      p_related_connection_id: body.related_connection_id ?? null,
      p_trigger_source:        "analyst_manual",
      p_trigger_record_type:   "Analyst_Profiles",
      p_trigger_record_id:     null,
      p_trigger_condition:     "Manual submission via signal-submit API",
      p_observed_value:        body.risk_score,
      p_threshold_value:       null,
    });

    if (error) throw error;

    if (body.source_url && signalId) {
      await admin
        .from("cassandra_signals")
        .update({ primary_source_url: body.source_url })
        .eq("signal_id", signalId);
    }

    return new Response(
      JSON.stringify({
        signal_id: signalId,
        severity:  SEVERITY_MAP[body.risk_score],
        message:   `Signal ${signalId} dispatched at severity ${SEVERITY_MAP[body.risk_score]}`,
      }),
      { status: 201, headers: { ...CORS, "Content-Type": "application/json" } }
    );
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return new Response(
      JSON.stringify({ error: msg }),
      { status: 400, headers: { ...CORS, "Content-Type": "application/json" } }
    );
  }
});
