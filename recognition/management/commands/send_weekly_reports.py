import json
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from recognition.models import Student, Attendance
from recognition.services.email_service import send_low_attendance_warning
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Sends weekly attendance summaries to parents and checks for low attendance warnings.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting weekly report generation...")
        
        # Calculate the past week's date range
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        # In Django, charfields are often empty strings instead of null. 
        # But when saving from model form with blank=True, null=True, it might be either.
        students = Student.objects.filter(role='student').exclude(parent_email__isnull=True).exclude(parent_email__exact='')
        
        if not students.exists():
            self.stdout.write(self.style.WARNING("No students with listed parent_emails found. Exiting."))
            return

        emails_sent = 0
        warnings_sent = 0

        for student in students:
            # 1. Weekly Stats Calculation
            weekly_records = Attendance.objects.filter(student=student, date__gte=week_ago, date__lte=today)
            weekly_present = weekly_records.count()
            
            # Assuming a standard 5 period day, 5 days a week = 25 periods
            # For a real system we'd calculate exactly how many classes *could* have been attended
            expected_weekly_periods = 25
            weekly_absent = expected_weekly_periods - weekly_present
            
            # 2. Overall Stats for Warning Check
            total_records = Attendance.objects.filter(student=student).count()
            
            # Calculate total possible periods since start date (Feb 15, 2026)
            start_date = datetime(2026, 2, 15).date()
            days_since_start = (today - start_date).days
            total_possible_periods = max(1, (days_since_start // 7 * 5) * 5) # rough estimate of total classes
            
            overall_percentage = min(100, int((total_records / total_possible_periods) * 100))
            
            # If attendance is critically low, send warning!
            if overall_percentage < 75:
                warning_sent = send_low_attendance_warning(student, overall_percentage, total_possible_periods - total_records)
                if warning_sent:
                    warnings_sent += 1
            
            # 3. Compile and Send Weekly Summary Email
            subject = f"Weekly Attendance Summary for {student.name}"
            
            message = f"""
Dear Parent/Guardian,

Here is the weekly attendance summary for {student.name} (Roll No: {student.rollno}) for the week of {week_ago.strftime('%b %d')} to {today.strftime('%b %d')}.

Classes Attended this week: {weekly_present}
Classes Missed this week: {max(0, weekly_absent)}

Overall Attendance Percentage: {overall_percentage}%

Please encourage consistent attendance to ensure academic success.

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
                emails_sent += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to send weekly summary to {student.parent_email}: {e}"))
                
        self.stdout.write(self.style.SUCCESS(f"Finished! Sent {emails_sent} weekly summaries and {warnings_sent} warnings."))
