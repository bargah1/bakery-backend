# ===================================================================
# File: app.py (New Flask Application)
# ===================================================================
import os
import datetime
import json
import base64
# from flask import Flask, request, jsonify
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import translate_v2 as translate, texttospeech
import google.generativeai as genai
import google.auth
import numpy as np
import requests
import cv2 # Not directly used in the provided snippets, but kept as it was in your original

# --- For Speech-to-Text (using OpenAI Whisper locally) ---
import whisper
import tempfile # For creating temporary files
import shutil   # For cleaning up temporary directories

# --- CONFIGURATION ---
from dotenv import load_dotenv
load_dotenv()

# Set your Google Cloud Project ID and API Key in a .env file:
# GOOGLE_API_KEY="YOUR_GEMINI_API_KEY"
# GOOGLE_CLOUD_PROJECT="your-gcp-project-id"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")

app = Flask(__name__)

# --- INITIALIZE CLIENTS ---
# Initialize Google Cloud clients and Gemini model globally once
db = None
model = None
translate_client = None
tts_client = None
whisper_model = None # New: For Whisper STT

def initialize_clients():
    global db, model, translate_client, tts_client, whisper_model
    try:
        if not google.auth.default()[0]: # Check if credentials are set up
            # If running locally, you might need to set GOOGLE_APPLICATION_CREDENTIALS env var
            # or use `gcloud auth application-default login`
            print("WARNING: Google Cloud credentials not found. Some services may fail.")
            print("Please ensure GOOGLE_APPLICATION_CREDENTIALS is set or gcloud auth is configured.")

        credentials, project = google.auth.default()
        db = firestore.Client(project=PROJECT_ID, credentials=credentials)
        translate_client = translate.Client(credentials=credentials)
        tts_client = texttospeech.TextToSpeechClient(credentials=credentials)
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest') # Using latest for tool calling
        
        print("DEBUG: Initializing Whisper model...")
        # Choose a model size: "tiny", "base", "small", "medium", "large"
        # "base" is a good balance for testing, "small" for better accuracy.
        # "large" offers highest accuracy but is very resource intensive.
        whisper_model = whisper.load_model("base") # Or "small" for better Malayalam
        print("DEBUG: Whisper model loaded.")

        print("DEBUG: All services initialized successfully.")
    except Exception as e:
        print(f"FATAL ERROR: Could not initialize services. Error: {e}")
        db, model, translate_client, tts_client = None, None, None, None, None

# Call initialization once when the app starts
with app.app_context():
    initialize_clients()


# --- Helper Function to find staff ID from name ---
def _get_staff_id_from_name(staff_name: str) -> str:
    if not db or not staff_name: return None
    query = db.collection('staff').where(filter=FieldFilter("name", "==", staff_name)).limit(1)
    docs = list(query.stream())
    if docs:
        staff_id = docs[0].id
        print(f"DEBUG: Matched staff name '{staff_name}' to ID '{staff_id}'")
        return staff_id
    
    print(f"WARN: Could not find a staff ID for the name '{staff_name}'.")
    return None

# --- DATA FETCHING TOOLS (Firestore Functions) ---
def get_sales_report(start_date: str, end_date: str, outlet_id: str = None):
    """Fetches a sales report for a given date range and optional outlet."""
    global db # Ensure db is accessible
    if not db: return "Error: Database is not connected."
    try:
        query = db.collection('sales')
        query = query.where(filter=FieldFilter('date', '>=', start_date))
        query = query.where(filter=FieldFilter('date', '<=', end_date))
        if outlet_id and outlet_id != 'All Outlets':
            query = query.where(filter=FieldFilter('outlet_id', '==', outlet_id))
        
        docs = list(query.stream())
        if not docs:
            return f"No sales data found for outlet '{outlet_id or 'all outlets'}' from {start_date} to {end_date}."

        total_sales = sum(doc.to_dict().get('total_amount', 0.0) for doc in docs)
        items_sold = {}
        for doc in docs:
            for item in doc.to_dict().get('items', []):
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

def get_production_report(start_date: str = None, end_date: str = None):
    global db
    if not db: return "Error: Firestore is not connected."
    query = db.collection('production')
    today = datetime.date.today().isoformat()
    if start_date: query = query.where(filter=FieldFilter('date', '>=', start_date))
    if end_date: query = query.where(filter=FieldFilter('date', '<=', end_date))
    if not start_date and not end_date: query = query.where(filter=FieldFilter('date', '==', today))
    results = list(query.stream())
    if not results: return "No production data found."
    produced = {}
    for doc in results:
        data = doc.to_dict()
        produced[data.get('product_id')] = produced.get(data.get('product_id'), 0) + data.get('quantity_produced', 0)
    report = "Production Report:\n" + "\n".join([f"  - {p.replace('_', ' ').title()}: {q} units" for p, q in sorted(produced.items())])
    return report

def get_inventory_report():
    global db
    if not db: return "Error: Firestore is not connected."
    product_list = list(db.collection('items').order_by('name').stream())
    if not product_list: return "No inventory items found."
    report_lines = ["Current Inventory Report:\n"] + [f"- {doc.to_dict().get('name', 'Unknown')}: {doc.to_dict().get('stock', 0)} units" for doc in product_list]
    return "\n".join(report_lines)

def get_staff_activity_report(staff_name: str = None, start_date: str = None, end_date: str = None):
    global db
    if not db: return "Error: Firestore is not connected."
    today, all_events = datetime.date.today(), []
    start_date = start_date or today.isoformat()
    end_date = end_date or today.isoformat()
    staff_id_to_filter = _get_staff_id_from_name(staff_name) if staff_name else None
    if staff_name and not staff_id_to_filter: return f"I could not find any staff member named '{staff_name}'."

    att_q = db.collection('attendance_records').where(filter=FieldFilter('date', '>=', start_date)).where(filter=FieldFilter('date', '<=', end_date))
    if staff_id_to_filter: att_q = att_q.where(filter=FieldFilter('staff_id', '==', staff_id_to_filter))
    for doc in att_q.stream():
        d = doc.to_dict()
        all_events.append({"ts": d.get('timestamp'), "name": d.get('staff_name'), "event": f"Manually {d.get('punch_type', 'punched').replace('_', ' ')} at {d.get('location_id', 'N/A')}."})

    cctv_q = db.collection('cctv_observations').where(filter=FieldFilter('date', '>=', start_date)).where(filter=FieldFilter('date', '<=', end_date))
    if staff_name: cctv_q = cctv_q.where(filter=FieldFilter('staff_name', '==', staff_name))
    for doc in cctv_q.stream():
        d = doc.to_dict()
        all_events.append({"ts": d.get('timestamp'), "name": d.get('staff_name'), "event": f"Spotted by CCTV on {d.get('camera_id', 'N/A')}."})

    if not all_events: return f"No activities found for '{staff_name or 'any staff'}'."
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
        except: report.append(f"  - At unknown time: {event['event']}")
    return "\n".join(report)

# --- AI & LANGUAGE PROCESSING ---
def detect_language(text: str):
    global translate_client
    if not translate_client: return {'language': 'en'}
    try:
        result = translate_client.detect_language(text)
        if result.get('language') == 'ml':
            return {'language': 'ml'}
        return {'language': 'en'}
    except Exception as e:
        print(f"ERROR: Language detection failed: {e}")
        return {'language': 'en'}

def translate_text(text: str, target_lang: str):
    global translate_client
    if not translate_client or not text: return text
    try:
        lang_code = target_lang.split('-')[0]
        result = translate_client.translate(text, target_language=lang_code)
        return result['translatedText']
    except Exception as e:
        print(f"ERROR: Translation failed: {e}")
        return "Translation Error"

def generate_audio_response(text: str, lang: str):
    global tts_client
    if not tts_client or not text: return None
    base_lang = lang.split('-')[0]
    voice_map = {'en': ("en-US", "en-US-Wavenet-D"), 'ml': ("ml-IN", "ml-IN-Wavenet-B")}
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

# --- MAIN BOT RESPONSE HANDLER ---
def get_ownerbot_response(message: str, mode: str = 'voice'):
    global db, model, translate_client
    if not db:
        return {"text_response": "Error: Database not loaded.", "audio_response": None}

    try:
        outlets_docs = db.collection('outlets').stream()
        available_outlets = [{"id": doc.id, "name": doc.to_dict().get("name")} for doc in outlets_docs]
    except Exception:
        available_outlets = []

    today_date = datetime.date.today()
    
    system_prompt = f"""
    You are an expert data analyst for Asthana Bakery. Your main goal is to call the correct function to get reports. Today's date is {today_date.strftime('%Y-%m-%d')}.
    Available outlets: {json.dumps(available_outlets)}.
    RULES:
    1. Infer dates: "today" is {today_date.isoformat()}, "yesterday" is {(today_date - datetime.timedelta(days=1)).isoformat()}.
    2. If the user asks about "profit", "loss", or "earnings", you MUST use the `get_profit_report` function.
    3. For sales reports, if an outlet is not specified, ask for one.
    4. After a tool is called, present its output data directly as your final answer.
    """
    
    # Ensure the Gemini model is initialized and re-configured if necessary (though global init should handle it)
    if not model:
        # Fallback if model wasn't initialized, try again.
        # In a production Flask app, you'd handle this more robustly (e.g., using Blueprints with setup functions)
        print("WARN: Gemini model not initialized, attempting re-initialization.")
        initialize_clients() # Try to re-initialize all clients
        if not model: # If still not initialized, return error
            return {"text_response": "Error: Gemini model not available.", "audio_response": None}

    tools = [
        get_sales_report,
        get_profit_report,
        get_production_report,
        get_inventory_report,
        get_staff_activity_report
    ]
    
    original_lang = detect_language(message).get('language', 'en')
    msg_en = translate_text(message, 'en')

    try:
        chat = model.start_chat(enable_automatic_function_calling=True)
        response = chat.send_message(msg_en, tools=tools) # Pass the list of functions
        text_en = response.text
            
    except Exception as e:
        print(f"ERROR: Gemini inference failed: {e}")
        text_en = "I'm sorry, I had trouble understanding that. Please rephrase."

    audio_b64 = None
    if mode == 'voice':
        summary_for_speech = text_en.split('\n')[0]
        final_text = translate_text(text_en, original_lang)
        audio_text = translate_text(summary_for_speech, original_lang)
        audio_b64 = generate_audio_response(audio_text, original_lang)
    else:
        final_text = text_en
    
    return {"text_response": final_text, "audio_response": audio_b64}

# --- NEW: Function to calculate profit ---
def get_profit_report(start_date: str, end_date: str):
    global db
    """Calculates and returns a profit and loss summary for a given date range."""
    if not db: return "Error: Database is not connected."
    try:
        # 1. Calculate Total Revenue
        sales_query = db.collection('sales').where(filter=FieldFilter('date', '>=', start_date)).where(filter=FieldFilter('date', '<=', end_date))
        total_revenue = sum(doc.to_dict().get('total_amount', 0.0) for doc in sales_query.stream())

        # 2. Calculate Cost of Goods Sold (from production)
        # Assuming 'production_logs' contains documents with 'total_cost'
        prod_query = db.collection('production_logs').where(filter=FieldFilter('date', '>=', start_date)).where(filter=FieldFilter('date', '<=', end_date))
        cogs = sum(doc.to_dict().get('total_cost', 0.0) for doc in prod_query.stream())

        # 3. Calculate Operating Expenses
        # Assuming 'expenses' collection contains documents with 'amount'
        expenses_query = db.collection('expenses').where(filter=FieldFilter('date', '>=', start_date)).where(filter=FieldFilter('date', '<=', end_date))
        op_expenses = sum(doc.to_dict().get('amount', 0.0) for doc in expenses_query.stream())

        # 4. Calculate Final Profit
        net_profit = total_revenue - (cogs + op_expenses)

        report = (
            f"Profit & Loss Report for {start_date} to {end_date}:\n"
            f"- Total Revenue:  ₹{total_revenue:,.2f}\n"
            f"- Cost of Goods: -₹{cogs:,.2f}\n"
            f"- Operating Expenses: -₹{op_expenses:,.2f}\n"
            f"----------------------------------\n"
            f"- Net Profit:  ₹{net_profit:,.2f}"
        )
        return report
    except Exception as e:
        return f"An error occurred while generating the profit report: {e}"

def parse_voice_order(spoken_text: str):
    """
    Analyzes spoken text to identify products and how they are being ordered.
    This version has a corrected f-string prompt to fix the format specifier error.
    """
    if not db:
        return {"error": "Database not connected."}
    print(f"DEBUG: Parsing smart voice order: '{spoken_text}'")
    
    try:
        products_ref = db.collection('items')
        docs = products_ref.stream()
        
        available_products_details = []
        for doc in docs:
            product_data = doc.to_dict()
            if product_data.get('name'):
                available_products_details.append({
                    "id": doc.id,
                    "name": product_data.get('name', '').lower(),
                    "malayalam_name": product_data.get('malayalam_name', '').lower(), 
                    "unit_type": product_data.get('unit_type', 'piece')
                })

        if not available_products_details:
            return {"error": "No products found in the database to match against."}

        # --- FIX: Correctly escaped the JSON examples in the prompt ---
        # The JSON examples now use double curly braces {{...}} to correctly
        # represent literal braces inside the f-string.
        prompt = f"""
        You are a highly accurate billing assistant for a bakery in Kerala, India.
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
        7.  If you cannot clearly identify a product or instruction, return an empty list: [].

        Your output MUST be ONLY a valid JSON list of objects.

        Example 1 (piece): "two puffs" -> [{{"item_id": "puff_id", "quantity": 2}}]
        Example 2 (weight - English): "oru kilo mixture" -> [{{"item_id": "mixture_id", "weight_grams": 1000}}]
        Example 3 (price - Malayalam): "20 രൂപക്ക് ലഡു" -> [{{"item_id": "laddu_id", "custom_price": 20}}]
        Example 4 (price - Manglish): "madak for 100 rs" -> [{{"item_id": "madak_id", "custom_price": 100}}]
        Example 5 (weight - Malayalam): "അര കിലോ ജിലേബി" -> [{{"item_id": "jilebi_id", "weight_grams": 500}}]
        Example 6 (quantity - Malayalam): "രണ്ട് പഫ്" -> [{{"item_id": "puff_id", "quantity": 2}}]
        Example 7 (multiple items): "ഒരു കിലോ ബോണ്ടയും രണ്ട് സമൂസയും" -> [{{"item_id": "bonda_id", "weight_grams": 1000}}, {{"item_id": "samosa_id", "quantity": 2}}]
        """
    
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '').strip()
        print(f"DEBUG: Parsed order from AI: {cleaned_response}")
    
        if not cleaned_response:
            return []

        parsed_order = json.loads(cleaned_response)
        if not isinstance(parsed_order, list):
            raise ValueError("AI did not return a list.")
        return parsed_order

    except Exception as e:
        print(f"ERROR: Failed to parse voice order with AI: {e}")
        return {"error": f"Sorry, I could not understand the order: '{spoken_text}'."}


# --- Flask Endpoints ---

@app.route('/voice-to-text/', methods=['POST'])
def handle_voice_to_text():
    global whisper_model
    if not whisper_model:
        return jsonify({"error": "Speech-to-Text service not initialized on backend."}), 500

    if 'Content-Type' not in request.headers or 'audio/wav' not in request.headers['Content-Type']:
        return jsonify({"error": "Unsupported Media Type. Please send audio/wav."}), 415

    try:
        audio_data = request.data # Get raw audio bytes

        # Create a temporary file to save the audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
            temp_audio_file.write(audio_data)
            temp_audio_path = temp_audio_file.name
        
        print(f"DEBUG: Audio saved to temporary path: {temp_audio_path}")

        # Transcribe the audio using Whisper
        # Use language="ml" for Malayalam to guide Whisper
        result = whisper_model.transcribe(temp_audio_path, language="ml")
        recognized_text = result["text"]

        # Clean up the temporary file
        os.unlink(temp_audio_path)
        
        print(f"DEBUG: Backend Recognized Text: '{recognized_text}'")

        # Now, pass the recognized text to your existing parse_voice_order function
        parsed_order_data = parse_voice_order(recognized_text)

        # Check if parse_voice_order returned an error dictionary
        if isinstance(parsed_order_data, dict) and 'error' in parsed_order_data:
            return jsonify(parsed_order_data), 400 # Return 400 if parsing had an error

        return jsonify({
            "recognized_text": recognized_text,
            "parsed_order": parsed_order_data
        }), 200

    except Exception as e:
        print(f"ERROR: Error processing voice-to-text on backend: {e}")
        # Clean up temp file in case of error
        if 'temp_audio_path' in locals() and os.path.exists(temp_audio_path):
            os.unlink(temp_audio_path)
        return jsonify({"error": f"Internal server error during voice processing: {str(e)}"}), 500

# Endpoint to fetch products (existing)
@app.route('/items/manage-products/', methods=['GET'])
def get_products():
    global db
    if not db:
        return jsonify({"error": "Database not connected"}), 500
    try:
        products_ref = db.collection('items')
        docs = products_ref.stream()
        products_list = []
        for doc in docs:
            product_data = doc.to_dict()
            product_data['id'] = doc.id # Add document ID
            products_list.append(product_data)
        return jsonify(products_list), 200
    except Exception as e:
        print(f"Error fetching products: {e}")
        return jsonify({"error": f"Failed to fetch products: {str(e)}"}), 500

# Endpoint to fetch outlets (existing)
@app.route('/outlets/manage/', methods=['GET'])
def get_outlets():
    global db
    if not db:
        return jsonify({"error": "Database not connected"}), 500
    try:
        outlets_ref = db.collection('outlets')
        docs = outlets_ref.stream()
        outlets_list = []
        for doc in docs:
            outlet_data = doc.to_dict()
            outlet_data['id'] = doc.id # Add document ID
            outlets_list.append(outlet_data)
        return jsonify(outlets_list), 200
    except Exception as e:
        print(f"Error fetching outlets: {e}")
        return jsonify({"error": f"Failed to fetch outlets: {str(e)}"}), 500

# Endpoint to process sales (existing)
@app.route('/sales/process/', methods=['POST'])
def process_sale_endpoint():
    global db
    if not db:
        return jsonify({"error": "Database not connected"}), 500
    try:
        sale_data = request.get_json()
        if not sale_data:
            return jsonify({"error": "No sale data provided"}), 400

        # Validate sale_data structure, especially items list
        if not isinstance(sale_data.get('items'), list) or not sale_data.get('outlet_id') or not sale_data.get('total_amount') is not None:
            return jsonify({"error": "Invalid sale data format"}), 400

        # Generate a unique numeric bill ID
        # You might have a more robust bill ID generation in a real system
        timestamp_ms = int(datetime.datetime.now().timestamp() * 1000)
        numeric_bill_id = str(timestamp_ms)[-8:] # Last 8 digits of timestamp for a simple ID

        # Add timestamp and bill ID
        sale_data['timestamp'] = datetime.datetime.now().isoformat()
        sale_data['date'] = datetime.date.today().isoformat()
        sale_data['numeric_bill_id'] = numeric_bill_id

        # Update stock for piece items
        batch = db.batch()
        for item in sale_data['items']:
            product_id = item.get('product_id')
            quantity = item.get('quantity', 0)
            unit_type = item.get('unit_type')

            if product_id and unit_type == 'piece' and quantity > 0:
                product_ref = db.collection('items').document(product_id)
                batch.update(product_ref, {'stock': firestore.Increment(-quantity)})
        
        # Commit stock updates
        batch.commit()

        # Save sale record
        doc_ref = db.collection('sales').add(sale_data)
        
        return jsonify({"message": "Sale processed successfully", "bill_id": doc_ref[1].id, "numeric_bill_id": numeric_bill_id}), 201

    except Exception as e:
        print(f"Error processing sale: {e}")
        return jsonify({"error": f"Failed to process sale: {str(e)}"}), 500

# Endpoint to find sales (existing)
@app.route('/sales/find/<string:numeric_bill_id>/', methods=['GET'])
def find_sale_by_numeric_id(numeric_bill_id):
    global db
    if not db:
        return jsonify({"error": "Database not connected"}), 500
    try:
        # Query for the sale using numeric_bill_id
        query = db.collection('sales').where(filter=FieldFilter('numeric_bill_id', '==', numeric_bill_id)).limit(1)
        docs = list(query.stream())

        if docs:
            sale_data = docs[0].to_dict()
            return jsonify(sale_data), 200
        else:
            return jsonify({"error": "Bill not found"}), 404
    except Exception as e:
        print(f"Error finding bill: {e}")
        return jsonify({"error": f"Failed to find bill: {str(e)}"}), 500


if __name__ == '__main__':
    # Flask development server settings.
    # For production, use a WSGI server like Gunicorn.
    app.run(host='0.0.0.0', port=8000, debug=True)