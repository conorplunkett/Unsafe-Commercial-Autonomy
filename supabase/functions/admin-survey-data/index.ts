// Admin endpoint for the survey tables, called by web/public/admin.html. The
// service_role key stays server-side; the caller authenticates with the admin
// passphrase, which grants read (GET) and single-row delete (DELETE) access
// to the whitelisted tables below — nothing else. This file is the source of
// truth for the deployed function — deploy from the repo, never edit in the
// dashboard:
//
//   supabase secrets set ADMIN_SURVEY_KEY="$(openssl rand -base64 30)" \
//     --project-ref tethtzycfdplyzvrtknh
//   supabase functions deploy admin-survey-data --no-verify-jwt \
//     --project-ref tethtzycfdplyzvrtknh
//
// The passphrase lives only in the function's secrets (rotate by re-running
// `secrets set`); the function refuses to serve while it is unset.

const ADMIN_KEY = Deno.env.get("ADMIN_SURVEY_KEY") ?? "";

const TABLES: Record<string, string> = {
  "1": "phase1_survey_responses",
  "2": "phase2_survey_responses",
};

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

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
    "Access-Control-Allow-Methods": "GET, DELETE, OPTIONS",
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

  const reqUrl = new URL(req.url);
  const phase = reqUrl.searchParams.get("phase") || "1";
  const table = TABLES[phase];
  if (!table) {
    return json(400, { error: "invalid phase" });
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  const serviceHeaders = {
    apikey: serviceKey ?? "",
    Authorization: `Bearer ${serviceKey}`,
  };

  if (req.method === "DELETE") {
    const id = reqUrl.searchParams.get("id") || "";
    if (!UUID_RE.test(id)) {
      return json(400, { error: "invalid id" });
    }
    const res = await fetch(
      `${supabaseUrl}/rest/v1/${table}?id=eq.${id}`,
      {
        method: "DELETE",
        headers: { ...serviceHeaders, Prefer: "return=representation" },
      },
    );
    const body = await res.text();
    if (res.ok) {
      // PostgREST returns the deleted rows as a JSON array; an empty array
      // means the id didn't match anything (already deleted, or never existed).
      let deleted: unknown[] = [];
      try {
        deleted = JSON.parse(body);
      } catch {
        // fall through with an empty array — treated as "not found" below
      }
      if (!Array.isArray(deleted) || deleted.length === 0) {
        return json(404, { error: "not found" });
      }
    }
    return new Response(body, {
      status: res.status,
      headers: { ...cors, "Content-Type": "application/json" },
    });
  }

  if (req.method !== "GET") {
    return json(405, { error: "method not allowed" });
  }

  const res = await fetch(
    `${supabaseUrl}/rest/v1/${table}?select=*&order=created_at.asc`,
    { headers: serviceHeaders },
  );

  const body = await res.text();
  return new Response(body, {
    status: res.status,
    headers: { ...cors, "Content-Type": "application/json" },
  });
});
