// supabase/functions/_shared/cors.ts
// Shared CORS headers for all Edge Functions

export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers':
    'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
};

/** Returns a CORS preflight response */
export function handleOptions(): Response {
  return new Response(null, { status: 204, headers: corsHeaders });
}

/** Wraps a response body with CORS headers */
export function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  });
}

/** Wraps an error with CORS headers */
export function errorResponse(message: string, status = 500): Response {
  return jsonResponse({ error: message }, status);
}
