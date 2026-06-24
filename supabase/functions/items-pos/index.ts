// supabase/functions/items-pos/index.ts
// POS-safe paginated product loader
// GET /items/pos/products/?outlet_id=&limit=50&cursor=

import { handleOptions, jsonResponse, errorResponse } from '../_shared/cors.ts';
import { getSupabaseAdmin } from '../_shared/supabase.ts';

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return handleOptions();

  const db = getSupabaseAdmin();
  const url = new URL(req.url);

  try {
    const outletId = url.searchParams.get('outlet_id');
    const limit = parseInt(url.searchParams.get('limit') ?? '50');
    const cursor = url.searchParams.get('cursor');

    if (!outletId) return errorResponse('outlet_id required', 400);

    let query = db
      .from('items')
      .select('*')
      .eq('is_active', true)
      .contains('outlet_ids', [outletId])
      .order('name')
      .limit(limit);

    // Cursor-based pagination: get name of cursor doc then filter gt
    if (cursor) {
      const { data: cursorData } = await db
        .from('items')
        .select('name')
        .eq('id', cursor)
        .single();
      if (cursorData) {
        query = query.gt('name', cursorData.name);
      }
    }

    const { data, error } = await query;
    if (error) throw error;

    const products = data ?? [];
    const nextCursor = products.length > 0 ? products[products.length - 1].id : null;

    return jsonResponse({ results: products, next_cursor: nextCursor });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return errorResponse(msg);
  }
});
