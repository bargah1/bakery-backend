# production/views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from bakery_ai_manager.firestore_client import get_firestore_client
from ownerbot.gpt_handler import get_production_report 

db = get_firestore_client()

@api_view(["POST"])
def record_production(request):
    """
    API endpoint to record a production batch.
    """
    required_fields = ["production_unit_id", "product_id", "quantity_produced"]
    for field in required_fields:
        if field not in request.data:
            return Response(
                {"error": f"Missing required field: {field}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    production_data = {
        "production_unit_id": request.data.get("production_unit_id", "vellachal_production"), # Default production unit for Asthana
        "product_id": request.data.get("product_id"),
        "quantity_produced": request.data.get("quantity_produced"),
        "raw_materials_used": request.data.get("raw_materials_used", {}),
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().date().isoformat(), 
    }

    try:
        production_ref = db.collection('production')
        update_time, doc_ref = production_ref.add(production_data)

        return Response(
            {"message": "Production recorded successfully", "production_id": doc_ref.id},
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        print(f"ERROR: Failed to record production: {e}")
        return Response(
            {"error": "Failed to record production", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
def get_production_summary_report(request):
    """
    API endpoint to retrieve aggregated production report as plain text for chatbot.
    """
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')

    try:
        report_text = get_production_report(start_date=start_date, end_date=end_date) 
        return Response({"report": report_text}, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"ERROR: Failed to get production summary: {e}")
        return Response({"error": "Failed to retrieve production report", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def get_structured_production_report(request):
    """
    API endpoint to retrieve structured production data for charting.
    """
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')

    production_ref = db.collection('production')
    query = production_ref

    if start_date_str:
        query = query.where('date', '>=', start_date_str)
    if end_date_str:
        query = query.where('date', '<=', end_date_str)
    
    # Order by date and timestamp for chronological charting
    query = query.order_by('date').order_by('timestamp')

    structured_data = []
    try:
        docs = query.stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id 
            structured_data.append(data)
        
        if not structured_data:
            return Response({"message": "No production data found for selected criteria."}, status=status.HTTP_200_OK)
        
        return Response(structured_data, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"ERROR: Failed to retrieve structured production data: {e}")
        return Response(
            {"error": "Failed to retrieve structured production data", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

