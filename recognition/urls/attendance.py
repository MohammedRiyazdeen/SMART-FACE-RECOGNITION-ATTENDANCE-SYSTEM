from django.urls import path
from ..views import attendance

urlpatterns = [
    path('select_period/', attendance.select_period, name='select_period'),
    path('api/mark_attendance/', attendance.mark_attendance, name='mark_attendance'),
    path('reset-attendance/', attendance.reset_attendance, name='reset_attendance'),
    path('finalize-period/', attendance.finalize_period_attendance, name='finalize_period'),
]
