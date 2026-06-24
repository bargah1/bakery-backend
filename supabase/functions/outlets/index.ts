// supabase/functions/outlets/index.ts
// Handles: GET /outlets/manage/, POST /outlets/manage/,
//           PUT /outlets/manage/:id/, DELETE /outlets/manage/:id/

import { corsHeaders, handleOptions, jsonResponse, errorResponse } from '../_shared/cors.ts';
import { getSupabaseAdmin } from '../_shared/supabase.ts';

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return handleOptions();

  const db = getSupabaseAdmin();
  const url = new URL(req.url);
  // Extract optional outlet ID from path: /outlets/manage/<id>/
  const pathParts = url.pathname.split('/').filter(Boolean);
  const outletId = pathParts[pathParts.length - 1] !== 'manage' ? pathParts[pathParts.length - 1] : null;

  try {
    // ---- GET /outlets/manage/ — list all outlets ----
    if (req.method === 'GET' && !outletId) {
      const { data, error } = await db
        .from('outlets')
        .select('*')
        .order('name')
        .limit(50);

      if (error) throw error;

      const outlets = (data ?? []).map((row) => ({
        id: row.id,
        name: row.name,
        phone: row.phone,
        type: row.type,
      }));
      return jsonResponse(outlets);
    }

    // ---- POST /outlets/manage/ — create outlet ----
    if (req.method === 'POST') {
      const body = await req.json();
      const { name, phone, type = 'sales' } = body;

      if (!name || !phone) {
        return errorResponse('Name and phone are required.', 400);
      }

      const id = name.toLowerCase().replace(/ /g, '_').replace(/-/g, '_');
      const { error } = await db
        .from('outlets')
        .upsert({ id, name, phone, type });

      if (error) throw error;
      return jsonResponse({ message: 'Outlet added', id }, 201);
    }

    // ---- PUT /outlets/manage/:id/ — update outlet ----
    if (req.method === 'PUT' && outletId) {
      const body = await req.json();
      const { error } = await db
        .from('outlets')
        .update(body)
        .eq('id', outletId);

      if (error) throw error;
      return jsonResponse({ message: `Outlet '${outletId}' updated successfully.` });
    }

    // ---- DELETE /outlets/manage/:id/ — delete outlet ----
    if (req.method === 'DELETE' && outletId) {
      const { error } = await db
        .from('outlets')
        .delete()
        .eq('id', outletId);

      if (error) throw error;
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    return errorResponse('Not found', 404);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    console.error('outlets error:', msg);
    return errorResponse(msg);
  }
});
