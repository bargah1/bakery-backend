# items/pos_views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from bakery_ai_manager.firestore_client import get_firestore_client

db = get_firestore_client()

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
    cursor = request.GET.get('cursor')  # document id

    if not outlet_id:
        return Response({"error": "outlet_id required"}, status=400)

    query = (
        db.collection('items')
        .where('is_active', '==', True)
        .where('outlet_ids', 'array_contains', outlet_id)
        .order_by('name')
        .limit(limit)
    )

    if cursor:
        last_doc = db.collection('items').document(cursor).get()
        if last_doc.exists:
            query = query.start_after(last_doc)

    docs = query.stream()

    products = []
    last_id = None

    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        products.append(data)
        last_id = doc.id

    return Response({
        "results": products,
        "next_cursor": last_id
    })
