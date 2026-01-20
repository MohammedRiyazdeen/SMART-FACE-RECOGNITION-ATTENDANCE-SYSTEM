from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime

def send_absence_alert(student, absent_date, period_name, subject_name):
    """
    Sends an immediate email alert to the parent when a student is marked absent for a specific period.
    """
    if not student.parent_email:
        return False # No email on file

    subject = f"Absence Alert: {student.name} missed a class today"
    
    message = f"""
Dear Parent/Guardian,

This is an automated notification from the College Attendance System.

Please be advised that {student.name} (Roll No: {student.rollno}) was marked ABSENT for the following class:

Date: {absent_date}
Period: {period_name}
Subject: {subject_name}

If you believe this is an error or need further information, please contact the department.

Best regards,
Automated Attendance System
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.parent_email],
            fail_silently=False,
        )
        print(f"✅ Absence email successfully dispatched to {student.parent_email} (Console Backend)")
        return True
    except Exception as e:
        print(f"❌ Failed to send absence email: {e}")
        return False

def send_low_attendance_warning(student, current_percentage, total_absences):
    """
    Sends a warning email if the student's overall attendance drops below the 75% threshold.
    """
    if not student.parent_email:
        return False

    subject = f"URGENT: Low Attendance Warning for {student.name}"
    
    message = f"""
Dear Parent/Guardian,

This is a formal warning from the College Attendance System. 

{student.name}'s overall attendance has dropped to {current_percentage}%, which is below the mandatory 75% requirement. They have accumulated a total of {total_absences} absences so far.

Falling below the 75% threshold may result in the student being barred from upcoming examinations. We advise you to discuss this matter with the student and ensure regular attendance moving forward.

Best regards,
College Administration
"""

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.parent_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"❌ Failed to send low attendance warning: {e}")
        return False
