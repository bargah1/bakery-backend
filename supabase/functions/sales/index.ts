// supabase/functions/sales/index.ts
// Handles all sales endpoints
//
// POST   /sales/process/                          → process sale (with COGS + stock decrement)
// POST   /sales/record-sale/                      → simple record sale
// GET    /sales/summary-report/                   → summary report
// GET    /sales/structured-report/                → structured report
// GET    /sales/customer-transactions-report/     → customer transactions
// GET    /sales/history/                          → sales history
// GET    /sales/find/:numeric_bill_id/            → find by bill number
// GET    /sales/:sale_id/                         → get single sale
// DELETE /sales/delete-range/                     → bulk delete

import { corsHeaders, handleOptions, jsonResponse, errorResponse } from '../_shared/cors.ts';
import { getSupabaseAdmin } from '../_shared/supabase.ts';

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return handleOptions();

  const db = getSupabaseAdmin();
  const url = new URL(req.url);
  const pathname = url.pathname;

  try {
    // ---- POST /sales/process/ ----
    if (req.method === 'POST' && pathname.includes('process')) {
      const saleData = await req.json();
      const items: unknown[] = saleData.items ?? [];
      const totalAmount: number = saleData.total_amount ?? 0;

      if (!items.length || totalAmount === 0) {
        return errorResponse('Cannot process an empty sale', 400);
      }

      const processedItems = [];
      let totalCogs = 0.0;

      for (const item of items as Record<string, unknown>[]) {
        const productId = item.product_id as string | undefined;
        if (!productId || productId.includes('custom_')) {
          processedItems.push({ ...item, cost: 0.0 });
          continue;
        }

        const { data: productData } = await db
          .from('items')
          .select('*')
          .eq('id', productId)
          .single();

        let itemCost = 0.0;
        if (productData) {
          if (productData.type === 'wholesale') {
            itemCost = parseFloat(productData.cost_price ?? 0) * ((item.quantity as number) ?? 0);
          }
          totalCogs += itemCost;

          // Decrement stock for piece items
          if (productData.unit_type === 'piece' && (item.quantity as number) > 0) {
            await db.rpc('decrement_stock', {
              item_id: productId,
              qty: item.quantity,
            });
          }
        }

        processedItems.push({ ...item, cost: itemCost });
      }

      const numericBillId = String(Date.now()).slice(-7);
      const now = new Date();

      const { data: inserted, error } = await db.from('sales').insert({
        timestamp: now.toISOString(),
        date: now.toISOString().split('T')[0],
        numeric_bill_id: numericBillId,
        total_amount: totalAmount,
        total_cogs: totalCogs,
        items: processedItems,
        outlet_id: saleData.outlet_id ?? null,
        staff_id: saleData.staff_id ?? null,
      }).select('id');

      if (error) throw error;
      const saleId = inserted?.[0]?.id;
      return jsonResponse({ message: 'Sale processed', sale_id: saleId, numeric_bill_id: numericBillId }, 201);
    }

    // ---- POST /sales/record-sale/ ----
    if (req.method === 'POST' && pathname.includes('record-sale')) {
      const body = await req.json();
      const required = ['outlet_id', 'items', 'total_amount', 'payment_method'];
      for (const field of required) {
        if (!body[field]) return errorResponse(`Missing required field: ${field}`, 400);
      }

      const now = new Date();
      const saleRecord = {
        outlet_id: body.outlet_id,
        items: body.items,
        total_amount: body.total_amount,
        payment_method: body.payment_method,
        customer_id: body.customer_id ?? 'anonymous',
        payment_status: body.payment_status ?? 'Paid',
        timestamp: now.toISOString(),
        date: now.toISOString().split('T')[0],
      };

      const { data: inserted, error } = await db.from('sales').insert(saleRecord).select('id');
      if (error) throw error;

      // Decrement stock
      for (const soldItem of body.items ?? []) {
        if (soldItem.item_id && soldItem.quantity > 0) {
          await db.rpc('decrement_stock', { item_id: soldItem.item_id, qty: soldItem.quantity });
        }
      }

      return jsonResponse({
        message: 'Sale recorded successfully and inventory updated',
        sale_id: inserted?.[0]?.id,
      }, 201);
    }

    // ---- GET /sales/summary-report/ ----
    if (req.method === 'GET' && pathname.includes('summary-report')) {
      const startDate = url.searchParams.get('start_date');
      const endDate = url.searchParams.get('end_date');
      const outletId = url.searchParams.get('outlet_id');

      let query = db.from('sales').select('*');
      if (startDate) query = query.gte('date', startDate);
      if (endDate) query = query.lte('date', endDate);
      if (outletId && outletId !== 'All Outlets') query = query.eq('outlet_id', outletId);

      const { data, error } = await query;
      if (error) throw error;

      if (!data?.length) {
        return jsonResponse({ report: `No sales data found for outlet '${outletId ?? 'all outlets'}' from ${startDate} to ${endDate}.` });
      }

      let totalSales = 0;
      const itemsSold: Record<string, number> = {};

      for (const sale of data) {
        totalSales += sale.total_amount ?? 0;
        for (const item of sale.items ?? []) {
          if (item?.product_id) {
            const itemName = item.product_id.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase());
            if ((item.quantity ?? 0) > 0) {
              const key = `${itemName} (x${item.quantity})`;
              itemsSold[key] = (itemsSold[key] ?? 0) + item.quantity;
            } else if ((item.weight_grams ?? 0) > 0) {
              const key = `${itemName} (${item.weight_grams} gm)`;
              itemsSold[key] = (itemsSold[key] ?? 0) + item.weight_grams;
            }
          }
        }
      }

      const lines = [
        `Sales Report for '${outletId ?? 'all outlets'}' (${startDate} to ${endDate}):`,
        `Total Sales: ₹${totalSales.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`,
        'Items Sold:',
        ...Object.keys(itemsSold).sort().map((k) => `  - ${k}`),
      ];

      return jsonResponse({ report: lines.join('\n') });
    }

    // ---- GET /sales/structured-report/ ----
    if (req.method === 'GET' && pathname.includes('structured-report')) {
      const startDate = url.searchParams.get('start_date');
      const endDate = url.searchParams.get('end_date');
      const outletId = url.searchParams.get('outlet_id');

      let query = db.from('sales').select('*').order('date').order('timestamp');
      if (startDate) query = query.gte('date', startDate);
      if (endDate) query = query.lte('date', endDate);
      if (outletId && outletId !== 'All Outlets') query = query.eq('outlet_id', outletId);

      const { data, error } = await query;
      if (error) throw error;
      return jsonResponse(data ?? []);
    }

    // ---- GET /sales/customer-transactions-report/ ----
    if (req.method === 'GET' && pathname.includes('customer-transactions-report')) {
      const customerId = url.searchParams.get('customer_id');
      const startDate = url.searchParams.get('start_date');
      const endDate = url.searchParams.get('end_date');

      let query = db.from('sales').select('*').order('customer_id').order('timestamp');
      if (customerId) query = query.eq('customer_id', customerId);
      if (startDate) query = query.gte('date', startDate);
      if (endDate) query = query.lte('date', endDate);

      const { data, error } = await query;
      if (error) throw error;

      const customerTx: Record<string, unknown> = {};
      for (const record of data ?? []) {
        const cId = record.customer_id ?? 'anonymous';
        if (!customerTx[cId]) {
          customerTx[cId] = { customer_id: cId, total_spent: 0, visit_count: 0, transactions: [] };
        }
        const c = customerTx[cId] as Record<string, unknown>;
        (c.total_spent as number) += record.total_amount ?? 0;
        (c.visit_count as number) += 1;
        (c.transactions as unknown[]).push({
          timestamp: record.timestamp,
          total_amount: record.total_amount,
          payment_method: record.payment_method,
          payment_status: record.payment_status,
        });
      }

      return jsonResponse({ structured_data: customerTx });
    }

    // ---- GET /sales/history/ ----
    if (req.method === 'GET' && pathname.includes('history')) {
      const startDate = url.searchParams.get('start_date');
      const endDate = url.searchParams.get('end_date');

      let query = db.from('sales').select('*').order('date', { ascending: false }).order('timestamp', { ascending: false });
      if (startDate) query = query.gte('date', startDate);
      if (endDate) query = query.lte('date', endDate);

      const { data, error } = await query;
      if (error) throw error;
      return jsonResponse(data ?? []);
    }

    // ---- DELETE /sales/delete-range/ ----
    if (req.method === 'DELETE' && pathname.includes('delete-range')) {
      const startDate = url.searchParams.get('start_date');
      const endDate = url.searchParams.get('end_date');
      const outletId = url.searchParams.get('outlet_id');

      if (!startDate || !endDate) {
        return errorResponse('Start date and end date are required for deletion.', 400);
      }

      let query = db.from('sales').delete().gte('date', startDate).lte('date', endDate);
      if (outletId && outletId !== 'All Outlets') query = query.eq('outlet_id', outletId);

      const { data, error } = await query;
      if (error) throw error;
      const deleted = (data as unknown[])?.length ?? 0;
      return jsonResponse({ message: `Successfully deleted ${deleted} sales records.` });
    }

    // ---- GET /sales/find/:numeric_bill_id/ ----
    const findMatch = pathname.match(/\/find\/([^/]+)\/?$/);
    if (req.method === 'GET' && findMatch) {
      const billId = findMatch[1];
      const { data, error } = await db.from('sales').select('*').eq('numeric_bill_id', billId).limit(1);
      if (error) throw error;
      if (!data?.length) return errorResponse('Bill not found with that number.', 404);
      return jsonResponse(data[0]);
    }

    // ---- GET /sales/:sale_id/ ----
    const saleIdMatch = pathname.match(/\/sales\/([^/]+)\/?$/);
    if (req.method === 'GET' && saleIdMatch) {
      const saleId = saleIdMatch[1];
      const { data, error } = await db.from('sales').select('*').eq('id', saleId).single();
      if (error || !data) return errorResponse('Bill not found with that ID', 404);
      return jsonResponse(data);
    }

    return errorResponse('Not found', 404);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    console.error('sales error:', msg);
    return errorResponse(msg);
  }
});
