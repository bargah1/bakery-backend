# In staff_management/views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
from bakery_ai_manager.firestore_client import get_firestore_client
from google.cloud.firestore_v1.base_query import FieldFilter
# All other imports (storage, face_recognition, etc.) are assumed to be here

# --- FIX: Comment out imports for face recognition ---
# import face_recognition
# import numpy as np
# import cv2
# import requests
# from google.cloud import storage


db = get_firestore_client()
# --- FIX: Comment out GCS bucket initialization ---
# GCS_BUCKET_NAME = 'manger-ai-staff-images'
# try:
#     storage_client = storage.Client()
#     gcs_bucket = storage_client.bucket(GCS_BUCKET_NAME)
#     print(f"DEBUG: GCS client initialized for bucket: {GCS_BUCKET_NAME}")
# except Exception as e:
#     print(f"ERROR: Failed to initialize GCS client: {e}")
#     gcs_bucket = None

# --- Cache for known staff encodings ---
_known_staff_encodings = {}
_staff_names_by_id = {}

# --- FIX: Comment out face encoding helper function ---
# def _generate_face_encodings(image_urls):
#     encodings_for_all_images = []
#     for url in image_urls:
#         try:
#             response = requests.get(url)
#             response.raise_for_status()
            
#             image_array = np.frombuffer(response.content, np.uint8)
#             img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

#             if img is None:
#                 print(f"WARNING: Could not decode image from URL: {url}")
#                 continue

#             face_encodings_in_image = face_recognition.face_encodings(img)
#             if face_encodings_in_image:
#                 for encoding in face_encodings_in_image:
#                     encodings_for_all_images.append(encoding.tolist())
#             else:
#                 print(f"WARNING: No face found in image from URL: {url}")
#         except Exception as e:
#             print(f"ERROR: Failed to process image {url} for encoding: {e}")
#     return encodings_for_all_images

# --- FIX: Comment out function to load encodings ---
# def _load_known_staff_encodings():
#     global _known_staff_encodings, _staff_names_by_id
#     _known_staff_encodings = {}
#     _staff_names_by_id = {}
#     print("DEBUG: Loading known staff encodings from Firestore...")
#     try:
#         staff_docs = db.collection('staff').stream()
#         for doc in staff_docs:
#             staff_data = doc.to_dict()
#             staff_id = doc.id
#             staff_name = staff_data.get('name', 'Unknown Staff')
            
#             face_encodings_flat = staff_data.get('face_encodings', [])
            
#             if face_encodings_flat and isinstance(face_encodings_flat, list) and len(face_encodings_flat) > 0:
#                 if len(face_encodings_flat) % 128 == 0:
#                     num_encodings = len(face_encodings_flat) // 128
#                     reshaped_encodings = np.array(face_encodings_flat).reshape(num_encodings, 128)
#                     _known_staff_encodings[staff_id] = [np.array(e) for e in reshaped_encodings]
#                     _staff_names_by_id[staff_id] = staff_name
#                 else:
#                     print(f"WARNING: Face encodings for {staff_id} have invalid length. Skipping.")
#         print(f"DEBUG: Loaded {len(_known_staff_encodings)} staff members for recognition.")
#     except Exception as e:
#         print(f"ERROR: Failed to load known staff encodings for recognition cache: {e}")

# # Load encodings once at Django server startup
# _load_known_staff_encodings()

@api_view(["POST"])
def add_staff(request):
    """
    API endpoint to add a new staff member.
    Face encoding part is disabled for the lite version.
    """
    required_fields = ["name", "role", "contact_number", "salary"] 
    for field in required_fields:
        if field not in request.data:
            return Response(
                {"error": f"Missing required field: {field}"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    staff_name = request.data.get("name").strip()
    staff_id = staff_name.lower().replace(" ", "_") + "_" + str(datetime.now().timestamp()).replace('.', '') 
    
    existing_doc = db.collection('staff').document(staff_id).get()
    if existing_doc.exists:
        return Response({"error": f"Staff member '{staff_name}' (ID: {staff_id}) already exists."}, status=status.HTTP_409_CONFLICT)

    # --- FIX: Face encoding generation is skipped ---
    image_urls = request.data.get("image_urls", [])
    
    staff_data = {
        "name": staff_name,
        "role": request.data.get("role"),
        "contact_number": request.data.get("contact_number"),
        "address": request.data.get("address", ""),
        "emergency_contact": request.data.get("emergency_contact", ""),
        "image_urls": image_urls, 
        "face_encodings": [], # Store an empty list
        "location_id": request.data.get("location_id", ""), 
        "salary": float(request.data.get("salary")), 
        "created_at": datetime.now().isoformat()
    }

    try:
        db.collection('staff').document(staff_id).set(staff_data)
        # _load_known_staff_encodings() # No need to reload cache
        print(f"DEBUG: Added new staff member '{staff_name}' with ID: {staff_id} to location {staff_data['location_id']}")
        return Response(
            {"message": "Staff member added successfully", "staff_id": staff_id},
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        print(f"ERROR: Failed to add staff member: {e}")
        return Response(
            {"error": "Failed to add staff member", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# --- FIX: Comment out image upload as it's related to face auth ---
# @api_view(["POST"])
# def upload_staff_image(request):
#     if gcs_bucket is None:
#         return Response({"error": "Google Cloud Storage is not initialized."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#     if 'file' not in request.FILES:
#         return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
#     uploaded_file = request.FILES['file']
#     destination_blob_name = f"staff_images/{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{uploaded_file.name.replace(' ', '_')}"
#     try:
#         blob = gcs_bucket.blob(destination_blob_name)
#         blob.upload_from_file(uploaded_file.file, content_type=uploaded_file.content_type)
#         blob.make_public()
#         public_url = blob.public_url
#         print(f"DEBUG: Image uploaded to GCS: {public_url}")
#         return Response(
#             {"message": "Image uploaded successfully", "image_url": public_url},
#             status=status.HTTP_201_CREATED
#         )
#     except Exception as e:
#         print(f"ERROR: Failed to upload image to GCS: {e}")
#         return Response(
#             {"error": "Failed to upload image", "details": str(e)},
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )

@api_view(["GET"])
def list_staff(request):
    query = db.collection('staff')
    location_id = request.GET.get('location_id')
    if location_id:
        query = query.where(filter=FieldFilter('location_id', '==', location_id))
    
    staff_list = []
    try:
        docs = query.order_by('name').stream() 
        for doc in docs:
            staff_data = doc.to_dict()
            staff_data['id'] = doc.id 
            if 'face_encodings' in staff_data:
                del staff_data['face_encodings'] 
            staff_list.append(staff_data)
        return Response(staff_list, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": f"Failed to list staff: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(["DELETE"])
def delete_staff(request, staff_id):
    if not staff_id:
        return Response({"error": "Staff ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
    staff_doc_ref = db.collection('staff').document(staff_id)
    try:
        doc = staff_doc_ref.get()
        if not doc.exists:
            return Response({"error": "Staff member not found"}, status=status.HTTP_404_NOT_FOUND)
            
        staff_doc_ref.delete()
        # _load_known_staff_encodings() # No need to reload cache
        print(f"DEBUG: Deleted staff member with ID: {staff_id}")
        return Response(status=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        print(f"ERROR: Failed to delete staff member: {e}")
        return Response(
            {"error": "Failed to delete staff member", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
def punch_attendance(request):
    staff_id = request.data.get('staff_id')
    punch_type = request.data.get('type') 
    
    if not staff_id or not punch_type:
        return Response({"error": "Missing staff_id or punch_type"}, status=status.HTTP_400_BAD_REQUEST)
    
    if punch_type not in ['clock_in', 'clock_out']:
        return Response({"error": "Invalid punch_type. Must be 'clock_in' or 'clock_out'"}, status=status.HTTP_400_BAD_REQUEST)

    staff_doc = db.collection('staff').document(staff_id).get()
    if not staff_doc.exists:
        return Response({"error": "Staff member not found"}, status=status.HTTP_404_NOT_FOUND)

    attendance_data = {
        "staff_id": staff_id,
        "staff_name": staff_doc.to_dict().get('name', 'Unknown'), 
        "punch_type": punch_type,
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().date().isoformat(),
        "location_id": request.data.get('location_id', 'vailathur_cafe')
    }

    try:
        attendance_ref = db.collection('attendance_records')
        update_time, doc_ref = attendance_ref.add(attendance_data)
        print(f"DEBUG: Recorded attendance for {staff_id}: {punch_type} at {attendance_data['timestamp']}")
        return Response(
            {"message": "Attendance punched successfully", "punch_id": doc_ref.id},
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        print(f"ERROR: Failed to punch attendance: {e}")
        return Response(
            {"error": "Failed to punch attendance", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
@api_view(["PUT"])
def edit_staff(request, staff_id):
    """
    API endpoint to edit an existing staff member.
    """
    if not staff_id:
        return Response({"error": "Staff ID is required"}, status=status.HTTP_400_BAD_REQUEST)

    staff_ref = db.collection('staff').document(staff_id)
    try:
        if not staff_ref.get().exists:
            return Response({"error": "Staff member not found"}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        
        # Prepare the data for updating
        staff_data = {
            "name": data.get("name"),
            "role": data.get("role"),
            "contact_number": data.get("contact_number"),
            # Safely handle the salary conversion
            "salary": float(data.get("salary", 0.0)),
            "image_urls": data.get("image_urls", []),
        }
        
        # Use .update() to change only the specified fields
        staff_ref.update(staff_data)
        
        return Response({"message": "Staff member updated successfully", "staff_id": staff_id}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f"Failed to update staff member: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- FIX: Comment out the entire recognize_face function ---
# @api_view(["POST"])
# def recognize_face(request): 
#     """
#     API endpoint to receive an image, detect faces, and identify staff.
#     """
#     if 'file' not in request.FILES:
#         return Response({"error": "No image file provided."}, status=status.HTTP_400_BAD_REQUEST)

#     uploaded_file = request.FILES['file']
#     camera_id = request.data.get('camera_id', 'Unknown_Camera') # Allow camera_id from request

#     try:
#         image_array = np.frombuffer(uploaded_file.read(), np.uint8)
#         unknown_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

#         if unknown_image is None:
#             return Response({"error": "Could not decode image."}, status=status.HTTP_400_BAD_REQUEST)

#         face_locations = face_recognition.face_locations(unknown_image)
#         unknown_face_encodings = face_recognition.face_encodings(unknown_image, face_locations)

#         identified_staff_members = []
        
#         if not _known_staff_encodings:
#             _load_known_staff_encodings()

#         if not _known_staff_encodings:
#             return Response({"message": "No staff faces registered for recognition. Please add staff with images."}, status=status.HTTP_200_OK)

#         for unknown_encoding in unknown_face_encodings:
#             for staff_id, known_encodings_for_staff_list in _known_staff_encodings.items(): 
#                 if not known_encodings_for_staff_list: 
#                     continue

#                 matches = face_recognition.compare_faces(known_encodings_for_staff_list, unknown_encoding, tolerance=0.5) 
                
#                 if True in matches:
#                     face_distances = face_recognition.face_distance(known_encodings_for_staff_list, unknown_encoding)
#                     best_match_distance = np.min(face_distances)

#                     identified_staff_name = _staff_names_by_id.get(staff_id, staff_id)
#                     identified_staff_members.append({"staff_id": staff_id, "name": identified_staff_name, "confidence": float(best_match_distance)}) 
                    
#                     observation_data = {
#                         "staff_id": identified_staff_name, 
#                         "staff_name": identified_staff_name,
#                         "detected_activity": "present_by_cctv", 
#                         "camera_id": camera_id,
#                         "timestamp": datetime.now().isoformat(),
#                         "date": datetime.now().date().isoformat(),
#                         "confidence": float(best_match_distance)
#                     }
#                     db.collection('cctv_observations').add(observation_data)
#                     print(f"DEBUG: Recognized {identified_staff_name} on camera {camera_id}.")
#                     break 

#         if identified_staff_members:
#             return Response({"message": "Faces recognized and observations logged.", "identified_staff": identified_staff_members}, status=status.HTTP_200_OK)
#         else:
#             return Response({"message": "No familiar faces recognized in the image."}, status=status.HTTP_200_OK)

#     except Exception as e:
#         print(f"ERROR: Facial recognition failed: {e}")
#         return Response(
#             {"error": "Facial recognition failed", "details": str(e)},
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )


@api_view(["GET"])
def get_cctv_observation_report(request): 
    # This function can remain as is, it will just return empty data
    # since no new observations can be logged.
    return Response({"report": "CCTV reporting is disabled in this version.", "structured_data": {}}, status=status.HTTP_200_OK)

@api_view(["GET"])
def get_staff_attendance_report(request):
    staff_id = request.GET.get('staff_id')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # 1. Fetch all staff details first (name, daily salary)
    staff_details = {}
    try:
        staff_query = db.collection('staff')
        if staff_id and staff_id != 'All Staff':
            doc = staff_query.document(staff_id).get()
            if doc.exists:
                 staff_details[doc.id] = doc.to_dict()
        else:
            for doc in staff_query.stream():
                staff_details[doc.id] = doc.to_dict()
    except Exception as e:
        return Response({"error": f"Could not fetch staff data: {e}"}, status=500)

    # 2. Get all attendance punches in the date range
    attendance_punches = {}
    try:
        attendance_query = db.collection('attendance_records').order_by('timestamp')
        if start_date_str:
            attendance_query = attendance_query.where(filter=FieldFilter('date', '>=', start_date_str))
        if end_date_str:
            attendance_query = attendance_query.where(filter=FieldFilter('date', '<=', end_date_str))

        for doc in attendance_query.stream():
            record = doc.to_dict()
            s_id = record.get('staff_id')
            if s_id not in attendance_punches:
                attendance_punches[s_id] = []
            attendance_punches[s_id].append(record)
    except Exception as e:
        return Response({"error": f"Failed to retrieve attendance records: {e}"}, status=500)

    # 3. Process data for each staff member
    salary_report_list = []
    
    for s_id, details in staff_details.items():
        punches = attendance_punches.get(s_id, [])
        present_days = set()
        total_duration = timedelta()
        clock_in_time = None

        for punch in punches:
            present_days.add(punch.get('date'))
            punch_time = datetime.fromisoformat(punch['timestamp'])
            punch_type = punch['punch_type']

            if punch_type == 'clock_in':
                clock_in_time = punch_time
            elif punch_type == 'clock_out' and clock_in_time:
                total_duration += punch_time - clock_in_time
                clock_in_time = None
        
        days_present = len(present_days)
        total_hours_worked = total_duration.total_seconds() / 3600
        daily_salary = float(details.get('salary', 0.0))
        salary_due = daily_salary * days_present

        # 4. Check if this salary period has already been paid
        payment_doc_id = f"{s_id}_{start_date_str}_{end_date_str}"
        payment_doc = db.collection('salary_payments').document(payment_doc_id).get()

        salary_report_list.append({
            "staff_id": s_id,
            "staff_name": details.get("name", "Unknown"),
            "total_days_present": days_present,
            "total_hours_worked": round(total_hours_worked, 2), # New field
            "total_salary_due": round(salary_due, 2),
            "is_paid": payment_doc.exists
        })
        
    return Response(salary_report_list, status=status.HTTP_200_OK)

# --- NEW FUNCTION ---
@api_view(["POST"])
def mark_salary_as_paid(request):
    data = request.data
    staff_id = data.get('staff_id')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    amount = data.get('amount')
    status = data.get('status') # This will be True to pay, False to un-pay

    if not all([staff_id, start_date, end_date, amount is not None, status is not None]):
        return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

    payment_doc_id = f"{staff_id}_{start_date}_{end_date}"
    payment_ref = db.collection('salary_payments').document(payment_doc_id)
    expense_ref = db.collection('expenses').document(f"salary_{payment_doc_id}")
    
    try:
        if status is True: # If the app is marking the salary as PAID
            # 1. Create a payment record
            payment_ref.set({
                "staff_id": staff_id,
                "amount": amount,
                "payment_date": datetime.now().strftime('%Y-%m-%d'),
                "period_start": start_date,
                "period_end": end_date,
                "expense_doc_id": expense_ref.id,
            })
            # 2. Create a corresponding expense record for P&L reports
            expense_ref.set({
                "category": "Salary",
                "amount": amount,
                "date": datetime.now().strftime('%Y-%m-%d'),
                "description": f"Salary for staff ID {staff_id} for period {start_date} to {end_date}"
            })
            return Response({"message": "Salary marked as paid and expense recorded."}, status=status.HTTP_200_OK)
        
        else: # If the app is marking the salary as UNPAID
            # Delete both the payment and the expense record
            batch = db.batch()
            batch.delete(payment_ref)
            batch.delete(expense_ref)
            batch.commit()
            return Response({"message": "Salary payment and expense record reverted."}, status=status.HTTP_200_OK)
            
    except Exception as e:
        return Response({"error": f"An error occurred: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def record_cctv_observation(request):
    # This function can remain as is, it will just return an error
    # if called, which is fine since the frontend won't call it.
    return Response({"error": "CCTV observation is disabled in this version."}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
def delete_attendance_logs(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    staff_id = request.GET.get('staff_id')

    if not start_date or not end_date:
        return Response({'error': 'Start date and end date are required for deletion.'}, status=400)
    
    try:
        query = db.collection('attendance_records').where(filter=FieldFilter('date', '>=', start_date)).where(filter=FieldFilter('date', '<=', end_date))
        
        if staff_id and staff_id != 'All Staff':
            query = query.where(filter=FieldFilter('staff_id', '==', staff_id))

        docs_to_delete = list(query.stream())
        
        if not docs_to_delete:
            return Response({'message': 'No attendance logs found in the selected range to delete.'}, status=200)

        batch = db.batch()
        for doc in docs_to_delete:
            batch.delete(doc.reference)
        batch.commit()

        return Response({'message': f'Successfully deleted {len(docs_to_delete)} attendance records.'}, status=200)

    except Exception as e:
        print(f"ERROR deleting attendance logs: {e}")
        return Response({'error': f'An unexpected error occurred during deletion: {e}'}, status=500)


@api_view(["GET"])
def get_last_punch_status(request, staff_id):
    if not staff_id:
        return Response({"error": "Staff ID is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        query = db.collection('attendance_records').where(
            filter=FieldFilter('staff_id', '==', staff_id)
        ).order_by(
            'timestamp', direction=firestore.Query.DESCENDING
        ).limit(1)

        docs = list(query.stream())

        if not docs:
            return Response({"last_punch": "none"}, status=status.HTTP_200_OK)
        
        last_punch_record = docs[0].to_dict()
        return Response({
            "last_punch": last_punch_record.get('punch_type')
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"ERROR: Failed to get last punch status for {staff_id}: {e}")
        return Response(
            {"error": "Failed to retrieve last punch status", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
