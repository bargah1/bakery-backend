from rest_framework.decorators import api_view
from rest_framework.response import Response
from .gpt_handler import get_ownerbot_response # Assuming gpt_handler is where get_ownerbot_response lives

@api_view(["POST"])
def ask(request):
    # Print the raw request data for full visibility
    print(f"DEBUG: Received request.data: {request.data}")

    # Ensure this matches your frontend's key for the message
    user_msg = request.data.get("question") 
    
    print(f"DEBUG: Extracted user_msg: '{user_msg}' (Type: {type(user_msg)})")

    if not user_msg:
        print("DEBUG: user_msg is empty or None. Returning 'No message received'.")
        return Response({"response": "No message received"})
    
    print(f"DEBUG: user_msg is not empty. Calling get_ownerbot_response with: '{user_msg}'")
    ai_reply = get_ownerbot_response(user_msg)
    
    print(f"DEBUG: AI Reply from get_ownerbot_response: {ai_reply}")

    return Response({"response": ai_reply})