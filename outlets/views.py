# =======================================================
# File: outlets/views.py (Migrated to Supabase)
# =======================================================
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from bakery_ai_manager.supabase_client import get_supabase_client

db = get_supabase_client()

@api_view(['GET', 'POST'])
def manage_outlets(request):
    """
    Handles listing all outlets (GET) and creating a new outlet (POST).
    """
    if request.method == 'GET':
        try:
            result = db.table('outlets').select('*').order('name').limit(10).execute()
            outlets_list = []
            for row in result.data:
                outlets_list.append({
                    "id": row.get("id", ""),
                    "name": row.get("name", ""),
                    "phone": row.get("phone", ""),
                    "type": row.get("type", "sales"),
                })
            return Response(outlets_list, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Failed to fetch outlets: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    elif request.method == 'POST':
        try:
            name = request.data.get("name")
            phone = request.data.get("phone")
            outlet_type = request.data.get("type", "sales")

            if not name or not phone:
                return Response(
                    {"error": "Name and phone are required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            outlet_id = name.lower().replace(" ", "_").replace("-", "_")

            new_outlet_data = {
                "id": outlet_id,
                "name": name,
                "phone": phone,
                "type": outlet_type,
            }

            db.table('outlets').upsert(new_outlet_data).execute()

            return Response(
                {"message": "Outlet added", "id": outlet_id},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to add outlet: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['PUT', 'DELETE'])
def manage_single_outlet(request, outlet_id):
    """
    Handles updating (PUT) and deleting (DELETE) a single outlet by its ID.
    """
    if request.method == 'PUT':
        try:
            update_data = dict(request.data)
            db.table('outlets').update(update_data).eq('id', outlet_id).execute()
            return Response({"message": f"Outlet '{outlet_id}' updated successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to update outlet: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == 'DELETE':
        try:
            db.table('outlets').delete().eq('id', outlet_id).execute()
            return Response(status=204)
        except Exception as e:
            return Response({"error": f"Failed to delete outlet: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
