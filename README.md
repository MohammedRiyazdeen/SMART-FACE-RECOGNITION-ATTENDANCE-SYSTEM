# Simple Face Recognition System

A lightweight and interactive face recognition system that can register faces and recognize them in real-time using your webcam. Built with OpenCV's Haar Cascade and LBPH (Local Binary Patterns Histograms) face recognizer.

## Features

- **Interactive Registration**: Captures 10 photos of your face for accurate recognition
- **Real-time Recognition**: Detects and identifies faces in live camera feed using LBPH algorithm
- **Voice Announcements**: Speaks out the person's name (e.g., "This is Riyaz's face") or "Unknown person detected"
- **Visual Feedback**: Shows bounding boxes around detected faces (green for known, red for unknown)
- **Confidence Score**: Displays recognition confidence for each detected face
- **Persistent Storage**: Saves registered faces for future use
- **Multiple Faces**: Can register and recognize multiple people

## Requirements

- Python 3.7 or higher
- Webcam
- Windows/Linux/Mac OS

## Installation

1. Install the required packages:
```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install opencv-contrib-python numpy pyttsx3
```

**Note**: The installation is much simpler than the original face-recognition library as we use OpenCV's built-in face recognition capabilities.

## Usage

1. Run the application:
```bash
python main_simple.py
```

2. **First Time Setup**:
   - Enter your name when prompted (e.g., "Riyaz")
   - The camera will open
   - Position your face in the frame (you'll see a green rectangle when detected)
   - Press **SPACE** to capture a photo (capture 10 photos with slight variations)
   - Try different angles and expressions for better accuracy
   - Press **Q** to quit registration early (need at least 5 photos)

3. **Face Recognition**:
   - After registration, press ENTER to start recognition
   - The camera will show live feed
   - When your face is detected, it will show your name and speak "This is Riyaz's face"
   - When an unknown face is detected, it will show "Unknown" and speak "Unknown person detected"
   - The confidence score is shown in parentheses (lower is better)
   - Press **Q** to quit

4. **Next Time**:
   - When you run the program again, it will load your saved face data
   - Choose option:
     - **(1)** Add more faces
     - **(2)** Start recognition directly
     - **(3)** View registered faces
     - **(4)** Exit

## How It Works

1. **Face Detection**:
   - Uses Haar Cascade Classifier to detect faces in video frames
   - Draws bounding boxes around detected faces

2. **Registration Phase**:
   - Captures multiple photos of your face
   - Converts images to grayscale
   - Resizes face regions to standard size (200x200)
   - Saves the face samples to `face_data.pkl`

3. **Training Phase**:
   - Uses LBPH (Local Binary Patterns Histograms) algorithm
   - Creates a model from all registered face samples
   - Assigns labels to each person

4. **Recognition Phase**:
   - Continuously captures frames from webcam
   - Detects faces using Haar Cascade
   - Compares detected faces with trained model using LBPH
   - Displays the name if confidence is high enough, otherwise shows "Unknown"
   - Announces the detection using text-to-speech

## Tips for Best Results

- Ensure good lighting when registering and recognizing
- Look directly at the camera during registration
- Capture photos with slight variations (different angles, expressions)
- Keep only one person in frame during registration
- Maintain a distance of 1-2 feet from the camera

## Troubleshooting

**Camera not opening**:
- Check if another application is using the camera
- Try changing the camera index in the code (0 to 1 or 2)

**Poor recognition accuracy**:
- Register more photos (modify `photos_needed` in code)
- Ensure good lighting conditions
- Re-register with better quality photos

**Installation errors**:
- Make sure you have Visual C++ Build Tools installed (Windows)
- Update pip: `pip install --upgrade pip`

## File Structure

```
face_recognition_project/
├── main.py              # Main application
├── requirements.txt     # Python dependencies
├── README.md           # This file
└── face_data.pkl       # Saved face data (created after first registration)
```

## Customization

You can customize the following in `main_simple.py`:

- `photos_needed`: Number of photos to capture during registration (default: 10)
- `recognition_confidence_threshold`: Face matching sensitivity (default: 70, lower = stricter)
- Haar Cascade parameters: `scaleFactor`, `minNeighbors`, `minSize` for detection tuning
- Frame processing: Adjust the modulo value in `frame_count % 30` to change speech frequency

## License

Free to use and modify for personal and educational purposes.
