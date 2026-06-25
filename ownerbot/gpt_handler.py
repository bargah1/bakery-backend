# ===================================================================
# File: ownerbot/gpt_handler.py
# Rewritten to use Groq AI + Supabase (replaces Gemini + Firestore)
# ===================================================================
import os
import datetime
import json
import base64

from dotenv import load_dotenv
load_dotenv()

from groq import Groq
from bakery_ai_manager.supabase_client import get_supabase_client

# --- Optional: Google Cloud for TTS & Translation ---
try:
    from google.cloud import translate_v2 as translate, texttospeech
    import google.auth
    translate_client = None
    tts_client = None

    def _init_google_clients():
        global translate_client, tts_client
        try:
            credentials, project = google.auth.default()
            translate_client = translate.Client(credentials=credentials)
            tts_client = texttospeech.TextToSpeechClient(credentials=credentials)
            print("✅ Google Cloud TTS & Translation initialized.")
        except Exception as e:
            print(f"⚠️  Google Cloud TTS/Translation not available: {e}")
            print("   (Ownerbot will still work, but without voice/translation features)")

    _init_google_clients()
    GOOGLE_CLOUD_AVAILABLE = translate_client is not None
except ImportError:
    print("⚠️  Google Cloud libraries not installed. TTS/Translation disabled.")
    translate_client = None
    tts_client = None
    GOOGLE_CLOUD_AVAILABLE = False


# --- CONFIGURATION ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"

# --- INITIALIZE CLIENTS ---
groq_client = None
db = None

def initialize_clients():
    global groq_client, db
    try:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable is not set.")
        groq_client = Groq(api_key=GROQ_API_KEY)
        db = get_supabase_client()
        print("✅ Groq + Supabase clients initialized successfully.")
    except Exception as e:
        print(f"🔥 FATAL ERROR: Could not initialize clients: {e}")
        groq_client, db = None, None

initialize_clients()


# --- TOOL DEFINITIONS (OpenAI-compatible format for Groq) ---
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_sales_report",
            "description": "Fetches a sales report for a given date range and optional outlet. Use this when the user asks about sales, revenue, or transactions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    },
                    "outlet_id": {
                        "type": "string",
                        "description": "Optional outlet ID to filter by. Leave empty for all outlets."
                    }
                },
                "required": ["start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_profit_report",
            "description": "Calculates profit and loss including revenue, cost of goods sold, and expenses. Use when the user asks about profit, loss, earnings, or P&L.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    }
                },
                "required": ["start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_production_report",
            "description": "Fetches production data showing what was produced and in what quantities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format. Defaults to today."
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format. Defaults to today."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory_report",
            "description": "Fetches current inventory/stock levels for all products.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_staff_activity_report",
            "description": "Fetches staff attendance and activity data. Can filter by staff name and date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "staff_name": {
                        "type": "string",
                        "description": "Optional staff member name to filter by"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format. Defaults to today."
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format. Defaults to today."
                    }
                },
                "required": []
            }
        }
    }
]


# --- DATA FETCHING FUNCTIONS (Supabase) ---

def _get_staff_id_from_name(staff_name: str) -> str:
    """Finds a staff ID by matching the name in Supabase."""
    if not db or not staff_name:
        return None
    try:
        result = db.table('staff').select('id').ilike('name', f'%{staff_name}%').limit(1).execute()
        if result.data:
            staff_id = result.data[0]['id']
            print(f"DEBUG: Matched staff name '{staff_name}' to ID '{staff_id}'")
            return staff_id
    except Exception as e:
        print(f"WARN: Error looking up staff name '{staff_name}': {e}")
    return None


def get_sales_report(start_date: str, end_date: str, outlet_id: str = None) -> str:
    """Fetches a sales report from Supabase for a given date range and optional outlet."""
    if not db:
        return "Error: Database is not connected."
    try:
        query = db.table('sales').select('*').gte('date', start_date).lte('date', end_date)
        if outlet_id and outlet_id != 'All Outlets':
            query = query.eq('outlet_id', outlet_id)

        result = query.execute()
        docs = result.data

        if not docs:
            return f"No sales data found for outlet '{outlet_id or 'all outlets'}' from {start_date} to {end_date}."

        total_sales = sum(doc.get('total_amount', 0.0) for doc in docs)
        items_sold = {}
        for doc in docs:
            for item in doc.get('items', []):
                if isinstance(item, dict) and item.get('product_id'):
                    item_name = item.get('product_id').replace('_', ' ').title()
                    if item.get('quantity', 0) > 0:
                        key = f"{item_name} (x{item.get('quantity')})"
                        items_sold[key] = items_sold.get(key, 0) + item.get('quantity')
                    elif item.get('weight_grams', 0.0) > 0:
                        key = f"{item_name} ({item.get('weight_grams')} gm)"
                        items_sold[key] = items_sold.get(key, 0.0) + item.get('weight_grams')
                    elif item.get('custom_price', 0.0) > 0:
                        key = f"{item_name} (Custom Price)"
                        items_sold[key] = items_sold.get(key, 0.0) + item.get('custom_price')

        report_lines = [
            f"Sales Report for '{outlet_id or 'all outlets'}' ({start_date} to {end_date}):",
            f"Total Sales: ₹{total_sales:,.2f}",
            "Items Sold:"
        ]
        if not items_sold:
            report_lines.append("  - No items were sold.")
        else:
            for item_description in sorted(items_sold.keys()):
                report_lines.append(f"  - {item_description}")
        return "\n".join(report_lines)
    except Exception as e:
        return f"An error occurred while fetching the sales report: {e}"


def get_profit_report(start_date: str, end_date: str) -> str:
    """Calculates profit and loss from Supabase data."""
    if not db:
        return "Error: Database is not connected."
    try:
        # 1. Revenue
        sales_result = db.table('sales').select('total_amount').gte('date', start_date).lte('date', end_date).execute()
        total_revenue = sum(row.get('total_amount', 0.0) for row in sales_result.data)

        # 2. Cost of Goods Sold (from production logs)
        prod_result = db.table('production_logs').select('total_cost').gte('date', start_date).lte('date', end_date).execute()
        cogs = sum(row.get('total_cost', 0.0) for row in prod_result.data)

        # 3. Operating Expenses
        expenses_result = db.table('expenses').select('amount').gte('date', start_date).lte('date', end_date).execute()
        op_expenses = sum(row.get('amount', 0.0) for row in expenses_result.data)

        # 4. Net Profit
        net_profit = total_revenue - (cogs + op_expenses)

        report = (
            f"Profit & Loss Report for {start_date} to {end_date}:\n"
            f"- Total Revenue:      ₹{total_revenue:,.2f}\n"
            f"- Cost of Goods: -₹{cogs:,.2f}\n"
            f"- Operating Expenses: -₹{op_expenses:,.2f}\n"
            f"----------------------------------\n"
            f"- Net Profit:      ₹{net_profit:,.2f}"
        )
        return report
    except Exception as e:
        return f"An error occurred while generating the profit report: {e}"


def get_production_report(start_date: str = None, end_date: str = None) -> str:
    """Fetches production data from Supabase."""
    if not db:
        return "Error: Database is not connected."
    try:
        today = datetime.date.today().isoformat()
        query = db.table('production_logs').select('recipe_id, quantity_produced')

        if start_date:
            query = query.gte('date', start_date)
        if end_date:
            query = query.lte('date', end_date)
        if not start_date and not end_date:
            query = query.eq('date', today)

        result = query.execute()
        if not result.data:
            return "No production data found."

        produced = {}
        for row in result.data:
            recipe = row.get('recipe_id', 'Unknown')
            produced[recipe] = produced.get(recipe, 0) + row.get('quantity_produced', 0)

        report = "Production Report:\n" + "\n".join(
            [f"  - {p.replace('_', ' ').title()}: {q} units" for p, q in sorted(produced.items())]
        )
        return report
    except Exception as e:
        return f"An error occurred while fetching production report: {e}"


def get_inventory_report() -> str:
    """Fetches current inventory from Supabase."""
    if not db:
        return "Error: Database is not connected."
    try:
        result = db.table('items').select('name, stock').order('name').execute()
        if not result.data:
            return "No inventory items found."

        report_lines = ["Current Inventory Report:\n"]
        for item in result.data:
            report_lines.append(f"- {item.get('name', 'Unknown')}: {item.get('stock', 0)} units")
        return "\n".join(report_lines)
    except Exception as e:
        return f"An error occurred while fetching inventory: {e}"


def get_staff_activity_report(staff_name: str = None, start_date: str = None, end_date: str = None) -> str:
    """Fetches staff attendance data from Supabase."""
    if not db:
        return "Error: Database is not connected."
    try:
        today = datetime.date.today().isoformat()
        start_date = start_date or today
        end_date = end_date or today

        staff_id_to_filter = _get_staff_id_from_name(staff_name) if staff_name else None
        if staff_name and not staff_id_to_filter:
            return f"I could not find any staff member named '{staff_name}'."

        # Fetch attendance records
        query = db.table('attendance_records').select('*').gte('date', start_date).lte('date', end_date)
        if staff_id_to_filter:
            query = query.eq('staff_id', staff_id_to_filter)

        result = query.order('timestamp').execute()
        all_events = []

        for record in result.data:
            all_events.append({
                "ts": record.get('timestamp'),
                "name": record.get('staff_name', 'Unknown'),
                "event": f"Manually {record.get('punch_type', 'punched').replace('_', ' ')} at {record.get('location_id', 'N/A')}."
            })

        # Fetch CCTV observations
        cctv_query = db.table('cctv_observations').select('*').gte('date', start_date).lte('date', end_date)
        if staff_name:
            cctv_query = cctv_query.eq('staff_name', staff_name)

        cctv_result = cctv_query.execute()
        for record in cctv_result.data:
            all_events.append({
                "ts": record.get('timestamp'),
                "name": record.get('staff_name', 'Unknown'),
                "event": f"Spotted by CCTV on {record.get('camera_id', 'N/A')}."
            })

        if not all_events:
            return f"No activities found for '{staff_name or 'any staff'}'."

        all_events.sort(key=lambda x: x.get('ts', ''))
        report = [f"Activity Report for {staff_name or 'All Staff'} ({start_date} to {end_date}):\n"]
        current_staff = None
        for event in all_events:
            if not staff_name and event['name'] != current_staff:
                current_staff = event['name']
                report.append(f"\n--- {current_staff} ---")
            try:
                dt = datetime.datetime.fromisoformat(event['ts'])
                report.append(f"  - At {dt.strftime('%I:%M:%S %p')}: {event['event']}")
            except Exception:
                report.append(f"  - At unknown time: {event['event']}")
        return "\n".join(report)
    except Exception as e:
        return f"An error occurred while fetching staff activity: {e}"


# --- Map function names to actual functions ---
AVAILABLE_FUNCTIONS = {
    "get_sales_report": get_sales_report,
    "get_profit_report": get_profit_report,
    "get_production_report": get_production_report,
    "get_inventory_report": get_inventory_report,
    "get_staff_activity_report": get_staff_activity_report,
}


# --- AI & LANGUAGE PROCESSING ---
def detect_language(text: str) -> dict:
    if not GOOGLE_CLOUD_AVAILABLE or not translate_client:
        return {'language': 'en'}
    try:
        result = translate_client.detect_language(text)
        if result.get('language') == 'ml':
            return {'language': 'ml'}
        return {'language': 'en'}
    except Exception as e:
        print(f"ERROR: Language detection failed: {e}")
        return {'language': 'en'}


def translate_text(text: str, target_lang: str) -> str:
    if not GOOGLE_CLOUD_AVAILABLE or not translate_client or not text:
        return text
    try:
        lang_code = target_lang.split('-')[0]
        result = translate_client.translate(text, target_language=lang_code)
        return result['translatedText']
    except Exception as e:
        print(f"ERROR: Translation failed: {e}")
        return text


def generate_audio_response(text: str, lang: str):
    if not GOOGLE_CLOUD_AVAILABLE or not tts_client or not text:
        return None
    base_lang = lang.split('-')[0]
    voice_map = {
        'en': ("en-US", "en-US-Wavenet-D"),
        'ml': ("ml-IN", "ml-IN-Wavenet-B")
    }
    lang_code, voice_name = voice_map.get(base_lang, voice_map['en'])
    voice = texttospeech.VoiceSelectionParams(language_code=lang_code, name=voice_name)
    s_input = texttospeech.SynthesisInput(text=text)
    a_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    try:
        response = tts_client.synthesize_speech(input=s_input, voice=voice, audio_config=a_config)
        return base64.b64encode(response.audio_content).decode('utf-8')
    except Exception as e:
        print(f"ERROR: TTS failed: {e}")
        return None


# --- MAIN BOT RESPONSE HANDLER (Groq + Supabase) ---
def get_ownerbot_response(message: str, mode: str = 'voice') -> dict:
    """
    Processes a user message using Groq AI with tool calling.
    Fetches data from Supabase via tool functions.
    """
    global groq_client, db

    if not groq_client:
        return {"text_response": "Error: AI model not loaded.", "audio_response": None}
    if not db:
        return {"text_response": "Error: Database not connected.", "audio_response": None}

    try:
        # Fetch available outlets for context
        outlets_result = db.table('outlets').select('id, name').execute()
        available_outlets = outlets_result.data if outlets_result.data else []
    except Exception:
        available_outlets = []

    today_date = datetime.date.today()

    system_prompt = f"""You are an expert data analyst for Asthana Bakery. Your main goal is to call the correct function to get reports and then present the data clearly to the owner.

Today's date is {today_date.strftime('%Y-%m-%d')}.
Available outlets: {json.dumps(available_outlets)}.

RULES:
1. Infer dates: "today" is {today_date.isoformat()}, "yesterday" is {(today_date - datetime.timedelta(days=1)).isoformat()}.
2. If the user asks about "profit", "loss", or "earnings", you MUST use the `get_profit_report` function.
3. For sales reports, if an outlet is not specified, use all outlets.
4. After a tool is called, present its output data directly as your final answer. Be concise and helpful.
5. Use ₹ for currency values.
6. If the user's question doesn't require data, answer conversationally."""

    # Detect language and translate to English for the AI
    original_lang = detect_language(message).get('language', 'en')
    msg_en = translate_text(message, 'en')

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": msg_en}
        ]

        # First call — the model may request tool calls
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            max_tokens=2048,
            temperature=0.3,
        )

        response_message = response.choices[0].message

        # If the model wants to call tools, execute them
        if response_message.tool_calls:
            messages.append(response_message)

            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                print(f"DEBUG: Groq calling tool '{function_name}' with args: {function_args}")

                # Execute the function
                func = AVAILABLE_FUNCTIONS.get(function_name)
                if func:
                    function_result = func(**function_args)
                else:
                    function_result = f"Error: Unknown function '{function_name}'"

                # Add the tool result to the conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(function_result)
                })

            # Second call — model summarizes the tool results
            second_response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                max_tokens=2048,
                temperature=0.3,
            )
            text_en = second_response.choices[0].message.content
        else:
            # No tool calls needed — direct response
            text_en = response_message.content

    except Exception as e:
        print(f"ERROR: Groq inference failed: {e}")
        text_en = "I'm sorry, I had trouble understanding that. Please rephrase."

    # Handle voice mode (translate back and generate audio)
    audio_b64 = None
    if mode == 'voice':
        summary_for_speech = text_en.split('\n')[0]
        final_text = translate_text(text_en, original_lang)
        audio_text = translate_text(summary_for_speech, original_lang)
        audio_b64 = generate_audio_response(audio_text, original_lang)
    else:
        final_text = text_en

    return {"text_response": final_text, "audio_response": audio_b64}


# --- VOICE ORDER PARSING (Groq) ---
def parse_voice_order(spoken_text: str):
    """
    Analyzes spoken text to identify bakery products and how they are being ordered.
    Uses Groq AI instead of Gemini.
    """
    global groq_client, db

    if not db:
        return {"error": "Database not connected."}
    if not groq_client:
        return {"error": "AI model not available."}

    print(f"DEBUG: Parsing smart voice order: '{spoken_text}'")

    try:
        # Fetch available products from Supabase
        result = db.table('items').select('id, name, malayalam_name, unit_type').execute()
        available_products_details = []
        for item in result.data:
            if item.get('name'):
                available_products_details.append({
                    "id": item['id'],
                    "name": item.get('name', '').lower(),
                    "malayalam_name": item.get('malayalam_name', '').lower(),
                    "unit_type": item.get('unit_type', 'piece')
                })

        if not available_products_details:
            return {"error": "No products found in the database to match against."}

        prompt = f"""You are a highly accurate billing assistant for a bakery in Kerala, India.
Your task is to analyze a spoken order and convert it into a structured JSON list.
The order can be in Malayalam, English, or a mix (Manglish).

Here is the list of available products with their English and Malayalam names:
{json.dumps(available_products_details, indent=2, ensure_ascii=False)}

The spoken order is: "{spoken_text}"

Follow these rules VERY STRICTLY:
1.  Match the words in the order to a product from the list. The match can be with the 'name' or the 'malayalam_name'.
2.  If a number is followed by 'രൂപക്ക്', 'roopakku', 'rs', or 'rupees', or preceded by 'for', it is ALWAYS a "custom_price".
3.  If a number is followed by 'kg', 'kilo', 'gram', or 'gm', or 'കിലോ', 'ഗ്രാം', it is ALWAYS "weight_grams". Convert all weights to grams (e.g., 'അര കിലോ' is 500 grams, '1 kg' is 1000 grams).
4.  If a number (like 'രണ്ട്' or '2') appears with a piece item, it is "quantity".
5.  If no number is specified for a 'piece' item, assume "quantity" is 1.
6.  The 'item_id' in your response MUST BE the exact 'id' from the product list for the matched product.
7.  If you cannot clearly identify a product or instruction, return an empty list: []

Your output MUST be ONLY a valid JSON list of objects. No markdown, no explanation.

Example 1 (piece): "two puffs" -> [{{"item_id": "puff_id", "quantity": 2}}]
Example 2 (weight): "oru kilo mixture" -> [{{"item_id": "mixture_id", "weight_grams": 1000}}]
Example 3 (price): "20 രൂപക്ക് ലഡു" -> [{{"item_id": "laddu_id", "custom_price": 20}}]
Example 4 (price): "madak for 100 rs" -> [{{"item_id": "madak_id", "custom_price": 100}}]
Example 5 (weight): "അര കിലോ ജിലേബി" -> [{{"item_id": "jilebi_id", "weight_grams": 500}}]
Example 6 (quantity): "രണ്ട് പഫ്" -> [{{"item_id": "puff_id", "quantity": 2}}]
Example 7 (multiple): "ഒരു കിലോ ബോണ്ടയും രണ്ട് സമൂസയും" -> [{{"item_id": "bonda_id", "weight_grams": 1000}}, {{"item_id": "samosa_id", "quantity": 2}}]"""

        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a JSON-only billing assistant. Respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1024,
            temperature=0.1,
        )

        cleaned_response = response.choices[0].message.content.strip()
        # Remove markdown code fences if present
        cleaned_response = cleaned_response.replace('```json', '').replace('```', '').strip()
        print(f"DEBUG: Parsed order from Groq: {cleaned_response}")

        if not cleaned_response:
            return []

        parsed_order = json.loads(cleaned_response)
        if not isinstance(parsed_order, list):
            raise ValueError("AI did not return a list.")
        return parsed_order

    except Exception as e:
        print(f"ERROR: Failed to parse voice order with Groq: {e}")
        return {"error": f"Sorry, I could not understand the order: '{spoken_text}'."}
