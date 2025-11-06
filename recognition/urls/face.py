from django.urls import path
from ..views import face

urlpatterns = [
    path('register/', face.register, name='register'),
    path('recognize/', face.recognize, name='recognize'),
    path('video_feed/register/', face.video_feed_register, name='video_feed_register'),
    path('video_feed/recognize/', face.video_feed_recognize, name='video_feed_recognize'),
    path('api/capture/', face.capture_face, name='capture_face'),
    path('api/reset/', face.reset_face, name='reset_face'),
    path('api/registered/', face.get_registered_faces, name='get_registered_faces'),
    path('api/camera/stop/', face.stop_camera, name='stop_camera'),
    path('api/status/', face.check_status, name='check_status'),
]
