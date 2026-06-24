// supabase/functions/ownerbot/index.ts
// AI-powered owner bot with Gemini, Google Translate, Google TTS, voice order parsing
//
// POST /ownerbot/ask/           → text-based ownerbot query (Gemini AI)
// POST /ownerbot/parse-order/   → parse voice order text into structured items

import { handleOptions, jsonResponse, errorResponse } from '../_shared/cors.ts';
import { getSupabaseAdmin } from '../_shared/supabase.ts';

const GOOGLE_API_KEY = Deno.env.get('GOOGLE_API_KEY') ?? '';
const GOOGLE_CLOUD_PROJECT = Deno.env.get('GOOGLE_CLOUD_PROJECT') ?? '';
const GOOGLE_TTS_API_KEY = Deno.env.get('GOOGLE_TTS_API_KEY') ?? GOOGLE_API_KEY;

// ---------- Helper: Call Groq API ----------
async function callGroq(prompt: string): Promise<string> {
  const GROQ_API_KEY = Deno.env.get('GROQ_API_KEY') ?? '';
  const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${GROQ_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model: 'llama-3.3-70b-versatile',
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.2
    })
  });
  const json = await res.json();
  return json?.choices?.[0]?.message?.content ?? '';
}

// ---------- Helper: Transcribe Audio (Groq Whisper API) ----------
async function transcribeAudioGroq(audioBlob: Blob): Promise<string> {
  const GROQ_API_KEY = Deno.env.get('GROQ_API_KEY') ?? '';
  const formData = new FormData();
  formData.append('file', audioBlob, 'audio.webm');
  formData.append('model', 'whisper-large-v3');
  
  const res = await fetch('https://api.groq.com/openai/v1/audio/transcriptions', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${GROQ_API_KEY}` },
    body: formData
  });
  const json = await res.json();
  return json?.text ?? '';
}

// ---------- Helper: Detect language (Google Translate API) ----------
async function detectLanguage(text: string): Promise<string> {
  if (!GOOGLE_API_KEY) return 'en';
  try {
    const res = await fetch(
      `https://translation.googleapis.com/language/translate/v2/detect?key=${GOOGLE_API_KEY}`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ q: text }) }
    );
    const json = await res.json();
    return json?.data?.detections?.[0]?.[0]?.language ?? 'en';
  } catch {
    return 'en';
  }
}

// ---------- Helper: Translate text (Google Translate API) ----------
async function translateText(text: string, targetLang: string): Promise<string> {
  if (!GOOGLE_API_KEY || !text) return text;
  try {
    const res = await fetch(
      `https://translation.googleapis.com/language/translate/v2?key=${GOOGLE_API_KEY}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ q: text, target: targetLang.split('-')[0] }),
      }
    );
    const json = await res.json();
    return json?.data?.translations?.[0]?.translatedText ?? text;
  } catch {
    return text;
  }
}

// ---------- Helper: Text-to-Speech (Google TTS API) ----------
async function generateAudioResponse(text: string, lang: string): Promise<string | null> {
  if (!GOOGLE_TTS_API_KEY || !text) return null;
  const baseLang = lang.split('-')[0];
  const voiceMap: Record<string, { languageCode: string; name: string }> = {
    en: { languageCode: 'en-US', name: 'en-US-Wavenet-D' },
    ml: { languageCode: 'ml-IN', name: 'ml-IN-Wavenet-B' },
  };
  const voice = voiceMap[baseLang] ?? voiceMap['en'];

  try {
    const res = await fetch(
      `https://texttospeech.googleapis.com/v1/text:synthesize?key=${GOOGLE_TTS_API_KEY}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          input: { text },
          voice,
          audioConfig: { audioEncoding: 'MP3' },
        }),
      }
    );
    const json = await res.json();
    return json?.audioContent ?? null;
  } catch {
    return null;
  }
}

// ---------- Data Fetchers (for Gemini function calling context) ----------
async function getSalesReport(db: ReturnType<typeof getSupabaseAdmin>, startDate: string, endDate: string, outletId?: string): Promise<string> {
  let query = db.from('sales').select('total_amount,items').gte('date', startDate).lte('date', endDate);
  if (outletId && outletId !== 'All Outlets') query = query.eq('outlet_id', outletId);
  const { data } = await query;
  if (!data?.length) return `No sales data found for outlet '${outletId ?? 'all outlets'}' from ${startDate} to ${endDate}.`;

  const totalSales = data.reduce((s: number, r) => s + (r.total_amount ?? 0), 0);
  const itemsSold: Record<string, number> = {};
  for (const sale of data) {
    for (const item of sale.items ?? []) {
      if (item?.product_id) {
        const name = item.product_id.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase());
        if ((item.quantity ?? 0) > 0) itemsSold[`${name} (x${item.quantity})`] = (itemsSold[`${name} (x${item.quantity})`] ?? 0) + item.quantity;
        else if ((item.weight_grams ?? 0) > 0) itemsSold[`${name} (${item.weight_grams} gm)`] = (itemsSold[`${name} (${item.weight_grams} gm)`] ?? 0) + item.weight_grams;
      }
    }
  }

  return [
    `Sales Report for '${outletId ?? 'all outlets'}' (${startDate} to ${endDate}):`,
    `Total Sales: ₹${totalSales.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`,
    'Items Sold:',
    ...Object.keys(itemsSold).sort().map((k) => `  - ${k}`),
  ].join('\n');
}

async function getProfitReport(db: ReturnType<typeof getSupabaseAdmin>, startDate: string, endDate: string): Promise<string> {
  const [salesRes, prodRes, expRes] = await Promise.all([
    db.from('sales').select('total_amount').gte('date', startDate).lte('date', endDate),
    db.from('production_logs').select('total_cost').gte('date', startDate).lte('date', endDate),
    db.from('expenses').select('amount').gte('date', startDate).lte('date', endDate),
  ]);
  const revenue = (salesRes.data ?? []).reduce((s: number, r) => s + (r.total_amount ?? 0), 0);
  const cogs = (prodRes.data ?? []).reduce((s: number, r) => s + (r.total_cost ?? 0), 0);
  const opExpenses = (expRes.data ?? []).reduce((s: number, r) => s + (r.amount ?? 0), 0);
  const netProfit = revenue - (cogs + opExpenses);
  return [
    `Profit & Loss Report for ${startDate} to ${endDate}:`,
    `- Total Revenue:      ₹${revenue.toFixed(2)}`,
    `- Cost of Goods:     -₹${cogs.toFixed(2)}`,
    `- Operating Expenses: -₹${opExpenses.toFixed(2)}`,
    `----------------------------------`,
    `- Net Profit:         ₹${netProfit.toFixed(2)}`,
  ].join('\n');
}

async function getInventoryReport(db: ReturnType<typeof getSupabaseAdmin>): Promise<string> {
  const { data } = await db.from('items').select('name,stock').order('name');
  if (!data?.length) return 'No inventory items found.';
  return ['Current Inventory Report:', ...data.map((d) => `- ${d.name}: ${d.stock ?? 0} units`)].join('\n');
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return handleOptions();

  const db = getSupabaseAdmin();
  const url = new URL(req.url);
  const pathname = url.pathname;

  try {
    // ---- POST /ownerbot/ask/ ----
    if (req.method === 'POST' && pathname.includes('/ask')) {
      let userMsg = '';
      
      const contentType = req.headers.get('content-type') ?? '';
      if (contentType.includes('multipart/form-data')) {
        const formData = await req.formData();
        const audioFile = formData.get('audio');
        if (audioFile && audioFile instanceof Blob) {
          userMsg = await transcribeAudioGroq(audioFile);
        }
      } else {
        const body = await req.json();
        userMsg = body.question ?? '';
      }

      if (!userMsg) return errorResponse('No message received.', 400);

      // Detect language & translate to English
      const originalLang = await detectLanguage(userMsg);
      const msgEn = originalLang !== 'en' ? await translateText(userMsg, 'en') : userMsg;

      // Fetch available outlets for context
      const { data: outletsData } = await db.from('outlets').select('id,name');
      const availableOutlets = (outletsData ?? []).map((o: { id: string; name: string }) => ({ id: o.id, name: o.name }));

      const today = new Date().toISOString().split('T')[0];
      const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];

      // Build a comprehensive prompt that includes data-fetching instructions
      const systemContext = `You are an expert data analyst for Asthana Bakery. Today's date is ${today}.
Available outlets: ${JSON.stringify(availableOutlets)}.
RULES:
1. "today" = ${today}, "yesterday" = ${yesterday}.
2. If asked about "profit", "loss", or "earnings", respond with P&L data.
3. For specific data queries, compute date ranges and outlet filters from context.
4. Respond concisely and in a friendly tone.`;

      // For function calling, we build a two-pass prompt:
      // First pass: determine what data to fetch
      const intentPrompt = `${systemContext}

User question: "${msgEn}"

Based on the question, respond with ONLY a JSON object specifying what data to fetch:
{
  "action": "sales_report" | "profit_report" | "inventory_report" | "general_answer",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "outlet_id": "outlet_id or null",
  "answer": "direct answer if action is general_answer"
}`;

      const intentRaw = await callGroq(intentPrompt);
      let textEn = '';

      try {
        const cleaned = intentRaw.replace(/```json|```/g, '').trim();
        const intent = JSON.parse(cleaned);

        if (intent.action === 'sales_report') {
          textEn = await getSalesReport(db, intent.start_date ?? today, intent.end_date ?? today, intent.outlet_id);
        } else if (intent.action === 'profit_report') {
          textEn = await getProfitReport(db, intent.start_date ?? today, intent.end_date ?? today);
        } else if (intent.action === 'inventory_report') {
          textEn = await getInventoryReport(db);
        } else {
          textEn = intent.answer ?? await callGroq(`${systemContext}\n\nUser: ${msgEn}\nAssistant:`);
        }
      } catch {
        textEn = await callGroq(`${systemContext}\n\nUser: ${msgEn}\nAssistant:`);
      }

      // Translate response back to original language
      const finalText = originalLang !== 'en' ? await translateText(textEn, originalLang) : textEn;

      // Generate audio (first sentence only for speed)
      const summaryForSpeech = finalText.split('\n')[0];
      const audioText = originalLang !== 'en' ? await translateText(summaryForSpeech, originalLang) : summaryForSpeech;
      const audioB64 = await generateAudioResponse(audioText, originalLang);

      return jsonResponse({ text_response: finalText, audio_response: audioB64 });
    }

    // ---- POST /ownerbot/parse-order/ ----
    if (req.method === 'POST' && pathname.includes('/parse-order')) {
      let spokenText = '';
      
      const contentType = req.headers.get('content-type') ?? '';
      if (contentType.includes('multipart/form-data')) {
        const formData = await req.formData();
        const audioFile = formData.get('audio');
        if (audioFile && audioFile instanceof Blob) {
          spokenText = await transcribeAudioGroq(audioFile);
        }
      } else {
        const body = await req.json();
        spokenText = body.text ?? '';
      }

      if (!spokenText) return errorResponse('No audio or text received.', 400);

      // Fetch all products for matching
      const { data: products } = await db.from('items').select('id,name,malayalam_name,unit_type');
      if (!products?.length) return errorResponse('No products found in the database to match against.', 500);

      const availableProducts = products.map((p) => ({
        id: p.id,
        name: (p.name ?? '').toLowerCase(),
        malayalam_name: (p.malayalam_name ?? '').toLowerCase(),
        unit_type: p.unit_type ?? 'piece',
      }));

      const prompt = `You are a highly accurate billing assistant for a bakery in Kerala, India.
Your task is to analyze a spoken order and convert it into a structured JSON list.
The order can be in Malayalam, English, or a mix (Manglish).

Here is the list of available products with their English and Malayalam names:
${JSON.stringify(availableProducts, null, 2)}

The spoken order is: "${spokenText}"

Follow these rules VERY STRICTLY:
1. Match the words in the order to a product from the list.
2. If a number is followed by 'രൂപക്ക്', 'roopakku', 'rs', 'rupees', or preceded by 'for', it is ALWAYS a "custom_price".
3. If a number is followed by 'kg', 'kilo', 'gram', 'gm', 'കിലോ', 'ഗ്രാം', it is ALWAYS "weight_grams". Convert to grams (e.g., 'അര കിലോ' = 500 grams).
4. If a number (like 'രണ്ട്' or '2') appears with a piece item, it is "quantity".
5. If no number is specified for a 'piece' item, assume "quantity" is 1.
6. The 'item_id' MUST BE the exact 'id' from the product list.
7. If you cannot identify a product, return an empty list: [].

Your output MUST be ONLY a valid JSON list of objects. No explanation.

Example: "two puffs" → [{"item_id": "puff", "quantity": 2}]
Example: "oru kilo mixture" → [{"item_id": "mixture", "weight_grams": 1000}]
Example: "20 രൂപക്ക് ലഡു" → [{"item_id": "laddu", "custom_price": 20}]`;

      const rawResponse = await callGroq(prompt);
      const cleaned = rawResponse.trim().replace(/```json|```/g, '').trim();

      if (!cleaned) return jsonResponse([]);

      try {
        const parsed = JSON.parse(cleaned);
        if (!Array.isArray(parsed)) throw new Error('AI did not return a list.');
        return jsonResponse(parsed);
      } catch {
        return errorResponse(`Sorry, I could not understand the order: '${spokenText}'.`, 400);
      }
    }

    return errorResponse('Not found', 404);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    console.error('ownerbot error:', msg);
    return errorResponse(msg);
  }
});
