# items/pos_views.py (Migrated to Supabase)

from rest_framework.decorators import api_view
from rest_framework.response import Response
from bakery_ai_manager.supabase_client import get_supabase_client

db = get_supabase_client()

@api_view(['GET'])
def pos_products(request):
    """
    POS-safe product loader
    - paginated
    - outlet aware
    - fast
    """
    outlet_id = request.GET.get('outlet_id')
    limit = int(request.GET.get('limit', 50))
    cursor = request.GET.get('cursor')  # product id for pagination

    if not outlet_id:
        return Response({"error": "outlet_id required"}, status=400)

    try:
        query = db.table('items').select('*') \
            .eq('is_active', True) \
            .contains('outlet_ids', [outlet_id]) \
            .order('name') \
            .limit(limit)

        # For cursor-based pagination, filter items after the cursor
        if cursor:
            # Get the cursor item's name for ordering
            cursor_result = db.table('items').select('name').eq('id', cursor).execute()
            if cursor_result.data:
                cursor_name = cursor_result.data[0]['name']
                query = query.gt('name', cursor_name)

        result = query.execute()

        products = result.data
        last_id = products[-1]['id'] if products else None

        return Response({
            "results": products,
            "next_cursor": last_id
        })
    except Exception as e:
        return Response({"error": f"Failed to fetch POS products: {e}"}, status=500)
