from django.core.management.base import BaseCommand
from recognition.models import Student, Attendance, OrderSchedule
from recognition.services.email_service import send_absence_alert
from datetime import datetime

class Command(BaseCommand):
    help = 'Checks if any student missed a specific period today and sends an email.'

    def add_arguments(self, parser):
        parser.add_argument('period', type=str, help='The period number to check (e.g., "1", "2")')

    def handle(self, *args, **options):
        period_id = options['period']
        today = datetime.now().date()
        
        self.stdout.write(f"Checking for absences in Period {period_id} on {today}...")

        # Find all students who have a parent email
        students = Student.objects.filter(role='student').exclude(parent_email__isnull=True).exclude(parent_email__exact='')
        
        if not students.exists():
            self.stdout.write(self.style.WARNING("No students with listed parent_emails found."))
            return

        emails_sent = 0

        # Optional: Find out what subject this was supposed to be (for a nicer email)
        subject_name = f"Period {period_id}"
        
        # Calculate Day Order for today
        start_date = datetime(2026, 2, 15).date()
        delta = (today - start_date).days
        day_order = "-"
        if delta >= 0:
            cycle = ['A', 'B', 'C', 'D', 'E', 'F']
            day_order = cycle[delta % 6]

        for student in students:
            # Did they attend this period today?
            attended = Attendance.objects.filter(student=student, date=today, period=period_id).exists()
            
            if not attended:
                # They are absent! Send the alert.
                student_subject = subject_name
                if day_order != "-":
                    try:
                        schedule = OrderSchedule.objects.get(day_order=day_order, period=period_id, department=student.department)
                        student_subject = schedule.subject
                    except OrderSchedule.DoesNotExist:
                        pass
                        
                self.stdout.write(f"Student {student.name} missed Period {period_id}. Sending email...")
                success = send_absence_alert(student, today, f"Period {period_id}", student_subject)
                if success:
                    emails_sent += 1
                    
        self.stdout.write(self.style.SUCCESS(f"Finished. Sent {emails_sent} absence alerts."))
