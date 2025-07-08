# =======================================================
# File: outlets/views.py (Upgraded)
# =======================================================
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from bakery_ai_manager.firestore_client import get_firestore_client

db = get_firestore_client()
outlets_collection_ref = db.collection('outlets')

@api_view(['GET', 'POST'])
def manage_outlets(request):
    """
    Handles listing all outlets (GET) and creating a new outlet (POST).
    """
    if request.method == 'GET':
        try:
            docs = outlets_collection_ref.order_by('name').stream()
            outlets_list = [{'id': doc.id, **doc.to_dict()} for doc in docs]
            return Response(outlets_list, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to fetch outlets: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == 'POST':
        try:
            name = request.data.get("name")
            phone = request.data.get("phone")
            # --- FIX: Get the new 'type' field from the request ---
            outlet_type = request.data.get("type", "sales") # Default to 'sales'

            if not name or not phone:
                return Response({"error": "Name and phone are required."}, status=status.HTTP_400_BAD_REQUEST)
            
            outlet_id = name.lower().replace(" ", "_").replace("-", "_")
            
            # --- FIX: Add the 'type' to the data saved in Firestore ---
            new_outlet_data = {
                "name": name, 
                "phone": phone,
                "type": outlet_type 
            }
            outlets_collection_ref.document(outlet_id).set(new_outlet_data)
            
            return Response({"message": "Outlet added", "id": outlet_id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": f"Failed to add outlet: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT', 'DELETE'])
def manage_single_outlet(request, outlet_id):
    """
    Handles updating (PUT) and deleting (DELETE) a single outlet by its ID.
    The .update() method will correctly handle the new 'type' field if sent from the frontend.
    """
    outlet_ref = outlets_collection_ref.document(outlet_id)

    if request.method == 'PUT':
        try:
            outlet_ref.update(request.data)
            return Response({"message": f"Outlet '{outlet_id}' updated successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to update outlet: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == 'DELETE':
        try:
            outlet_ref.delete()
            return Response(status=204)
        except Exception as e:
            return Response({"error": f"Failed to delete outlet: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
