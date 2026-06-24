// supabase/functions/expenses/index.ts
// Handles: GET /expenses/manage/?start_date=&end_date=
//           POST /expenses/manage/
//           PUT /expenses/manage/:id/
//           DELETE /expenses/manage/:id/

import { corsHeaders, handleOptions, jsonResponse, errorResponse } from '../_shared/cors.ts';
import { getSupabaseAdmin } from '../_shared/supabase.ts';

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return handleOptions();

  const db = getSupabaseAdmin();
  const url = new URL(req.url);
  const pathParts = url.pathname.split('/').filter(Boolean);
  const expenseId = pathParts[pathParts.length - 1] !== 'manage' ? pathParts[pathParts.length - 1] : null;

  try {
    // ---- GET /expenses/manage/ ----
    if (req.method === 'GET') {
      const startDate = url.searchParams.get('start_date');
      const endDate = url.searchParams.get('end_date');

      let query = db.from('expenses').select('*');
      if (startDate) query = query.gte('date', startDate);
      if (endDate) query = query.lte('date', endDate);
      query = query.order('date', { ascending: false });

      const { data, error } = await query;
      if (error) throw error;
      return jsonResponse(data ?? []);
    }

    // ---- POST /expenses/manage/ ----
    if (req.method === 'POST') {
      const body = await req.json();
      const { description, amount, category, date, outlet_id = 'general' } = body;

      if (!description || !amount || !category) {
        return errorResponse('Description, amount, and category are required.', 400);
      }

      const expenseData = {
        description,
        amount: parseFloat(amount),
        category,
        date: date ?? new Date().toISOString().split('T')[0],
        outlet_id,
        created_at: new Date().toISOString(),
      };

      const { error } = await db.from('expenses').insert(expenseData);
      if (error) throw error;
      return jsonResponse({ message: 'Expense recorded successfully.' }, 201);
    }

    // ---- PUT /expenses/manage/:id/ ----
    if (req.method === 'PUT' && expenseId) {
      const body = await req.json();
      const { error } = await db
        .from('expenses')
        .update(body)
        .eq('id', expenseId);
      if (error) throw error;
      return jsonResponse({ message: 'Expense updated successfully.' });
    }

    // ---- DELETE /expenses/manage/:id/ ----
    if (req.method === 'DELETE' && expenseId) {
      const { error } = await db
        .from('expenses')
        .delete()
        .eq('id', expenseId);
      if (error) throw error;
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    return errorResponse('Not found', 404);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    console.error('expenses error:', msg);
    return errorResponse(msg);
  }
});
