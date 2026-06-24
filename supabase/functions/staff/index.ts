// supabase/functions/staff/index.ts
// Handles all staff management endpoints
//
// POST   /staff/add/                              → add staff member
// GET    /staff/list/                             → list staff (optionally by location)
// DELETE /staff/delete/:staff_id/                 → delete staff
// PUT    /staff/edit/:staff_id/                   → edit staff
// POST   /staff/punch-attendance/                 → punch attendance (simple status)
// POST   /staff/attendance/mark/                  → alias for punch-attendance
// GET    /staff/attendance-report/                → attendance + salary report
// DELETE /staff/attendance/delete-range/          → bulk delete attendance logs
// GET    /staff/last-punch-status/:staff_id/      → last punch type
// POST   /staff/staff/salary/mark-paid/           → mark salary as paid/unpaid
// GET    /staff/cctv-observation-report/          → (disabled) returns stub

import { corsHeaders, handleOptions, jsonResponse, errorResponse } from '../_shared/cors.ts';
import { getSupabaseAdmin } from '../_shared/supabase.ts';

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return handleOptions();

  const db = getSupabaseAdmin();
  const url = new URL(req.url);
  const pathname = url.pathname;

  try {
    // ---- POST /staff/add/ ----
    if (req.method === 'POST' && pathname.includes('/add')) {
      const body = await req.json();
      const required = ['name', 'role', 'contact_number', 'salary'];
      for (const f of required) {
        if (!body[f]) return errorResponse(`Missing required field: ${f}`, 400);
      }

      const name = String(body.name).trim();
      const staffId = `${name.toLowerCase().replace(/ /g, '_')}_${Date.now()}`;

      // Check if exists
      const { data: existing } = await db.from('staff').select('id').eq('id', staffId).single();
      if (existing) return errorResponse(`Staff member '${name}' (ID: ${staffId}) already exists.`, 409);

      const staffData = {
        id: staffId,
        name,
        role: body.role,
        contact_number: body.contact_number,
        address: body.address ?? '',
        emergency_contact: body.emergency_contact ?? '',
        image_urls: body.image_urls ?? [],
        face_encodings: [],
        location_id: body.location_id ?? '',
        salary: parseFloat(body.salary),
        created_at: new Date().toISOString(),
      };

      const { error } = await db.from('staff').insert(staffData);
      if (error) throw error;
      return jsonResponse({ message: 'Staff member added successfully', staff_id: staffId }, 201);
    }

    // ---- GET /staff/list/ ----
    if (req.method === 'GET' && pathname.includes('/list')) {
      const locationId = url.searchParams.get('location_id');
      let query = db.from('staff').select('id,name,role,contact_number,address,emergency_contact,image_urls,location_id,salary,created_at').order('name');
      if (locationId) query = query.eq('location_id', locationId);
      const { data, error } = await query;
      if (error) throw error;
      return jsonResponse(data ?? []);
    }

    // ---- DELETE /staff/delete/:staff_id/ ----
    const deleteMatch = pathname.match(/\/delete\/([^/]+)\/?$/);
    if (req.method === 'DELETE' && deleteMatch) {
      const staffId = deleteMatch[1];
      const { data: existing } = await db.from('staff').select('id').eq('id', staffId).single();
      if (!existing) return errorResponse('Staff member not found', 404);
      const { error } = await db.from('staff').delete().eq('id', staffId);
      if (error) throw error;
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    // ---- PUT /staff/edit/:staff_id/ or /staff/staff/edit/:staff_id/ ----
    const editMatch = pathname.match(/\/edit\/([^/]+)\/?$/);
    if (req.method === 'PUT' && editMatch) {
      const staffId = editMatch[1];
      const body = await req.json();
      const updateData: Record<string, unknown> = {};
      if (body.name) updateData.name = body.name;
      if (body.role) updateData.role = body.role;
      if (body.contact_number) updateData.contact_number = body.contact_number;
      if (body.salary !== undefined) updateData.salary = parseFloat(body.salary);
      if (body.image_urls) updateData.image_urls = body.image_urls;

      const { error } = await db.from('staff').update(updateData).eq('id', staffId);
      if (error) throw error;
      return jsonResponse({ message: 'Staff member updated successfully', staff_id: staffId });
    }

    // ---- POST /staff/punch-attendance/ or /staff/attendance/mark/ ----
    if (req.method === 'POST' && (pathname.includes('punch-attendance') || pathname.includes('attendance/mark'))) {
      const body = await req.json();
      const { date: attendanceDate, attendance: records } = body;

      if (!attendanceDate || !records) {
        return errorResponse('Missing date or attendance data', 400);
      }

      const toInsert = [];
      for (const record of records) {
        const { staff_id, status } = record;
        if (!staff_id || !status) continue;
        toInsert.push({
          id: `${staff_id}_${attendanceDate}`,
          staff_id,
          date: attendanceDate,
          status,
        });
      }

      if (toInsert.length) {
        const { error } = await db.from('attendance').upsert(toInsert);
        if (error) throw error;
      }

      return jsonResponse({ message: 'Attendance recorded successfully!' });
    }

    // ---- GET /staff/attendance-report/ ----
    if (req.method === 'GET' && pathname.includes('attendance-report')) {
      const staffId = url.searchParams.get('staff_id');
      const startDate = url.searchParams.get('start_date');
      const endDate = url.searchParams.get('end_date');

      // Fetch staff
      let staffQuery = db.from('staff').select('id,name,salary');
      if (staffId && staffId !== 'All Staff') staffQuery = staffQuery.eq('id', staffId);
      const { data: staffData } = await staffQuery;
      const staffMap: Record<string, { name: string; salary: number }> = {};
      for (const s of staffData ?? []) staffMap[s.id] = { name: s.name, salary: s.salary };

      // Fetch attendance punches
      let attQuery = db.from('attendance_records').select('*').order('timestamp');
      if (startDate) attQuery = attQuery.gte('date', startDate);
      if (endDate) attQuery = attQuery.lte('date', endDate);
      if (staffId && staffId !== 'All Staff') attQuery = attQuery.eq('staff_id', staffId);
      const { data: punches } = await attQuery;

      // Group punches by staff
      const punchMap: Record<string, { punch_type: string; timestamp: string; date: string }[]> = {};
      for (const punch of punches ?? []) {
        if (!punchMap[punch.staff_id]) punchMap[punch.staff_id] = [];
        punchMap[punch.staff_id].push(punch);
      }

      // Build salary report
      const report = [];
      for (const [sId, details] of Object.entries(staffMap)) {
        const staffPunches = punchMap[sId] ?? [];
        const presentDays = new Set<string>();
        let totalMs = 0;
        let clockInTime: Date | null = null;

        for (const punch of staffPunches) {
          presentDays.add(punch.date);
          const t = new Date(punch.timestamp);
          if (punch.punch_type === 'clock_in') {
            clockInTime = t;
          } else if (punch.punch_type === 'clock_out' && clockInTime) {
            totalMs += t.getTime() - clockInTime.getTime();
            clockInTime = null;
          }
        }

        const daysPresent = presentDays.size;
        const hoursWorked = totalMs / 3_600_000;
        const salaryDue = details.salary * daysPresent;

        // Check salary payment
        const paymentId = `${sId}_${startDate}_${endDate}`;
        const { data: payment } = await db.from('salary_payments').select('id').eq('id', paymentId).single();

        report.push({
          staff_id: sId,
          staff_name: details.name,
          total_days_present: daysPresent,
          total_hours_worked: Math.round(hoursWorked * 100) / 100,
          total_salary_due: Math.round(salaryDue * 100) / 100,
          is_paid: !!payment,
        });
      }

      return jsonResponse(report);
    }

    // ---- DELETE /staff/attendance/delete-range/ ----
    if (req.method === 'DELETE' && pathname.includes('attendance/delete-range')) {
      const startDate = url.searchParams.get('start_date');
      const endDate = url.searchParams.get('end_date');
      const staffId = url.searchParams.get('staff_id');

      if (!startDate || !endDate) return errorResponse('Start date and end date are required for deletion.', 400);

      let query = db.from('attendance_records').delete().gte('date', startDate).lte('date', endDate);
      if (staffId && staffId !== 'All Staff') query = query.eq('staff_id', staffId);

      const { data, error } = await query;
      if (error) throw error;
      return jsonResponse({ message: `Successfully deleted ${(data as unknown[])?.length ?? 0} attendance records.` });
    }

    // ---- GET /staff/last-punch-status/:staff_id/ ----
    const lastPunchMatch = pathname.match(/last-punch-status\/([^/]+)\/?$/);
    if (req.method === 'GET' && lastPunchMatch) {
      const staffId = lastPunchMatch[1];
      const { data } = await db
        .from('attendance_records')
        .select('punch_type')
        .eq('staff_id', staffId)
        .order('timestamp', { ascending: false })
        .limit(1);

      if (!data?.length) return jsonResponse({ last_punch: 'none' });
      return jsonResponse({ last_punch: data[0].punch_type });
    }

    // ---- POST /staff/staff/salary/mark-paid/ ----
    if (req.method === 'POST' && pathname.includes('salary/mark-paid')) {
      const body = await req.json();
      const { staff_id, start_date, end_date, amount, status: isPaid } = body;

      if (!staff_id || !start_date || !end_date || amount === undefined || isPaid === undefined) {
        return errorResponse('Missing required fields', 400);
      }

      const paymentId = `${staff_id}_${start_date}_${end_date}`;
      const expenseId = `salary_${paymentId}`;

      if (isPaid === true) {
        await db.from('salary_payments').upsert({
          id: paymentId,
          staff_id,
          amount,
          payment_date: new Date().toISOString().split('T')[0],
          period_start: start_date,
          period_end: end_date,
          expense_doc_id: expenseId,
        });
        await db.from('expenses').upsert({
          id: expenseId,
          category: 'Salary',
          amount,
          date: new Date().toISOString().split('T')[0],
          description: `Salary for staff ID ${staff_id} for period ${start_date} to ${end_date}`,
        });
        return jsonResponse({ message: 'Salary marked as paid and expense recorded.' });
      } else {
        await db.from('salary_payments').delete().eq('id', paymentId);
        await db.from('expenses').delete().eq('id', expenseId);
        return jsonResponse({ message: 'Salary payment and expense record reverted.' });
      }
    }

    // ---- GET /staff/cctv-observation-report/ ---- (disabled stub)
    if (req.method === 'GET' && pathname.includes('cctv-observation-report')) {
      return jsonResponse({ report: 'CCTV reporting is disabled in this version.', structured_data: {} });
    }

    // ---- POST /staff/record-cctv-observation/ ---- (disabled stub)
    if (req.method === 'POST' && pathname.includes('record-cctv-observation')) {
      return errorResponse('CCTV observation is disabled in this version.', 404);
    }

    return errorResponse('Not found', 404);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    console.error('staff error:', msg);
    return errorResponse(msg);
  }
});
