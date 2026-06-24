// supabase/functions/production/index.ts
// Handles all production endpoints
//
// GET    /production/ingredients/all/             → all ingredients across all production units
// GET    /production/inventory/:outlet_id/        → ingredients for one outlet
// POST   /production/inventory/:outlet_id/        → add ingredient to outlet
// PUT    /production/inventory/:outlet_id/:ing_id/  → update ingredient
// DELETE /production/inventory/:outlet_id/:ing_id/  → delete ingredient
// GET    /production/recipes/                     → list all recipes
// POST   /production/recipes/                     → create recipe
// PUT    /production/recipes/:recipe_id/          → update recipe
// DELETE /production/recipes/:recipe_id/          → delete recipe
// POST   /production/record/                      → record production batch
// GET    /production/structured-report/           → production report
// DELETE /production/logs/delete-range/           → bulk delete logs

import { corsHeaders, handleOptions, jsonResponse, errorResponse } from '../_shared/cors.ts';
import { getSupabaseAdmin } from '../_shared/supabase.ts';

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return handleOptions();

  const db = getSupabaseAdmin();
  const url = new URL(req.url);
  const pathname = url.pathname;

  try {
    // ---- GET /production/ingredients/all/ ----
    if (req.method === 'GET' && pathname.includes('ingredients/all')) {
      const { data: outlets } = await db.from('outlets').select('id').eq('type', 'production');
      const outletIds = (outlets ?? []).map((o: { id: string }) => o.id);

      if (!outletIds.length) return jsonResponse([]);

      const { data, error } = await db
        .from('outlet_ingredients')
        .select('*')
        .in('outlet_id', outletIds);
      if (error) throw error;

      // Aggregate stock across all production units
      const combined: Record<string, Record<string, unknown>> = {};
      for (const row of data ?? []) {
        if (combined[row.id]) {
          (combined[row.id].stock as number) += row.stock ?? 0;
        } else {
          combined[row.id] = { ...row };
        }
      }
      return jsonResponse(Object.values(combined));
    }

    // ---- /production/inventory/:outlet_id/ ----
    const inventoryMatch = pathname.match(/inventory\/([^/]+)(?:\/([^/]+))?\/?$/);
    if (inventoryMatch) {
      const outletId = inventoryMatch[1];
      const ingredientId = inventoryMatch[2];

      if (!ingredientId) {
        // GET or POST /production/inventory/:outlet_id/
        if (req.method === 'GET') {
          const { data, error } = await db
            .from('outlet_ingredients')
            .select('*')
            .eq('outlet_id', outletId)
            .order('name');
          if (error) throw error;
          return jsonResponse(data ?? []);
        }

        if (req.method === 'POST') {
          const body = await req.json();
          const { name, unit, stock = 0, cost_per_unit = 0 } = body;
          if (!name || !unit) return errorResponse('Ingredient name and unit are required.', 400);

          const id = name.toLowerCase().replace(/ /g, '_');
          const { error } = await db.from('outlet_ingredients').upsert({
            id, outlet_id: outletId, name, unit,
            stock: parseFloat(stock), cost_per_unit: parseFloat(cost_per_unit),
          });
          if (error) throw error;
          return jsonResponse({ id, message: 'Ingredient added.' }, 201);
        }
      } else {
        // PUT or DELETE /production/inventory/:outlet_id/:ingredient_id/
        if (req.method === 'PUT') {
          const body = await req.json();
          delete body.id;
          delete body.outlet_id;
          const { error } = await db.from('outlet_ingredients')
            .update(body)
            .eq('id', ingredientId)
            .eq('outlet_id', outletId);
          if (error) throw error;
          return jsonResponse({ message: 'Ingredient updated.' });
        }

        if (req.method === 'DELETE') {
          const { error } = await db.from('outlet_ingredients')
            .delete()
            .eq('id', ingredientId)
            .eq('outlet_id', outletId);
          if (error) throw error;
          return new Response(null, { status: 204, headers: corsHeaders });
        }
      }
    }

    // ---- /production/recipes/ ----
    const recipeMatch = pathname.match(/recipes(?:\/([^/]+))?\/?$/);
    if (recipeMatch) {
      const recipeId = recipeMatch[1];

      if (!recipeId) {
        // GET /production/recipes/
        if (req.method === 'GET') {
          const { data, error } = await db.from('recipes').select('*').order('name');
          if (error) throw error;
          return jsonResponse(data ?? []);
        }

        // POST /production/recipes/
        if (req.method === 'POST') {
          const body = await req.json();
          const { name } = body;
          if (!name) return errorResponse('Product name is required.', 400);

          const id = name.toLowerCase().replace(/ /g, '_');
          const recipeData = {
            id, name,
            unit_type: body.unit_type,
            ingredients: body.ingredients ?? [],
            shelf_life_days: body.shelf_life_days,
            calories: body.calories,
            energy: body.energy,
            nutrition_info: body.nutrition_info,
          };
          const itemData = {
            id, name,
            unit_type: body.unit_type,
            price: body.price ?? 0,
            stock: body.stock ?? 0,
          };

          await db.from('recipes').upsert(recipeData);
          await db.from('items').upsert(itemData);
          return jsonResponse({ id, message: 'Recipe added/updated.' }, 201);
        }
      } else {
        // PUT /production/recipes/:recipe_id/
        if (req.method === 'PUT') {
          const body = await req.json();
          const recipeUpdate: Record<string, unknown> = {};
          const itemUpdate: Record<string, unknown> = {};

          for (const k of ['name', 'unit_type', 'ingredients', 'shelf_life_days', 'calories', 'energy', 'nutrition_info', 'rate']) {
            if (body[k] !== undefined) recipeUpdate[k] = body[k];
          }
          if (body.name) itemUpdate.name = body.name;
          if (body.unit_type) itemUpdate.unit_type = body.unit_type;
          if (body.rate) itemUpdate.price = body.rate;

          if (Object.keys(recipeUpdate).length) {
            await db.from('recipes').update(recipeUpdate).eq('id', recipeId);
          }
          if (Object.keys(itemUpdate).length) {
            await db.from('items').update(itemUpdate).eq('id', recipeId);
          }
          return jsonResponse({ message: 'Recipe updated.' });
        }

        // DELETE /production/recipes/:recipe_id/
        if (req.method === 'DELETE') {
          await db.from('recipes').delete().eq('id', recipeId);
          await db.from('items').delete().eq('id', recipeId);
          return new Response(null, { status: 204, headers: corsHeaders });
        }
      }
    }

    // ---- POST /production/record/ ----
    if (req.method === 'POST' && pathname.includes('/record')) {
      const body = await req.json();
      const { recipe_id, production_unit_id, quantity } = body;

      if (!recipe_id || !production_unit_id || !quantity || parseFloat(quantity) <= 0) {
        return errorResponse('Recipe, Production Unit, and a positive quantity are required.', 400);
      }

      const qty = parseFloat(quantity);
      const now = new Date();
      const batchId = `${recipe_id.toUpperCase()}-${now.toISOString().replace(/[-:T.Z]/g, '').slice(0, 14)}`;

      // Get recipe ingredients
      const { data: recipe } = await db.from('recipes').select('ingredients').eq('id', recipe_id).single();
      if (!recipe) return errorResponse(`Recipe '${recipe_id}' not found.`, 404);

      // Use the PostgreSQL transaction function
      const { error: rpcError } = await db.rpc('record_production_transaction', {
        p_batch_id: batchId,
        p_recipe_id: recipe_id,
        p_quantity: qty,
        p_production_unit_id: production_unit_id,
        p_ingredients: recipe.ingredients ?? [],
        p_date: now.toISOString().split('T')[0],
        p_timestamp: now.toISOString(),
      });

      if (rpcError) throw new Error(rpcError.message);
      return jsonResponse({ message: 'Production recorded and stock/cost updated.', batch_id: batchId });
    }

    // ---- GET /production/structured-report/ ----
    if (req.method === 'GET' && pathname.includes('structured-report')) {
      const startDate = url.searchParams.get('start_date');
      const endDate = url.searchParams.get('end_date');
      const unitId = url.searchParams.get('production_unit_id');

      let query = db.from('production_logs').select('*').order('date', { ascending: false }).order('timestamp', { ascending: false });
      if (startDate) query = query.gte('date', startDate);
      if (endDate) query = query.lte('date', endDate);
      if (unitId && unitId !== 'All Production Units') query = query.eq('production_unit_id', unitId);

      const { data, error } = await query;
      if (error) throw error;
      return jsonResponse(data ?? []);
    }

    // ---- DELETE /production/logs/delete-range/ ----
    if (req.method === 'DELETE' && pathname.includes('logs/delete-range')) {
      const startDate = url.searchParams.get('start_date');
      const endDate = url.searchParams.get('end_date');
      const unitId = url.searchParams.get('production_unit_id');

      if (!startDate || !endDate) return errorResponse('Start and end dates are required.', 400);

      let query = db.from('production_logs').delete().gte('date', startDate).lte('date', endDate);
      if (unitId && unitId !== 'All Production Units') query = query.eq('production_unit_id', unitId);

      const { data, error } = await query;
      if (error) throw error;
      return jsonResponse({ message: `Deleted ${(data as unknown[])?.length ?? 0} production logs.` });
    }

    return errorResponse('Not found', 404);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    console.error('production error:', msg);
    return errorResponse(msg);
  }
});
