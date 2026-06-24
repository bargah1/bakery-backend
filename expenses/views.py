# =======================================================
# File: expenses/views.py (Migrated to Supabase)
# =======================================================
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from bakery_ai_manager.supabase_client import get_supabase_client

db = get_supabase_client()

@api_view(['GET', 'POST'])
def manage_expenses(request):
    """
    Handles listing all expenses (GET) and creating a new one (POST).
    """
    if request.method == 'GET':
        try:
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            query = db.table('expenses').select('*')
            if start_date:
                query = query.gte('date', start_date)
            if end_date:
                query = query.lte('date', end_date)
            
            result = query.order('date', desc=True).execute()
            return Response(result.data)
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

            result = db.table('expenses').insert(expense_data).execute()
            return Response({'message': 'Expense recorded successfully.'}, status=201)
        except Exception as e:
            return Response({'error': f'Failed to record expense: {e}'}, status=500)

@api_view(['PUT', 'DELETE'])
def manage_single_expense(request, expense_id):
    """
    Handles updating or deleting a single expense.
    """
    if request.method == 'PUT':
        try:
            update_data = dict(request.data)
            db.table('expenses').update(update_data).eq('id', expense_id).execute()
            return Response({'message': 'Expense updated successfully.'})
        except Exception as e:
            return Response({'error': f'Failed to update expense: {e}'}, status=500)
    
    elif request.method == 'DELETE':
        try:
            db.table('expenses').delete().eq('id', expense_id).execute()
            return Response(status=204)
        except Exception as e:
            return Response({'error': f'Failed to delete expense: {e}'}, status=500)
