from django.core.management.base import BaseCommand
from recognition.models import Student
import datetime

class Command(BaseCommand):
    help = "Bulk set a default DOB and update passwords for existing students who don't have a DOB set."

    def handle(self, *args, **kwargs):
        students = Student.objects.filter(role='student', dob__isnull=True)
        count = 0
        default_dob = datetime.date(2005, 1, 1)
        pwd_str = default_dob.strftime('%d/%m/%Y')
        
        for student in students:
            student.dob = default_dob
            student.set_password(pwd_str)
            student.save()
            count += 1
            
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} existing students with default DOB ({pwd_str}).'))
