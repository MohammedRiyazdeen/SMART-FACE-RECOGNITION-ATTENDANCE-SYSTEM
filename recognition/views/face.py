from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import cv2
import json
from ..models import Student, OrderSchedule
from ..face_system import face_system
from .attendance import get_day_order, is_attendance_open


@login_required
def register(request):
    """Face registration page"""
    if request.user.role == 'teacher':
        messages.warning(request, "face registration is for students only.")
        return redirect('teacher_dashboard')
        
    count = len(face_system.known_faces.get(request.user.rollno, []))
    is_registered = count >= 20
    
    return render(request, 'recognition/register.html', {
        'registered_count': count,
        'is_registered': is_registered
    })


def recognize(request):
    """Public face recognition page - no login required"""
    period = request.session.get('active_period')
    if not period:
        return redirect('select_period')

    is_open, msg = is_attendance_open(period)
    if not is_open:
        return render(request, 'recognition/select_period.html', {'error': msg, 'is_registered': True})

    # The precise subject will be assigned when the backend marks attendance
    # because it needs to know the student's department from the recognized face
    subject_name = f"Period {period}"

    # Determine current/next period based on time
    from .attendance import get_attendance_windows
    from datetime import datetime
    now = datetime.now().time()
    windows = get_attendance_windows()
    
    period_status_label = ""
    period_status_type = ""  # "active", "next", "done"
    
    # Find if any period is currently active
    active_found = False
    for pid, label, start, end in windows:
        if start <= now <= end:
            period_status_label = f"Period {pid} ({label}) — Active Now"
            period_status_type = "active"
            active_found = True
            break
    
    if not active_found:
        # Find the next upcoming period
        next_period = None
        for pid, label, start, end in windows:
            if now < start:
                if next_period is None or start < next_period[2]:
                    next_period = (pid, label, start, end)
        
        if next_period:
            pid, label, start, end = next_period
            period_status_label = f"Next Up: Period {pid} ({label}) at {start.strftime('%I:%M %p')}"
            period_status_type = "next"
        else:
            period_status_label = "All periods done for today"
            period_status_type = "done"

    return render(request, 'recognition/recognize.html', {
        'registered_faces': {},
        'period': period,
        'period_name': subject_name,
        'period_status_label': period_status_label,
        'period_status_type': period_status_type,
    })


def generate_frames_register():
    """Generate video frames for registration with face detection"""
    camera = face_system.get_camera()

    while True:
        success, frame = camera.read()
        if not success:
            break

        # Detect faces
        faces, _ = face_system.detect_faces_only(frame)

        # Draw rectangles around detected faces
        for face in faces:
            x, y, w, h = face['x'], face['y'], face['w'], face['h']
            color = (0, 255, 0) if len(faces) == 1 else (0, 165, 255)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

            if len(faces) == 1:
                cv2.putText(frame, "Ready to capture", (x, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            elif len(faces) > 1:
                cv2.putText(frame, "Multiple faces!", (x, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

        if len(faces) == 0:
            cv2.putText(frame, "No face detected", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Encode frame
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


def generate_frames_recognize(user_id=None):
    """Generate video frames for recognition with face recognition"""
    face_system.clear_recognition_state()  # Clear any stale recognition from previous period
    camera = face_system.get_camera()

    while True:
        success, frame = camera.read()
        if not success:
            break

        # Detect and recognize faces, filtering for specific user if provided
        results = face_system.detect_and_recognize(frame, target_id=user_id)

        # Draw rectangles and labels ONLY for recognized faces
        for result in results:
            x, y, w, h = result['x'], result['y'], result['w'], result['h']
            name = result['name']
            confidence = result['confidence']

            # Skip drawing the 'Unknown' red box entirely
            if name == "Unknown":
                continue

            # Color for recognized face
            color = (0, 255, 0)

            # Draw rectangle
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

            # Draw label background
            label_text = f"{name} ({int(confidence)})"

            cv2.rectangle(frame, (x, y-35), (x+w, y), color, cv2.FILLED)
            cv2.putText(frame, label_text, (x+6, y-6),
                       cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)

        # Display info
        registered = face_system.get_registered_faces()
        # Only show if THIS user is registered
        is_registered = user_id in registered if user_id else False
        info_text = "Face Registered" if is_registered else "Face Not Registered"

        cv2.putText(frame, info_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Encode frame
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


def video_feed_register(request):
    """Video streaming route for registration"""
    if request.user.is_authenticated and request.user.role == 'teacher':
        return StreamingHttpResponse(status=403)
    return StreamingHttpResponse(generate_frames_register(),
                                content_type='multipart/x-mixed-replace; boundary=frame')


def video_feed_recognize(request):
    """Video streaming route for recognition - public, recognizes ALL registered faces"""
    return StreamingHttpResponse(generate_frames_recognize(user_id=None),
                                content_type='multipart/x-mixed-replace; boundary=frame')


@csrf_exempt
@login_required
def reset_face(request):
    """API endpoint to clear existing face data for rescan"""
    if request.method == 'POST':
        try:
            name = request.user.rollno
            face_system.clear_registration(name)
            face_system.save_known_faces()
            face_system.train_recognizer()
            return JsonResponse({'success': True, 'message': 'Face data cleared. Ready for rescan.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@csrf_exempt
@login_required
def capture_face(request):
    """API endpoint to capture a face for registration"""
    if request.user.role == 'teacher':
         return JsonResponse({'success': False, 'error': 'Teachers cannot register faces'})

    if request.method == 'POST':
        try:
            # Use logged-in user's roll number as the unique identifier
            name = request.user.rollno

            # Helper to process image data
            import numpy as np
            import base64

            data = json.loads(request.body)
            # Check if image data is provided (frontend capture)
            image_data = data.get('image')

            frame = None
            if image_data:
                # Convert base64 to image
                encoded_data = image_data.split(',')[1]
                nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            else:
                # Backend capture (if frontend sends null/empty)
                frame = face_system.capture_frame()

            if frame is None:
                return JsonResponse({'success': False, 'error': 'Failed to capture frame from camera'})

            # Extract face
            face_roi, coords = face_system.extract_face(frame)

            if face_roi is None:
                return JsonResponse({'success': False, 'error': 'No single face detected'})

            # Get current count
            count = len(face_system.known_faces.get(name, []))

            # Already registered? Reject capture
            if count >= 20:
                # Ensure it's finalized just in case
                face_system.finalize_registration(name)
                return JsonResponse({
                    'success': False,
                    'error': 'Already registered 20 faces.',
                    'complete': True,
                    'count': count
                })

            # Add face sample using rollno
            face_system.add_face_sample(name, face_roi)
            
            # Update count after adding
            count += 1

            # If we have reached enough samples, finalize
            if count >= 20:
                success = face_system.finalize_registration(name)
                return JsonResponse({
                    'success': True,
                    'count': count,
                    'complete': True,
                    'message': f'Successfully registered {request.user.name}!'
                })

            return JsonResponse({
                'success': True,
                'count': count,
                'complete': False
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@csrf_exempt
def stop_camera(request):
    """API endpoint to stop the camera"""
    if request.method == 'POST':
        try:
            face_system.clear_recognition_state()  # Clear stale state to prevent false attendance
            face_system.release_camera()
            return JsonResponse({'success': True, 'message': 'Camera stopped successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def check_status(request):
    """API endpoint to check current recognition status - public"""
    current = face_system.get_current_recognition()

    if current and current.get('name') and current['name'] != 'Unknown':
        # Look up student name from rollno for display
        response_data = current.copy()
        try:
            student = Student.objects.get(rollno=current['name'])
            response_data['display_name'] = student.name
        except Student.DoesNotExist:
            response_data['display_name'] = current['name']
        return JsonResponse({'recognition': response_data})

    return JsonResponse({'recognition': None})


def get_registered_faces(request):
    """API endpoint to get list of registered faces"""
    all_registered = face_system.get_registered_faces()

    # STRICT PRIVACY: Only return the logged-in user's data
    if request.user.is_authenticated:
        user_key = request.user.rollno
        if user_key in all_registered:
            # Return dict with just this user, mapped to display name
            return JsonResponse({'faces': {request.user.name: all_registered[user_key]}})

    return JsonResponse({'faces': {}})
