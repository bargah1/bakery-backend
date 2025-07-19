from rest_framework.decorators import api_view
from rest_framework.response import Response
from .gpt_handler import get_ownerbot_response, parse_voice_order # <-- Import the new function

@api_view(["POST"])
def ask(request):
    user_msg = request.data.get("question")
    if not user_msg:
        return Response({"error": "No message received."})
    ai_reply = get_ownerbot_response(user_msg)
    return Response(ai_reply)

@api_view(["POST"])
def parse_order_from_voice(request):
    """
    This new view handles requests from the billing app's voice feature.
    """
    spoken_text = request.data.get("text")
    if not spoken_text:
        return Response({"error": "No text received."}, status=400)
    
    parsed_items = parse_voice_order(spoken_text)
    
    if "error" in parsed_items:
         return Response(parsed_items, status=400)

    return Response(parsed_items)
