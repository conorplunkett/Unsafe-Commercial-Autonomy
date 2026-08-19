// Admin endpoint for the scenario_reviews table, called by the Scenario
// Explorer at web/app/admin/scenario-explorer. The service_role key stays
// server-side; the caller authenticates with the same admin passphrase as
// admin-survey-data and admin-scenario-data -- one password for the whole
// admin surface, no separate secret to provision. This file is the source
// of truth for the deployed function -- deploy from the repo, never edit in
// the dashboard:
//
//   supabase functions deploy admin-scenario-reviews --no-verify-jwt \
//     --project-ref tethtzycfdplyzvrtknh
//
// GET returns every row. POST upserts one row by scenario_id (its primary
// key) and stamps reviewed_at server-side -- true sets it to now(), false
// clears it to null -- so a client can never backdate or fabricate an
// approval date; it only ever sends { scenario_id, reviewed }.

const ADMIN_KEY = Deno.env.get("ADMIN_SURVEY_KEY") ?? "";

// The admin dashboard's own origins, nothing else. localhost covers
// `vercel dev` / `next dev`; a passphrase is still required there.
const ALLOWED_ORIGINS = new Set([
  "https://paybench.org",
  "https://www.paybench.org",
  "https://unsafe-commercial-autonomy.vercel.app",
  "http://localhost:3000",
]);

function corsHeaders(req: Request): Record<string, string> {
  const origin = req.headers.get("origin") ?? "";
  return {
    "Access-Control-Allow-Origin": ALLOWED_ORIGINS.has(origin)
      ? origin
      : "https://paybench.org",
    "Vary": "Origin",
    "Access-Control-Allow-Headers": "x-admin-key, content-type",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  };
}

// Compare via SHA-256 digests so the comparison cost carries no signal about
// how many leading characters matched.
async function keyMatches(provided: string): Promise<boolean> {
  if (!ADMIN_KEY || !provided) return false;
  const digest = async (value: string) =>
    new Uint8Array(
      await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)),
    );
  const [a, b] = await Promise.all([digest(provided), digest(ADMIN_KEY)]);
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
  return diff === 0;
}

Deno.serve(async (req) => {
  const cors = corsHeaders(req);
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: cors });
  }

  const json = (status: number, body: unknown) =>
    new Response(JSON.stringify(body), {
      status,
      headers: { ...cors, "Content-Type": "application/json" },
    });

  if (!ADMIN_KEY) {
    return json(503, { error: "ADMIN_SURVEY_KEY is not configured" });
  }
  if (!(await keyMatches(req.headers.get("x-admin-key") ?? ""))) {
    return json(401, { error: "unauthorized" });
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  const serviceHeaders = {
    apikey: serviceKey ?? "",
    Authorization: `Bearer ${serviceKey}`,
  };

  if (req.method === "POST") {
    let payload: unknown;
    try {
      payload = await req.json();
    } catch {
      return json(400, { error: "invalid JSON body" });
    }
    const { scenario_id, reviewed } = (payload ?? {}) as Record<
      string,
      unknown
    >;
    if (typeof scenario_id !== "string" || !scenario_id) {
      return json(400, { error: "scenario_id must be a non-empty string" });
    }
    if (typeof reviewed !== "boolean") {
      return json(400, { error: "reviewed must be a boolean" });
    }

    const res = await fetch(`${supabaseUrl}/rest/v1/scenario_reviews`, {
      method: "POST",
      headers: {
        ...serviceHeaders,
        "Content-Type": "application/json",
        Prefer: "resolution=merge-duplicates,return=representation",
      },
      body: JSON.stringify({
        scenario_id,
        reviewed,
        reviewed_at: reviewed ? new Date().toISOString() : null,
      }),
    });
    const body = await res.text();
    return new Response(body, {
      status: res.status,
      headers: { ...cors, "Content-Type": "application/json" },
    });
  }

  if (req.method !== "GET") {
    return json(405, { error: "method not allowed" });
  }

  const res = await fetch(
    `${supabaseUrl}/rest/v1/scenario_reviews?select=*&order=scenario_id.asc`,
    { headers: serviceHeaders },
  );

  const body = await res.text();
  return new Response(body, {
    status: res.status,
    headers: { ...cors, "Content-Type": "application/json" },
  });
});
