from django.urls import path
from ..views import dashboard

urlpatterns = [
    path('', dashboard.index, name='index'),
    path('attendance-history/', dashboard.attendance_history, name='attendance_history'),
    path('teacher/dashboard/', dashboard.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/student/<int:student_id>/', dashboard.student_detail_view, name='student_detail'),
    path('teacher/today/', dashboard.today_attendance, name='today_attendance'),
]
