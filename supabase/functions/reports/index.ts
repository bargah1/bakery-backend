// supabase/functions/reports/index.ts
// Handles all report & dashboard endpoints
//
// GET /reports/dashboard-summary/     → KPIs for today
// GET /reports/profit-loss/           → P&L report
// GET /reports/low-stock-alerts/      → low stock alerts
// DELETE /reports/clear-data/         → clear sales & expenses in range

import { handleOptions, jsonResponse, errorResponse } from '../_shared/cors.ts';
import { getSupabaseAdmin } from '../_shared/supabase.ts';

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return handleOptions();

  const db = getSupabaseAdmin();
  const url = new URL(req.url);
  const pathname = url.pathname;

  try {
    // ---- GET /reports/dashboard-summary/ ----
    if (req.method === 'GET' && pathname.includes('dashboard-summary')) {
      const today = new Date().toISOString().split('T')[0];

      const [salesRes, prodRes, expRes, staffRes] = await Promise.all([
        db.from('sales').select('total_amount,items').eq('date', today),
        db.from('production_logs').select('total_cost').eq('date', today),
        db.from('expenses').select('amount').eq('date', today),
        db.from('staff').select('salary'),
      ]);

      const todaysRevenue = (salesRes.data ?? []).reduce((s: number, r) => s + (r.total_amount ?? 0), 0);
      const todaysCogs = (prodRes.data ?? []).reduce((s: number, r) => s + (r.total_cost ?? 0), 0);
      const todaysOpExpenses = (expRes.data ?? []).reduce((s: number, r) => s + (r.amount ?? 0), 0);
      const totalDailySalaryCost = (staffRes.data ?? []).reduce((s: number, r) => s + (r.salary ?? 0) * 8, 0);

      // Top selling item
      const itemCounts: Record<string, number> = {};
      for (const sale of salesRes.data ?? []) {
        for (const item of sale.items ?? []) {
          if (item?.product_id) {
            itemCounts[item.product_id] = (itemCounts[item.product_id] ?? 0) +
              (item.quantity ?? 0) + (item.weight_grams ?? 0) / 1000;
          }
        }
      }
      const topItem = Object.entries(itemCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'N/A';

      const todaysProfit = todaysRevenue - (todaysCogs + todaysOpExpenses + totalDailySalaryCost);

      return jsonResponse({
        todays_revenue: todaysRevenue,
        todays_profit: todaysProfit,
        top_selling_item: topItem.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
      });
    }

    // ---- GET /reports/profit-loss/ ----
    if (req.method === 'GET' && pathname.includes('profit-loss')) {
      const startDate = url.searchParams.get('start_date');
      const endDate = url.searchParams.get('end_date');

      if (!startDate || !endDate) return errorResponse('Start date and end date are required.', 400);

      const [salesRes, prodRes, expRes, attendanceRes, staffRes] = await Promise.all([
        db.from('sales').select('total_amount,items').gte('date', startDate).lte('date', endDate),
        db.from('production_logs').select('total_cost').gte('date', startDate).lte('date', endDate),
        db.from('expenses').select('amount,category').gte('date', startDate).lte('date', endDate),
        db.from('attendance_records').select('staff_id,punch_type,timestamp').gte('date', startDate).lte('date', endDate).order('timestamp'),
        db.from('staff').select('id,salary'),
      ]);

      // Revenue & wholesale COGS
      let totalRevenue = 0;
      let costOfGoodsSold = 0;
      for (const sale of salesRes.data ?? []) {
        totalRevenue += sale.total_amount ?? 0;
      }

      // Production COGS
      const productionCogs = (prodRes.data ?? []).reduce((s: number, r) => s + (r.total_cost ?? 0), 0);
      costOfGoodsSold += productionCogs;

      // Operating expenses
      let totalOpExpenses = 0;
      const expenseBreakdown: Record<string, number> = {};
      for (const e of expRes.data ?? []) {
        totalOpExpenses += e.amount ?? 0;
        const cat = e.category ?? 'Uncategorized';
        expenseBreakdown[cat] = (expenseBreakdown[cat] ?? 0) + (e.amount ?? 0);
      }

      // Salary from actual clock-in/out
      const staffSalaries: Record<string, number> = {};
      for (const s of staffRes.data ?? []) staffSalaries[s.id] = s.salary;

      const staffHours: Record<string, { punches: { punch_type: string; timestamp: string }[] }> = {};
      for (const punch of attendanceRes.data ?? []) {
        if (!staffHours[punch.staff_id]) staffHours[punch.staff_id] = { punches: [] };
        staffHours[punch.staff_id].punches.push(punch);
      }

      let totalSalaryExpense = 0;
      for (const [sId, { punches }] of Object.entries(staffHours)) {
        let totalMs = 0;
        let clockIn: Date | null = null;
        for (const punch of punches) {
          const t = new Date(punch.timestamp);
          if (punch.punch_type === 'clock_in') clockIn = t;
          else if (punch.punch_type === 'clock_out' && clockIn) {
            totalMs += t.getTime() - clockIn.getTime();
            clockIn = null;
          }
        }
        const hours = totalMs / 3_600_000;
        totalSalaryExpense += hours * (staffSalaries[sId] ?? 0);
      }

      if (totalSalaryExpense > 0) {
        expenseBreakdown['Salaries'] = (expenseBreakdown['Salaries'] ?? 0) + totalSalaryExpense;
      }

      const totalExpenses = costOfGoodsSold + totalOpExpenses + totalSalaryExpense;
      const netProfit = totalRevenue - totalExpenses;

      return jsonResponse({
        total_revenue: totalRevenue,
        cost_of_goods_sold: costOfGoodsSold,
        operating_expenses: totalOpExpenses,
        salary_expenses: totalSalaryExpense,
        total_expenses: totalExpenses,
        net_profit: netProfit,
        expense_breakdown: expenseBreakdown,
      });
    }

    // ---- GET /reports/low-stock-alerts/ ----
    if (req.method === 'GET' && pathname.includes('low-stock-alerts')) {
      const { data: products } = await db.from('items').select('name,stock,low_stock_threshold,unit');
      const { data: outlets } = await db.from('outlets').select('id,name').eq('type', 'production');
      const outletIds = (outlets ?? []).map((o: { id: string }) => o.id);
      const outletNames = Object.fromEntries((outlets ?? []).map((o: { id: string; name: string }) => [o.id, o.name]));

      const lowStockProducts = (products ?? []).filter(
        (p) => (p.stock ?? 0) <= (p.low_stock_threshold ?? 0)
      ).map((p) => ({ name: p.name, stock: p.stock, unit: p.unit ?? 'pieces', threshold: p.low_stock_threshold }));

      let lowStockIngredients: unknown[] = [];
      if (outletIds.length) {
        const { data: ings } = await db
          .from('outlet_ingredients')
          .select('name,stock,low_stock_threshold,unit,outlet_id')
          .in('outlet_id', outletIds);

        lowStockIngredients = (ings ?? []).filter(
          (i) => (i.stock ?? 0) <= (i.low_stock_threshold ?? 0)
        ).map((i) => ({
          name: i.name,
          stock: i.stock,
          unit: i.unit ?? 'kg',
          threshold: i.low_stock_threshold,
          outlet_name: outletNames[i.outlet_id] ?? i.outlet_id,
        }));
      }

      return jsonResponse({ low_stock_products: lowStockProducts, low_stock_ingredients: lowStockIngredients });
    }

    // ---- DELETE /reports/clear-data/ ----
    if (req.method === 'DELETE' && pathname.includes('clear-data')) {
      const startDate = url.searchParams.get('start_date');
      const endDate = url.searchParams.get('end_date');

      if (!startDate || !endDate) return errorResponse('Start date and end date are required for deletion.', 400);

      await Promise.all([
        db.from('sales').delete().gte('date', startDate).lte('date', endDate),
        db.from('expenses').delete().gte('date', startDate).lte('date', endDate),
      ]);

      return jsonResponse({ message: 'Sales and expense data for the selected range have been cleared.' });
    }

    return errorResponse('Not found', 404);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    console.error('reports error:', msg);
    return errorResponse(msg);
  }
});
