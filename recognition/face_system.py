import cv2
import numpy as np
import os
import pickle
import threading
from datetime import datetime

class WebFaceRecognitionSystem:
    """Face recognition system adapted for web use with thread-safe operations"""
    
    def __init__(self):
        # Initialize face detector (OpenCV DNN)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        prototxt_path = os.path.join(base_dir, 'models_dnn', 'deploy.prototxt')
        model_path = os.path.join(base_dir, 'models_dnn', 'res10_300x300_ssd_iter_140000.caffemodel')
        self.net = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)
        
        # Initialize face recognizer (LBPH - Local Binary Patterns Histograms)
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        
        # Data storage
        self.data_file = "face_data.pkl"
        self.known_faces = {}  # {name: [face_samples]}
        self.is_trained = False
        self.label_map = {}
        self.current_recognition = None
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Stability check
        self.consecutive_frames = 0
        self.pending_name = None
        
        # Camera management
        self.camera = None
        self.camera_lock = threading.Lock()
        
        # Load existing data
        self.load_known_faces()
    
    def get_camera(self):
        """Get or create camera instance (thread-safe)"""
        with self.camera_lock:
            if self.camera is None or not self.camera.isOpened():
                self.camera = cv2.VideoCapture(0)
                # Set camera properties for better performance
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.camera.set(cv2.CAP_PROP_FPS, 30)
            return self.camera
    
    def release_camera(self):
        """Release camera (thread-safe)"""
        with self.camera_lock:
            if self.camera is not None:
                self.camera.release()
                self.camera = None

    def capture_frame(self):
        """Capture a single frame from the camera (thread-safe)"""
        with self.camera_lock:
            if self.camera is None or not self.camera.isOpened():
                return None
            success, frame = self.camera.read()
            if success:
                return frame
            return None
    
    def load_known_faces(self):
        """Load previously saved face data"""
        with self.lock:
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, 'rb') as f:
                        self.known_faces = pickle.load(f)
                    
                    # Train the recognizer with loaded data
                    if self.known_faces:
                        self.train_recognizer()
                    return True
                except Exception as e:
                    print(f"Error loading face data: {e}")
                    return False
            return False
    
    def save_known_faces(self):
        """Save face data to file"""
        with self.lock:
            try:
                with open(self.data_file, 'wb') as f:
                    pickle.dump(self.known_faces, f)
                return True
            except Exception as e:
                print(f"Error saving face data: {e}")
                return False
    
    def _augment_face(self, face_image):
        """Generate augmented versions of a face for better training"""
        augmented = []
        # 1. Horizontal flip
        augmented.append(cv2.flip(face_image, 1))
        # 2. Slightly brighter
        bright = cv2.convertScaleAbs(face_image, alpha=1.3, beta=20)
        augmented.append(bright)
        # 3. Slightly darker
        dark = cv2.convertScaleAbs(face_image, alpha=0.7, beta=-20)
        augmented.append(dark)
        return augmented

    def train_recognizer(self):
        """Train the face recognizer with known faces + augmented data"""
        faces = []
        labels = []
        label_map = {}
        
        for idx, (name, face_samples) in enumerate(self.known_faces.items()):
            label_map[idx] = name
            for face in face_samples:
                # Original sample
                faces.append(face)
                labels.append(idx)
                # Augmented samples (flip, bright, dark)
                for aug_face in self._augment_face(face):
                    faces.append(aug_face)
                    labels.append(idx)
        
        if faces:
            self.recognizer.train(faces, np.array(labels))
            self.label_map = label_map
            self.is_trained = True
        else:
            self.is_trained = False
    
    def add_face_sample(self, name, face_image):
        """Add a single face sample for a person"""
        with self.lock:
            if name not in self.known_faces:
                self.known_faces[name] = []
            self.known_faces[name].append(face_image)
    
    def finalize_registration(self, name):
        """Finalize registration and train the recognizer"""
        with self.lock:
            if name in self.known_faces and len(self.known_faces[name]) >= 5:
                self.save_known_faces()
                self.train_recognizer()
                return True
            return False
    
    def clear_registration(self, name):
        """Clear registration data for a person"""
        with self.lock:
            if name in self.known_faces:
                del self.known_faces[name]
    
    def get_registered_faces(self):
        """Get list of registered faces"""
        with self.lock:
            return {name: len(samples) for name, samples in self.known_faces.items()}
    
    def detect_and_recognize(self, frame, target_id=None):
        """Detect and recognize faces in a frame"""
        faces, gray = self.detect_faces_only(frame)
        
        results = []
        
        # Track if we found a valid match in this frame
        found_confirmed_match = False
        found_candidate_in_frame = False

        # Process each detected face
        for face_dict in faces:
            x, y, w, h = face_dict['x'], face_dict['y'], face_dict['w'], face_dict['h']
            
            # Extract face region
            face_roi = gray[y:y+h, x:x+w]
            if face_roi.size == 0:
                continue
            face_roi = cv2.resize(face_roi, (200, 200))
            face_roi = cv2.equalizeHist(face_roi)
            
            name = "Unknown"
            confidence = 100
            
            # Recognize the face if trained
            if self.is_trained:
                label, conf = self.recognizer.predict(face_roi)
                
                # Lower confidence value means better match (0 = perfect match)
                # Threshold tuned to 50 for stricter matching (was 70)
                if conf < 55:  # Stricter Threshold
                    predicted_name = self.label_map.get(label, "Unknown")
                    
                    # STRICT FILTERING: If a target_id is provided, only accept that specific user
                    if target_id:
                        if predicted_name == target_id:
                            name = predicted_name
                            confidence = conf
                        else:
                            # It's someone else, so treat as Unknown
                            name = "Unknown"
                            confidence = 100
                    else:
                        # No target_id (e.g. admin mode?), accept anyone
                        name = predicted_name
                        confidence = conf
            
            results.append({
                'x': int(x),
                'y': int(y),
                'w': int(w),
                'h': int(h),
                'name': name,
                'confidence': float(confidence)
            })
            
            # Update current recognition state (thread-safe)
            if name != "Unknown":
                found_candidate_in_frame = True
                
                # CONSECUTIVE FRAME VALIDATION
                # We need X consecutive frames of the same person to confirm recognition
                if name == self.pending_name:
                    self.consecutive_frames += 1
                else:
                    self.consecutive_frames = 1
                    self.pending_name = name
                
                # Threshold: 8 frames equals approx 0.5 - 1 second of steady recognition
                if self.consecutive_frames >= 8:
                    self.set_current_recognition(name, confidence)
                    found_confirmed_match = True
            
        # CRITICAL FIX:
        # 1. Only clear when we SAW a face but it was wrong (Unknown/different person).
        #    When no face in frame, DON'T clear - allows mark_attendance request to complete.
        #    get_current_recognition() expires results older than 5 seconds anyway.
        if not found_confirmed_match and found_candidate_in_frame:
            # We saw a face but it was Unknown or wrong person - clear immediately
            self.set_current_recognition(None, 0)
        # If no face in frame, leave previous recognition for grace period (expires in get)

        # 2. Only reset the counter if we didn't even see a CANDIDATE (i.e. different face or empty).
        # Note: If we saw "User A" but count < 8, found_candidate_in_frame is True, so we DO NOT reset.
        if not found_candidate_in_frame:
            self.consecutive_frames = 0
            self.pending_name = None
            
        return results


    def set_current_recognition(self, name, confidence):
        """Update the currently recognized face"""
        with self.lock:
            self.current_recognition = {
                'name': name,
                'confidence': float(confidence),
                'timestamp': datetime.now().timestamp()
            } if name else None

    def get_current_recognition(self, max_age_seconds=5):
        """Get the last recognized face. Returns None if recognition is older than max_age_seconds."""
        with self.lock:
            r = self.current_recognition
            if not r:
                return None
            age = datetime.now().timestamp() - r.get('timestamp', 0)
            if age > max_age_seconds:
                return None  # Expired
            return r

    def clear_recognition_state(self):
        """Clear recognition state - MUST be called when starting a new session or stopping camera
        to prevent stale recognition from a previous period causing false attendance marks."""
        with self.lock:
            self.current_recognition = None
            self.consecutive_frames = 0
            self.pending_name = None
    
    def detect_faces_only(self, frame):
        """Detect faces without recognition (for registration)"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = frame.shape[:2]
        
        # Prepare the frame for DNN
        blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0))
        self.net.setInput(blob)
        detections = self.net.forward()
        
        detected_faces = []
        for i in range(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            
            # Filter out weak detections (0.5 confidence threshold)
            if confidence > 0.5:
                # Compute the (x, y)-coordinates
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")
                
                # Ensure the bounding boxes fall within the dimensions of the frame
                startX = max(0, startX)
                startY = max(0, startY)
                endX = min(w, endX)
                endY = min(h, endY)
                
                width = endX - startX
                height = endY - startY
                
                if width > 0 and height > 0:
                    detected_faces.append({
                        'x': startX,
                        'y': startY,
                        'w': width,
                        'h': height
                    })
        
        return detected_faces, gray
    
    def extract_face(self, frame):
        """Extract a single face from frame for registration"""
        faces, gray = self.detect_faces_only(frame)
        
        if len(faces) == 1:
            face = faces[0]
            x, y, w, h = face['x'], face['y'], face['w'], face['h']
            face_roi = gray[y:y+h, x:x+w]
            
            if face_roi.size == 0:
                return None, None
                
            face_roi = cv2.resize(face_roi, (200, 200))
            face_roi = cv2.equalizeHist(face_roi)
            return face_roi, (x, y, w, h)
        
        return None, None

# Global instance
face_system = WebFaceRecognitionSystem()
