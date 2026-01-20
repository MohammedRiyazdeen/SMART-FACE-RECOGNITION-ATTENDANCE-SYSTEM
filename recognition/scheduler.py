import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from .models import PeriodFinalization, OrderSchedule, Student, Attendance
from .views.attendance import get_attendance_windows, get_day_order
from .services.email_service import send_absence_alert

logger = logging.getLogger(__name__)

def auto_finalize_and_email():
    
    now = datetime.now()
    today = now.date()
    current_time = now.time()
    
    windows = get_attendance_windows()
    day_order = get_day_order()
    
    if day_order == "-":
        return # Not a valid academic day

    for period_id, label, start_t, end_t in windows:
       
        end_mins = end_t.hour * 60 + end_t.minute
        curr_mins = current_time.hour * 60 + current_time.minute
        
      
        if 0 <= (curr_mins - end_mins) <= 2:
            
           
            if not PeriodFinalization.objects.filter(date=today, period=period_id).exists():
                print(f"Auto-finalizing {label} ({period_id}) at {current_time}...")
                
                PeriodFinalization.objects.create(date=today, period=period_id)
                
                # Subject logic per student handled below
                pass
                
                # Find Absentees
                students = Student.objects.filter(role='student').exclude(parent_email__isnull=True).exclude(parent_email__exact='')
                emails_sent = 0
                
                for student in students:
                    attended = Attendance.objects.filter(student=student, date=today, period=period_id).exists()
                    if not attended:
                        student_subject = label
                        try:
                            schedule = OrderSchedule.objects.get(day_order=day_order, period=period_id, department=student.department)
                            student_subject = schedule.subject
                        except OrderSchedule.DoesNotExist:
                            pass
                            
                        success = send_absence_alert(student, today, label, student_subject)
                        if success:
                            emails_sent += 1
                            
                print(f"Auto-finalization complete for {label}. Sent {emails_sent} absentee emails.")


def start_scheduler():
    """Initialize and start the background scheduler."""
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE if hasattr(settings, 'TIME_ZONE') else "UTC")
    
    # Run every 1 minute
    scheduler.add_job(auto_finalize_and_email, 'interval', minutes=1, id='auto_email_job', replace_existing=True)
    
    scheduler.start()
    print("APScheduler started: Monitoring period end times for automated emails.")
