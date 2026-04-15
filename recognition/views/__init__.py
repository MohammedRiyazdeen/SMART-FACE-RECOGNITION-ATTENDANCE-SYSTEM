# Views package - re-exports all views for backward compatibility
# This allows `from .views import index` to continue working.

from .auth import signup_view, login_view, logout_view, teacher_signup_view
from .dashboard import index, teacher_dashboard, student_detail_view, today_attendance
from .attendance import (
    get_attendance_windows,
    get_day_order,
    is_attendance_open,
    reset_attendance,
    select_period,
    mark_attendance,
)
from .face import (
    register,
    recognize,
    generate_frames_register,
    generate_frames_recognize,
    video_feed_register,
    video_feed_recognize,
    capture_face,
    stop_camera,
    check_status,
    get_registered_faces,
)
