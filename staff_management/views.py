# In staff_management/views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
from bakery_ai_manager.firestore_client import get_firestore_client
from google.cloud.firestore_v1.base_query import FieldFilter
# All other imports (storage, face_recognition, etc.) are assumed to be here
import face_recognition
import numpy as np
import cv2
import requests
from google.cloud import storage


db = get_firestore_client()
GCS_BUCKET_NAME = 'manger-ai-staff-images'
try:
    storage_client = storage.Client()
    gcs_bucket = storage_client.bucket(GCS_BUCKET_NAME)
    print(f"DEBUG: GCS client initialized for bucket: {GCS_BUCKET_NAME}")
except Exception as e:
    print(f"ERROR: Failed to initialize GCS client: {e}")
    gcs_bucket = None
# --- Cache for known staff encodings ---
_known_staff_encodings = {}
_staff_names_by_id = {}

# --- Helper function for face encoding from image URLs ---
def _generate_face_encodings(image_urls):
    encodings_for_all_images = []
    for url in image_urls:
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            image_array = np.frombuffer(response.content, np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if img is None:
                print(f"WARNING: Could not decode image from URL: {url}")
                continue

            face_encodings_in_image = face_recognition.face_encodings(img)
            if face_encodings_in_image:
                for encoding in face_encodings_in_image:
                    encodings_for_all_images.append(encoding.tolist())
            else:
                print(f"WARNING: No face found in image from URL: {url}")
        except Exception as e:
            print(f"ERROR: Failed to process image {url} for encoding: {e}")
    return encodings_for_all_images

# --- Helper function to load all staff encodings from Firestore into cache ---
def _load_known_staff_encodings():
    global _known_staff_encodings, _staff_names_by_id
    _known_staff_encodings = {}
    _staff_names_by_id = {}
    print("DEBUG: Loading known staff encodings from Firestore...")
    try:
        staff_docs = db.collection('staff').stream()
        for doc in staff_docs:
            staff_data = doc.to_dict()
            staff_id = doc.id
            staff_name = staff_data.get('name', 'Unknown Staff')
            
            face_encodings_flat = staff_data.get('face_encodings', [])
            
            if face_encodings_flat and isinstance(face_encodings_flat, list) and len(face_encodings_flat) > 0:
                if len(face_encodings_flat) % 128 == 0:
                    num_encodings = len(face_encodings_flat) // 128
                    reshaped_encodings = np.array(face_encodings_flat).reshape(num_encodings, 128)
                    _known_staff_encodings[staff_id] = [np.array(e) for e in reshaped_encodings]
                    _staff_names_by_id[staff_id] = staff_name
                else:
                    print(f"WARNING: Face encodings for {staff_id} have invalid length. Skipping.")
        print(f"DEBUG: Loaded {len(_known_staff_encodings)} staff members for recognition.")
    except Exception as e:
        print(f"ERROR: Failed to load known staff encodings for recognition cache: {e}")

# Load encodings once at Django server startup
_load_known_staff_encodings()

@api_view(["POST"])
def add_staff(request):
    """
    API endpoint to add a new staff member.
    Generates and stores face encodings.
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

    image_urls = request.data.get("image_urls", [])
    
    # Generate face encodings from provided image_urls
    all_face_encodings_flat = [] 
    if image_urls:
        list_of_encodings_lists = _generate_face_encodings(image_urls)
        
        for encoding_list in list_of_encodings_lists:
            all_face_encodings_flat.extend(encoding_list) 

        if not all_face_encodings_flat:
            return Response({"error": "No recognizable faces found in provided images for encoding. Please ensure faces are clear and visible."}, status=status.HTTP_400_BAD_REQUEST)
    
    staff_data = {
        "name": staff_name,
        "role": request.data.get("role"),
        "contact_number": request.data.get("contact_number"),
        "address": request.data.get("address", ""),
        "emergency_contact": request.data.get("emergency_contact", ""),
        "image_urls": image_urls, 
        "face_encodings": all_face_encodings_flat, # Store as a single, flattened list of floats
        "location_id": request.data.get("location_id", ""), 
        "salary": float(request.data.get("salary")), 
        "created_at": datetime.now().isoformat()
    }

    try:
        db.collection('staff').document(staff_id).set(staff_data)
        _load_known_staff_encodings() # Reload cache after new staff is added
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


@api_view(["POST"])
def upload_staff_image(request):

    if gcs_bucket is None:
        return Response({"error": "Google Cloud Storage is not initialized."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if 'file' not in request.FILES:
        return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
    
    uploaded_file = request.FILES['file']
    destination_blob_name = f"staff_images/{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{uploaded_file.name.replace(' ', '_')}"

    try:
        blob = gcs_bucket.blob(destination_blob_name)
        blob.upload_from_file(uploaded_file.file, content_type=uploaded_file.content_type)
        
        blob.make_public()
        public_url = blob.public_url

        print(f"DEBUG: Image uploaded to GCS: {public_url}")
        return Response(
            {"message": "Image uploaded successfully", "image_url": public_url},
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        print(f"ERROR: Failed to upload image to GCS: {e}")
        return Response(
            {"error": "Failed to upload image", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

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
    """
    API endpoint to delete a staff member by ID.
    """
    if not staff_id:
        return Response({"error": "Staff ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
    staff_doc_ref = db.collection('staff').document(staff_id)
    try:
        doc = staff_doc_ref.get()
        if not doc.exists:
            return Response({"error": "Staff member not found"}, status=status.HTTP_404_NOT_FOUND)
            
        staff_doc_ref.delete()
        _load_known_staff_encodings() # Reload cache to remove deleted staff
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
    """
    API endpoint for staff to punch in/out.
    """
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
        "location_id": request.data.get('location_id', 'vailathur_cafe') # Default to Vailathur Cafe
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

@api_view(["POST"])
def recognize_face(request): 
    """
    API endpoint to receive an image, detect faces, and identify staff.
    """
    if 'file' not in request.FILES:
        return Response({"error": "No image file provided."}, status=status.HTTP_400_BAD_REQUEST)

    uploaded_file = request.FILES['file']
    camera_id = request.data.get('camera_id', 'Unknown_Camera') # Allow camera_id from request

    try:
        image_array = np.frombuffer(uploaded_file.read(), np.uint8)
        unknown_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if unknown_image is None:
            return Response({"error": "Could not decode image."}, status=status.HTTP_400_BAD_REQUEST)

        face_locations = face_recognition.face_locations(unknown_image)
        unknown_face_encodings = face_recognition.face_encodings(unknown_image, face_locations)

        identified_staff_members = []
        
        if not _known_staff_encodings:
            _load_known_staff_encodings()

        if not _known_staff_encodings:
            return Response({"message": "No staff faces registered for recognition. Please add staff with images."}, status=status.HTTP_200_OK)

        for unknown_encoding in unknown_face_encodings:
            for staff_id, known_encodings_for_staff_list in _known_staff_encodings.items(): 
                if not known_encodings_for_staff_list: 
                    continue

                matches = face_recognition.compare_faces(known_encodings_for_staff_list, unknown_encoding, tolerance=0.5) 
                
                if True in matches:
                    face_distances = face_recognition.face_distance(known_encodings_for_staff_list, unknown_encoding)
                    best_match_distance = np.min(face_distances)

                    identified_staff_name = _staff_names_by_id.get(staff_id, staff_id)
                    identified_staff_members.append({"staff_id": staff_id, "name": identified_staff_name, "confidence": float(best_match_distance)}) 
                    
                    # Log observation for the identified staff
                    observation_data = {
                        "staff_id": identified_staff_name, 
                        "staff_name": identified_staff_name,
                        "detected_activity": "present_by_cctv", 
                        "camera_id": camera_id,
                        "timestamp": datetime.now().isoformat(),
                        "date": datetime.now().date().isoformat(),
                        "confidence": float(best_match_distance)
                    }
                    db.collection('cctv_observations').add(observation_data)
                    print(f"DEBUG: Recognized {identified_staff_name} on camera {camera_id}.")
                    break 

        if identified_staff_members:
            return Response({"message": "Faces recognized and observations logged.", "identified_staff": identified_staff_members}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "No familiar faces recognized in the image."}, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"ERROR: Facial recognition failed: {e}")
        return Response(
            {"error": "Facial recognition failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
def get_cctv_observation_report(request): 
    """
    API endpoint to retrieve CCTV observation records, with optional filtering.
    """
    staff_id = request.query_params.get('staff_id')
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')
    camera_id = request.query_params.get('camera_id')

    cctv_observations_ref = db.collection('cctv_observations')
    query = cctv_observations_ref

    if staff_id:
        query = query.where('staff_id', '==', staff_id)
    if start_date_str:
        query = query.where('date', '>=', start_date_str)
    if end_date_str:
        query = query.where('date', '<=', end_date_str)
    if camera_id:
        query = query.where('camera_id', '==', camera_id)

    query = query.order_by('staff_id').order_by('timestamp')

    observation_summary_data = {} 
    
    found_data = False

    try:
        docs = query.stream()
        for doc in docs:
            found_data = True
            record = doc.to_dict()
            s_id = record['staff_id']
            activity = record.get('detected_activity', 'unknown')
            camera = record.get('camera_id', 'unknown')
            timestamp = record.get('timestamp', 'N/A')
            staff_name = record.get('staff_name', s_id)
            
            if s_id not in observation_summary_data:
                observation_summary_data[s_id] = {
                    'name': staff_name,
                    'activities': {},
                    'cameras': {},
                    'observations_list': [] 
                }
            
            observation_summary_data[s_id]['activities'][activity] = observation_summary_data[s_id]['activities'].get(activity, 0) + 1
            observation_summary_data[s_id]['cameras'][camera] = observation_summary_data[s_id]['cameras'].get(camera, 0) + 1
            observation_summary_data[s_id]['observations_list'].append({
                'timestamp': timestamp,
                'activity': activity,
                'camera_id': camera
            })

        report_lines = []
        report_lines.append("CCTV Observation Report:\n")
        report_lines.append("----------------------------\n")

        if not found_data:
            report_lines.append("No CCTV observations found for the selected criteria.")
        else:
            for s_id, data in sorted(observation_summary_data.items(), key=lambda item: item[1]['name']):
                report_lines.append(f"\nStaff: {data['name']} (ID: {s_id})\n")
                
                report_lines.append("  Activity Summary:\n")
                for act, count in sorted(data['activities'].items()):
                    report_lines.append(f"    - {act.replace('_', ' ').title()}: {count} times\n")
                
                report_lines.append("  Camera Interactions:\n")
                for cam, count in sorted(data['cameras'].items()):
                    report_lines.append(f"    - {cam}: {count} times\n")
                
                report_lines.append("  Detailed Observations (Chronological):\n")
                for obs in sorted(data['observations_list'], key=lambda x: x['timestamp']):
                    report_lines.append(f"    - {obs['activity'].replace('_', ' ').title()} on {obs['camera_id']} at {datetime.fromisoformat(obs['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}\n")

        report_text = "".join(report_lines)
        
        return Response({
            "report": report_text,
            "structured_data": observation_summary_data 
        }, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"ERROR: Failed to retrieve CCTV observation report: {e}")
        return Response(
            {"error": "Failed to retrieve CCTV observation report", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
def get_staff_attendance_report(request):
    staff_id = request.GET.get('staff_id')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    staff_salaries = {}
    try:
        staff_docs = db.collection('staff').stream()
        for doc in staff_docs:
            staff_info = doc.to_dict()
            staff_salaries[doc.id] = {
                "name": staff_info.get('name', 'Unknown'),
                "salary": float(staff_info.get('salary', 0.0))
            }
    except Exception as e:
        return Response({"error": f"Could not fetch staff salary data: {e}"}, status=500)

    query = db.collection('attendance_records')
    if staff_id and staff_id != 'All Staff':
        query = query.where(filter=FieldFilter('staff_id', '==', staff_id))
    if start_date_str:
        query = query.where(filter=FieldFilter('date', '>=', start_date_str))
    if end_date_str:
        query = query.where(filter=FieldFilter('date', '<=', end_date_str))
    
    query = query.order_by('staff_id').order_by('timestamp')

    attendance_data = {}
    try:
        docs = query.stream()
        for doc in docs:
            record = doc.to_dict()
            s_id = record['staff_id']
            if s_id not in attendance_data:
                staff_name = staff_salaries.get(s_id, {}).get('name', 'Unknown')
                attendance_data[s_id] = {
                    'name': record.get('staff_name', staff_name), 
                    'punches': []
                }
            attendance_data[s_id]['punches'].append(record)
    except Exception as e:
        return Response({"error": f"Failed to retrieve attendance records: {e}"}, status=500)

    report_lines = ["Staff Attendance and Salary Report:\n", "----------------------------------\n"]
    if not attendance_data:
        report_lines.append("No attendance records found for the selected criteria.")
    else:
        sorted_staff_data = sorted(attendance_data.items(), key=lambda item: item[1]['name'])
        for s_id, data in sorted_staff_data:
            report_lines.append(f"\nStaff: {data['name']} (ID: {s_id})\n")
            total_duration = timedelta()
            clock_in_time = None
            for punch in data['punches']:
                punch_time = datetime.fromisoformat(punch['timestamp'])
                punch_type = punch['punch_type']
                report_lines.append(f"  - {punch_type.replace('_', ' ').title()} at {punch_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                if punch_type == 'clock_in':
                    clock_in_time = punch_time
                elif punch_type == 'clock_out' and clock_in_time:
                    duration = punch_time - clock_in_time
                    total_duration += duration
                    days, remainder = divmod(duration.total_seconds(), 86400)
                    hours, remainder = divmod(remainder, 3600)
                    minutes, _ = divmod(remainder, 60)
                    duration_str = f"{int(days)}d {int(hours)}h {int(minutes)}m"
                    report_lines.append(f"    (Duration: {duration_str})\n")
                    clock_in_time = None
            total_hours_worked = total_duration.total_seconds() / 3600
            salary_per_hour = staff_salaries.get(s_id, {}).get('salary', 0.0)
            estimated_salary = total_hours_worked * salary_per_hour
            report_lines.append(f"  Total Hours Worked in Period: {total_hours_worked:.2f} hours\n")
            report_lines.append(f"  Hourly Salary: ₹{salary_per_hour:.2f}\n")
            report_lines.append(f"  Estimated Earnings for Period: ₹{estimated_salary:.2f}\n")

    report_text = "".join(report_lines)
    return Response({"report": report_text, "structured_data": attendance_data}, status=status.HTTP_200_OK)

@api_view(["POST"])
def record_cctv_observation(request):
    """
    API endpoint to record a simulated CCTV observation.
    """
    required_fields = ["staff_id", "detected_activity", "camera_id"]
    for field in required_fields:
        if field not in request.data:
            return Response(
                {"error": f"Missing required field: {field}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    staff_id = request.data.get('staff_id')
    detected_activity = request.data.get('detected_activity')
    camera_id = request.data.get('camera_id')

    staff_doc = db.collection('staff').document(staff_id).get()
    if not staff_doc.exists:
        return Response({"error": "Staff member not found"}, status=status.HTTP_404_NOT_FOUND)

    observation_data = {
        "staff_id": staff_id,
        "staff_name": staff_doc.to_dict().get('name', 'Unknown'),
        "detected_activity": detected_activity,
        "camera_id": camera_id,
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().date().isoformat(),
    }

    try:
        cctv_observations_ref = db.collection('cctv_observations')
        update_time, doc_ref = cctv_observations_ref.add(observation_data)
        print(f"DEBUG: Recorded CCTV observation for {staff_id} ({detected_activity}) on {camera_id}")
        return Response(
            {"message": "CCTV observation recorded successfully", "observation_id": doc_ref.id},
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        print(f"ERROR: Failed to record CCTV observation: {e}")
        return Response(
            {"error": "Failed to record CCTV observation", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
def get_cctv_observation_report(request): 
    """
    API endpoint to retrieve CCTV observation records, with optional filtering.
    """
    staff_id = request.query_params.get('staff_id')
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')
    camera_id = request.query_params.get('camera_id')

    cctv_observations_ref = db.collection('cctv_observations')
    query = cctv_observations_ref

    # Apply filters
    if staff_id:
        query = query.where('staff_id', '==', staff_id)
    if start_date_str:
        query = query.where('date', '>=', start_date_str)
    if end_date_str:
        query = query.where('date', '<=', end_date_str)
    if camera_id:
        query = query.where('camera_id', '==', camera_id)

    # Order by for consistent reporting (requires index if multiple filters)
    query = query.order_by('staff_id').order_by('timestamp')

    observation_summary_data = {} # {staff_id: {name: "", activities: {}, cameras: {}, observations_list: []}}
    
    found_data = False

    try:
        docs = query.stream()
        for doc in docs:
            found_data = True
            record = doc.to_dict()
            s_id = record['staff_id']
            activity = record.get('detected_activity', 'unknown')
            camera = record.get('camera_id', 'unknown')
            timestamp = record.get('timestamp', 'N/A')
            staff_name = record.get('staff_name', s_id) # Get staff name from record
            
            if s_id not in observation_summary_data:
                observation_summary_data[s_id] = {
                    'name': staff_name,
                    'activities': {},
                    'cameras': {},
                    'observations_list': [] # List of raw observation details for structured report
                }
            
            observation_summary_data[s_id]['activities'][activity] = observation_summary_data[s_id]['activities'].get(activity, 0) + 1
            observation_summary_data[s_id]['cameras'][camera] = observation_summary_data[s_id]['cameras'].get(camera, 0) + 1
            # Add full observation record to list for structured output
            observation_summary_data[s_id]['observations_list'].append({
                'timestamp': timestamp,
                'activity': activity,
                'camera_id': camera
            })

        # Generate text report (similar to get_sales_report)
        report_lines = []
        report_lines.append("CCTV Observation Report:\n")
        report_lines.append("----------------------------\n")

        if not found_data:
            report_lines.append("No CCTV observations found for the selected criteria.")
        else:
            for s_id, data in sorted(observation_summary_data.items(), key=lambda item: item[1]['name']):
                report_lines.append(f"\nStaff: {data['name']} (ID: {s_id})\n")
                
                report_lines.append("  Activity Summary:\n")
                for act, count in sorted(data['activities'].items()):
                    report_lines.append(f"    - {act.replace('_', ' ').title()}: {count} times\n")
                
                report_lines.append("  Camera Interactions:\n")
                for cam, count in sorted(data['cameras'].items()):
                    report_lines.append(f"    - {cam}: {count} times\n")
                
                report_lines.append("  Detailed Observations (Chronological):\n")
                # Join with newline to ensure each observation is on a new line
                # Fixed: Iterate through observations_list and format each dict to a string
                for obs in sorted(data['observations_list'], key=lambda x: x['timestamp']):
                    report_lines.append(f"    - {obs['activity'].replace('_', ' ').title()} on {obs['camera_id']} at {datetime.fromisoformat(obs['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}\n")

        report_text = "".join(report_lines)
        
        # Return both the formatted report string and the structured data
        return Response({
            "report": report_text,
            "structured_data": observation_summary_data # This is the structured data for potential charting
        }, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"ERROR: Failed to retrieve CCTV observation report: {e}")
        return Response(
            {"error": "Failed to retrieve CCTV observation report", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(['DELETE'])
def delete_attendance_logs(request):
    """
    Deletes all attendance records within a specified date range,
    optionally filtered by a staff member.
    """
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
    """
    Finds the very last attendance record for a given staff member
    to determine if their last action was a clock-in or clock-out.
    """
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
            # No records found, so the user's next action must be to clock in.
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