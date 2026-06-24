// supabase/functions/items/index.ts
// Handles all items/products routes AND image upload to Supabase Storage
//
// Routes (mapped via query param ?action=):
//   GET    /items/manage-products/                  → list/search products
//   POST   /items/manage-products/                  → create product
//   GET    /items/manage-products/:id/              → get single product
//   PUT    /items/manage-products/:id/              → update product
//   DELETE /items/manage-products/:id/              → delete product
//   GET    /items/inventory-report/                 → inventory report
//   GET    /items/generate-barcode/                 → generate barcode
//   POST   /items/upload-image/                     → upload product image

import { corsHeaders, handleOptions, jsonResponse, errorResponse } from '../_shared/cors.ts';
import { getSupabaseAdmin } from '../_shared/supabase.ts';

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return handleOptions();

  const db = getSupabaseAdmin();
  const url = new URL(req.url);
  const pathname = url.pathname;

  try {
    // ---- GET /items/generate-barcode/ ----
    if (req.method === 'GET' && pathname.includes('generate-barcode')) {
      const barcode = String(Date.now()).slice(-12);
      const digits = barcode.split('').map(Number);
      const oddSum = digits.filter((_, i) => i % 2 === 0).reduce((a, b) => a + b, 0);
      const evenSum = digits.filter((_, i) => i % 2 !== 0).reduce((a, b) => a + b, 0);
      const checksum = (10 - ((oddSum + evenSum * 3) % 10)) % 10;
      return jsonResponse({ barcode: barcode + checksum });
    }

    // ---- POST /items/upload-image/ ----
    if (req.method === 'POST' && pathname.includes('upload-image')) {
      const formData = await req.formData();
      const file = formData.get('file') as File | null;

      if (!file) return errorResponse('No file provided', 400);

      const now = new Date().toISOString().replace(/[:.]/g, '').slice(0, 15);
      const filePath = `product_images/${now}_${file.name}`;
      const fileBytes = await file.arrayBuffer();

      const { error: uploadError } = await db.storage
        .from('product-images')
        .upload(filePath, fileBytes, { contentType: file.type, upsert: true });

      if (uploadError) throw uploadError;

      const { data: urlData } = db.storage
        .from('product-images')
        .getPublicUrl(filePath);

      return jsonResponse({ image_url: urlData.publicUrl }, 201);
    }

    // ---- GET /items/inventory-report/ ----
    if (req.method === 'GET' && pathname.includes('inventory-report')) {
      const { data, error } = await db.from('items').select('*').order('name');
      if (error) throw error;

      const rows = data ?? [];
      const totalStock = rows.reduce((s: number, r) => s + (r.stock ?? 0), 0);
      const lines = [
        'Current Inventory Report:\n',
        '---------------------------\n',
        ...rows.map((r) => `- ${r.name}: ${r.stock ?? 0} units\n`),
        '\n---------------------------\n',
        `Total Unique Products: ${rows.length}\n`,
        `Total Items In Stock: ${totalStock} units\n`,
      ];

      if (rows.length === 0) {
        return jsonResponse({ report: 'No inventory data found. Please add products via the billing system.' });
      }

      return jsonResponse({ report: lines.join('') });
    }

    // --- Extract product ID from path: /items/manage-products/<id>/ ---
    const manageMatch = pathname.match(/manage-products\/([^/]+)\/?$/);
    const productId = manageMatch ? manageMatch[1] : null;

    // ---- GET /items/manage-products/ — list/search ----
    if (req.method === 'GET' && !productId) {
      const search = url.searchParams.get('search')?.toLowerCase().trim() ?? '';
      const { data, error } = await db.from('items').select('*').order('name');
      if (error) throw error;

      const filtered = (data ?? []).filter((p) =>
        search ? p.name?.toLowerCase().includes(search) : true
      );
      return jsonResponse(filtered);
    }

    // ---- GET /items/manage-products/:id/ ----
    if (req.method === 'GET' && productId) {
      const { data, error } = await db
        .from('items')
        .select('*')
        .eq('id', productId)
        .single();
      if (error || !data) return errorResponse('Product not found', 404);
      return jsonResponse(data);
    }

    // ---- POST /items/manage-products/ — create product ----
    if (req.method === 'POST' && !productId) {
      const body = await req.json();
      const name = (body.name ?? '').trim();
      if (!name) return errorResponse('Product name cannot be empty', 400);

      const id = name.toLowerCase().replace(/ /g, '_');
      const product = {
        id,
        name,
        price: parseFloat(body.price ?? 0),
        stock: parseInt(body.stock ?? 0),
        unit_type: body.unit_type ?? 'piece',
        low_stock_threshold: parseFloat(body.low_stock_threshold ?? 10),
        barcode: body.barcode ?? null,
        type: body.type ?? 'production',
        cost_price: parseFloat(body.cost_price ?? 0),
        image_url: body.image_url ?? '',
        created_at: new Date().toISOString(),
      };

      const { error } = await db.from('items').upsert(product);
      if (error) throw error;
      return jsonResponse({ message: 'Product added', id }, 201);
    }

    // ---- PUT /items/manage-products/:id/ ----
    if (req.method === 'PUT' && productId) {
      const body = await req.json();
      delete body.id;
      const { error } = await db.from('items').update(body).eq('id', productId);
      if (error) throw error;
      return jsonResponse({ message: `Product '${productId}' updated successfully.` });
    }

    // ---- DELETE /items/manage-products/:id/ ----
    if (req.method === 'DELETE' && productId) {
      const { error } = await db.from('items').delete().eq('id', productId);
      if (error) throw error;
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    return errorResponse('Not found', 404);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    console.error('items error:', msg);
    return errorResponse(msg);
  }
});
