# cctv_video_processor.py
import cv2
import requests
import time
import os

# --- Configuration ---
# ⭐ IMPORTANT: Replace with the actual path to your video file for testing
# FIX: Use a raw string literal (prefix with r) to handle backslashes in Windows paths
VIDEO_PATH = r".\video\WhatsApp Video 2025-06-17 at 1.10.54 PM.mp4"
# Example: VIDEO_PATH = r'C:\Users\YourUser\Videos\test_footage.mp4'
# Alternatively, you could use forward slashes: "C:/Users/mxsab/OneDrive/Desktop/IMG_6678.MOV"

DJANGO_RECOGNIZE_FACE_URL = 'http://127.0.0.1:8000/staff/recognize-face/'
CAMERA_ID = 'Main_Entrance_Cam_01' # Identify which camera this footage is from
PROCESS_FRAME_INTERVAL_SECONDS = 5 # Process a frame every X seconds (simulate real-time)

# --- Main Script ---
def process_video_for_face_recognition():
    if not os.path.exists(VIDEO_PATH):
        print(f"ERROR: Video file not found at: {VIDEO_PATH}")
        print("Please update VIDEO_PATH in the script to your actual video file.")
        return

    cap = cv2.VideoCapture(VIDEO_PATH) 

    if not cap.isOpened():
        print(f"ERROR: Could not open video file: {VIDEO_PATH}")
        print("Possible reasons: Video file corrupted, unsupported codec, or missing OpenCV backend dependencies (e.g., FFmpeg).")
        return

    print(f"INFO: Starting video processing from: {VIDEO_PATH}")
    print(f"INFO: Sending observations to Django at: {DJANGO_RECOGNIZE_FACE_URL}")

    last_processed_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("INFO: End of video stream or frame could not be read.")
                break

            current_time = time.time()
            if current_time - last_processed_time < PROCESS_FRAME_INTERVAL_SECONDS:
                # Skip frames to simulate real-time processing interval
                continue

            last_processed_time = current_time

            # Encode the frame as JPEG (to send as a file)
            _, img_encoded = cv2.imencode('.jpg', frame)
            
            # Prepare multipart-formdata for the POST request
            files = {'file': ('cctv_frame.jpg', img_encoded.tobytes(), 'image/jpeg')}
            data = {'camera_id': CAMERA_ID}

            print(f"INFO: Sending frame from {CAMERA_ID} for recognition...")
            response = requests.post(DJANGO_RECOGNIZE_FACE_URL, files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                message = result.get('message', 'No message')
                identified_staff = result.get('identified_staff', [])
                
                if identified_staff:
                    names = ", ".join([s['name'] for s in identified_staff])
                    print(f"SUCCESS: Recognized: {names} (Camera: {CAMERA_ID})")
                else:
                    print(f"SUCCESS: {message} (Camera: {CAMERA_ID})")
            else:
                print(f"ERROR: Failed to recognize face. Status: {response.status_code}, Response: {response.text}")

            # Optional: Display the frame (uncomment for visual debugging, may slow down)
            # cv2.imshow('CCTV Frame', frame)
            # if cv2.waitKey(1) & 0xFF == ord('q'): # Press 'q' to quit
            #     break

            time.sleep(1) # Small delay to avoid hammering the CPU/API too fast

    except Exception as e:
        print(f"FATAL ERROR during video processing: {e}")
    finally:
        cap.release()
        # Removed: cv2.destroyAllWindows() as it causes error if GUI backend is not present

if __name__ == "__main__":
    print("NOTE: Ensure your Django server is running on http://127.0.0.1:8000/")
    print("NOTE: Ensure you have staff registered with images in your Flutter app.")
    process_video_for_face_recognition()

