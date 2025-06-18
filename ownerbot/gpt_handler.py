import os
import datetime
import json
import base64
import torch # You can remove this if not used elsewhere
from google.cloud import firestore, translate_v2 as translate, texttospeech
import google.generativeai as genai

# --- CONFIGURATION ---
# Load API keys and project ID from environment variables for security
# Ensure you have a .env file or have set these in your environment
# GOOGLE_API_KEY should be your Generative AI (Gemini) API key.
# GOOGLE_CLOUD_PROJECT should be your Google Cloud Project ID.
from dotenv import load_dotenv
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")

# --- INITIALIZE CLIENTS ---
try:
    # Firestore Client
    db = firestore.Client(project=PROJECT_ID)
    print("DEBUG: Firestore client initialized successfully.")

    # Google Cloud Services Clients
    translate_client = translate.Client()
    tts_client = texttospeech.TextToSpeechClient()
    print("DEBUG: Google Cloud Translate and TTS clients initialized.")

    # Gemini (Generative AI) Client
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    print("DEBUG: Google Generative AI (Gemini) client initialized.")

except Exception as e:
    print(f"FATAL ERROR: Could not initialize one or more services: {e}")
    db = None
    model = None
    translate_client = None
    tts_client = None

# --- DATA FETCHING TOOLS (Firestore Functions) ---
# These functions are the "tools" that our Gemini model can use.

def get_sales_report(start_date: str = None, end_date: str = None, outlet_id: str = None):
    """
    Retrieves sales data from Firestore based on a date range and an optional outlet_id,
    then generates a human-readable summary report.
    Args:
        start_date (str): The start date in 'YYYY-MM-DD' format.
        end_date (str): The end date in 'YYYY-MM-DD' format.
        outlet_id (str): The specific outlet to filter by (e.g., 'vailathur_cafe').
    """
    if not db: return "Error: Firestore is not connected."
    print(f"DEBUG: Executing get_sales_report with params: start_date={start_date}, end_date={end_date}, outlet_id={outlet_id}")
    
    sales_ref = db.collection('sales')
    query = sales_ref

    today = datetime.date.today().isoformat()
    if start_date:
        query = query.where('date', '>=', start_date)
    if end_date:
        query = query.where('date', '<=', end_date)
    # If no dates are provided, default to today's sales.
    if not start_date and not end_date:
        query = query.where('date', '==', today)
    
    if outlet_id:
        query = query.where('outlet_id', '==', outlet_id)

    query_results = query.stream()

    total_sales = 0.0
    items_sold = {}
    found_data = False

    for doc in query_results:
        found_data = True
        data = doc.to_dict()
        total_sales += data.get('total_amount', 0.0)
        for item in data.get('items', []):
            item_id = item.get('item_id', 'Unknown Item')
            quantity = item.get('quantity', 0)
            items_sold[item_id] = items_sold.get(item_id, 0) + quantity
    
    if not found_data:
        return "I couldn't find any sales data for the selected criteria. Please check if sales have been recorded."
    
    report = f"Sales Report for outlet '{outlet_id or 'all outlets'}'"
    if start_date and end_date:
        report += f" from {start_date} to {end_date}:\n"
    elif start_date:
         report += f" for {start_date}:\n"
    else:
        report += f" for today:\n"
        
    report += f"Total Sales: ₹{total_sales:,.2f}\nItems Sold:\n"
    if not items_sold:
        report += "  - No items recorded."
    else:
        for item, count in sorted(items_sold.items()):
            report += f"  - {item.replace('_', ' ').title()}: {count}\n"
    
    return report

def get_production_report(start_date: str = None, end_date: str = None):
    """
    Retrieves production data from Firestore for a given date range.
    Args:
        start_date (str): The start date in 'YYYY-MM-DD' format.
        end_date (str): The end date in 'YYYY-MM-DD' format.
    """
    if not db: return "Error: Firestore is not connected."
    print(f"DEBUG: Executing get_production_report with params: start_date={start_date}, end_date={end_date}")

    # Similar logic as sales report...
    # (The existing production report function is good, just adding the debug print)
    production_ref = db.collection('production')
    query = production_ref

    today = datetime.date.today().isoformat()
    if start_date:
        query = query.where('date', '>=', start_date)
    if end_date:
        query = query.where('date', '<=', end_date)
    if not start_date and not end_date:
        query = query.where('date', '==', today)

    query_results = query.stream()
    total_produced_items = {}
    found_data = False

    for doc in query_results:
        found_data = True
        data = doc.to_dict()
        product_id = data.get('product_id', 'Unknown Item')
        quantity = data.get('quantity_produced', 0)
        total_produced_items[product_id] = total_produced_items.get(product_id, 0) + quantity

    if not found_data:
        return "No production data found for the criteria."

    report = "Production Report:\n"
    for product, quantity in sorted(total_produced_items.items()):
        report += f"  - {product.replace('_', ' ').title()}: {quantity} units produced\n"
    return report

def get_inventory_report():
    """Retrieves a summary of all current inventory levels from Firestore."""
    if not db: return "Error: Firestore is not connected."
    print("DEBUG: Executing get_inventory_report")
    
    items_ref = db.collection('items').order_by('name').stream()
    report_lines = ["Current Inventory Report:\n"]
    found_items = False
    for doc in items_ref:
        found_items = True
        data = doc.to_dict()
        name = data.get('name', 'Unknown')
        stock = data.get('stock', 0)
        report_lines.append(f"- {name}: {stock} units in stock.")
        
    if not found_items:
        return "No inventory items found."
        
    return "\n".join(report_lines)

def get_staff_attendance_report(start_date: str = None, end_date: str = None):
    """
    Retrieves staff attendance records from Firestore, calculates total hours worked,
    and estimates salary for the given period.
    """
    if not db: return "Error: Firestore is not connected."
    print(f"DEBUG: Executing get_staff_attendance_report with params: start_date={start_date}, end_date={end_date}")

    # Default to today if no date range is given
    if not start_date: start_date = datetime.date.today().isoformat()
    if not end_date: end_date = start_date

    attendance_ref = db.collection('attendance')
    staff_ref = db.collection('staff')

    query = attendance_ref.where('date', '>=', start_date).where('date', '<=', end_date).order_by('staff_id').order_by('timestamp')
    docs = query.stream()

    # Get all staff salaries first to avoid multiple DB reads
    staff_salaries = {}
    for staff_doc in staff_ref.stream():
        staff_data = staff_doc.to_dict()
        staff_salaries[staff_doc.id] = staff_data.get('salary', 0.0) # Assuming salary is per hour

    # Process attendance records
    work_sessions = {}
    for doc in docs:
        record = doc.to_dict()
        staff_id = record.get('staff_id')
        punch_type = record.get('type')
        timestamp = datetime.datetime.fromisoformat(record.get('timestamp'))
        staff_name = record.get('staff_name', staff_id)

        if staff_id not in work_sessions:
            work_sessions[staff_id] = {'name': staff_name, 'punches': [], 'total_hours': 0, 'salary_due': 0}
        work_sessions[staff_id]['punches'].append((punch_type, timestamp))

    if not work_sessions:
        return f"No staff attendance records found from {start_date} to {end_date}."

    # Calculate hours and salary for each staff member
    report_lines = [f"Staff Attendance & Salary Report ({start_date} to {end_date}):\n"]
    for staff_id, data in work_sessions.items():
        punches = sorted(data['punches'], key=lambda x: x[1])
        total_duration = datetime.timedelta()
        clock_in_time = None

        for punch_type, timestamp in punches:
            if punch_type == 'clock_in':
                clock_in_time = timestamp
            elif punch_type == 'clock_out' and clock_in_time:
                total_duration += timestamp - clock_in_time
                clock_in_time = None # Reset for next session

        total_hours = total_duration.total_seconds() / 3600
        data['total_hours'] = total_hours
        hourly_rate = staff_salaries.get(staff_id, 0.0)
        data['salary_due'] = total_hours * hourly_rate
        
        report_lines.append(
            f"\n- Staff: {data['name']}\n"
            f"  Total Hours Worked: {total_hours:.2f} hours\n"
            f"  Estimated Salary Due: ₹{data['salary_due']:,.2f} (at ₹{hourly_rate}/hr)"
        )

    return "\n".join(report_lines)

# --- AI & LANGUAGE PROCESSING ---

def detect_language(text: str) -> dict:
    """Detects the language of the input text."""
    if not translate_client: return {'language': 'en', 'confidence': 1.0}
    try:
        result = translate_client.detect_language(text)
        return result
    except Exception as e:
        print(f"WARN: Language detection failed: {e}. Defaulting to English.")
        return {'language': 'en', 'confidence': 1.0}

def translate_text(text: str, target_language: str):
    """Translates text to the target language."""
    if not translate_client: return text
    try:
        result = translate_client.translate(text, target_language=target_language)
        return result['translatedText']
    except Exception as e:
        print(f"ERROR: Translation failed: {e}")
        return "Sorry, I am having trouble with translation right now."
        
def generate_audio_response(text: str, language_code: str = 'en-US') -> str:
    """Generates audio from text and returns it as a base64 encoded string."""
    if not tts_client: return None
    
    # Map simple language codes to specific TTS voice codes
    voice_map = {
        'en': texttospeech.VoiceSelectionParams(language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.FEMALE),
        'ml': texttospeech.VoiceSelectionParams(language_code="ml-IN", name="ml-IN-Wavenet-B") # A high-quality Malayalam voice
    }
    
    synthesis_input = texttospeech.SynthesisInput(text=text)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    
    try:
        response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice_map.get(language_code.split('-')[0], voice_map['en']), audio_config=audio_config
        )
        # Encode audio content to base64 for JSON transport
        return base64.b64encode(response.audio_content).decode('utf-8')
    except Exception as e:
        print(f"ERROR: Text-to-Speech synthesis failed: {e}")
        return None

# --- MAIN BOT RESPONSE HANDLER ---

def get_ownerbot_response(message: str) -> dict:
    """
    The main function to process a user's message.
    It handles language detection, translation, AI function calling, and generates a text and audio response.
    """
    if not model:
        return {
            "text_response": "Error: The core AI model is not loaded. Please check the server logs.",
            "audio_response": None,
            "language_code": "en"
        }

    # 1. Detect Language
    lang_detection = detect_language(message)
    source_lang = lang_detection.get('language', 'en')
    print(f"DEBUG: Detected language: {source_lang}")

    # 2. Translate to English if necessary
    # The AI model and tools work best with English prompts.
    if source_lang != 'en':
        message_en = translate_text(message, 'en')
        print(f"DEBUG: Translated query from '{source_lang}' to 'en': {message_en}")
    else:
        message_en = message

    # 3. Use Gemini with Function Calling to get a factual text response
    try:
        # Define the tools the model can use
        tools = [
            get_sales_report,
            get_production_report,
            get_inventory_report,
            get_staff_attendance_report
        ]
        
        # Start a chat session with the model, telling it about the tools
        chat_session = model.start_chat(
            enable_automatic_function_calling=True
        )
        
        # Send the message to the model
        # The model will either respond directly or call one of the Python functions
        response = chat_session.send_message(message_en)
        text_response_en = response.text

    except Exception as e:
        print(f"ERROR: Gemini model inference failed: {e}")
        text_response_en = "I'm sorry, I encountered an error trying to process that."

    # 4. Translate the response back to the source language if necessary
    if source_lang != 'en':
        final_text_response = translate_text(text_response_en, source_lang)
    else:
        final_text_response = text_response_en

    # 5. Generate Audio for the final response
    tts_lang_code = 'ml-IN' if source_lang == 'ml' else 'en-US'
    audio_b64 = generate_audio_response(final_text_response, source_lang)
    
    # 6. Return the complete package to the Flutter App
    return {
        "text_response": final_text_response,
        "audio_response": audio_b64,
        "language_code": source_lang
    }

# Example of how you would call this from your FastAPI endpoint
if __name__ == '__main__':
    # Test cases
    print("\n--- English Test ---")
    english_query = "how were sales at the vailathur cafe yesterday?"
    response = get_ownerbot_response(english_query)
    print(f"Query: {english_query}")
    print(f"Text Response: {response['text_response']}")
    print(f"Audio Generated: {'Yes' if response['audio_response'] else 'No'}")

    print("\n--- Malayalam Test ---")
    malayalam_query = "ഇന്നലത്തെ പ്രൊഡക്ഷൻ റിപ്പോർട്ട് തരൂ" # Trans: "Give yesterday's production report"
    response = get_ownerbot_response(malayalam_query)
    print(f"Query: {malayalam_query}")
    print(f"Text Response: {response['text_response']}")
    print(f"Audio Generated: {'Yes' if response['audio_response'] else 'No'}")
    
    print("\n--- Staff Attendance Test ---")
    attendance_query = "Give me the staff attendance report for today"
    response = get_ownerbot_response(attendance_query)
    print(f"Query: {attendance_query}")
    print(f"Text Response: {response['text_response']}")
    print(f"Audio Generated: {'Yes' if response['audio_response'] else 'No'}")