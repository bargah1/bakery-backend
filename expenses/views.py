# =======================================================
# File: expenses/views.py (NEW FILE)
# =======================================================
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from bakery_ai_manager.firestore_client import get_firestore_client
from google.cloud.firestore_v1.base_query import FieldFilter

db = get_firestore_client()
expenses_ref = db.collection('expenses')

@api_view(['GET', 'POST'])
def manage_expenses(request):
    """
    Handles listing all expenses (GET) and creating a new one (POST).
    """
    if request.method == 'GET':
        try:
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            query = expenses_ref
            if start_date:
                query = query.where(filter=FieldFilter('date', '>=', start_date))
            if end_date:
                query = query.where(filter=FieldFilter('date', '<=', end_date))
            
            docs = query.order_by('date', direction='DESCENDING').stream()
            expenses = [{'id': doc.id, **doc.to_dict()} for doc in docs]
            return Response(expenses)
        except Exception as e:
            return Response({"error": f"Failed to fetch expenses: {e}"}, status=500)

    elif request.method == 'POST':
        data = request.data
        try:
            expense_data = {
                "description": data.get('description'),
                "amount": float(data.get('amount')),
                "category": data.get('category'),
                "date": data.get('date', datetime.now().date().isoformat()),
                "outlet_id": data.get('outlet_id', 'general'),
                "created_at": datetime.now().isoformat()
            }
            if not expense_data['description'] or not expense_data['amount'] or not expense_data['category']:
                 return Response({'error': 'Description, amount, and category are required.'}, status=400)

            expenses_ref.add(expense_data)
            return Response({'message': 'Expense recorded successfully.'}, status=201)
        except Exception as e:
            return Response({'error': f'Failed to record expense: {e}'}, status=500)

@api_view(['PUT', 'DELETE'])
def manage_single_expense(request, expense_id):
    """
    Handles updating or deleting a single expense.
    """
    expense_doc_ref = expenses_ref.document(expense_id)
    if request.method == 'PUT':
        try:
            expense_doc_ref.update(request.data)
            return Response({'message': 'Expense updated successfully.'})
        except Exception as e:
            return Response({'error': f'Failed to update expense: {e}'}, status=500)
    
    elif request.method == 'DELETE':
        try:
            expense_doc_ref.delete()
            return Response(status=204)
        except Exception as e:
            return Response({'error': f'Failed to delete expense: {e}'}, status=500)
