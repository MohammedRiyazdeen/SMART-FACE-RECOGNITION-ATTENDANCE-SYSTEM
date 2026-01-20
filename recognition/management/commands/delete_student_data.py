import os
import pickle
from django.core.management.base import BaseCommand
from recognition.models import Student, Attendance
from django.conf import settings

class Command(BaseCommand):
    help = 'Deletes a student\'s attendance records and face embeddings by their student ID'

    def add_arguments(self, parser):
        parser.add_argument('student_id', type=str, help='The Student ID (e.g., 23ACS21)')

    def handle(self, *args, **kwargs):
        student_id = kwargs['student_id']

        # 1. Delete Attendance Data and Student Object
        try:
            student = Student.objects.get(student_id=student_id)
            # Delete attendance explicitly (though cascading delete of Student does this)
            attendance_count, _ = Attendance.objects.filter(student=student).delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted {attendance_count} attendance records for {student_id}.'))
            
            # Optionally, we don't delete the student so they can register from scratch, 
            # but if you need to start purely from scratch, uncomment the next line:
            # student.delete()
            
        except Student.DoesNotExist:
            self.stdout.write(self.style.WARNING(f'Student with ID {student_id} not found in the database.'))

        # 2. Delete Face Data from face_data.pkl
        pkl_path = os.path.join(settings.BASE_DIR, 'face_data.pkl')
        if os.path.exists(pkl_path):
            try:
                with open(pkl_path, 'rb') as f:
                    face_data = pickle.load(f)
                
                # The user in face system might be registered as <student_id> or <student_name>
                # Let's check both or generic keys
                keys_to_delete = []
                for key in face_data.keys():
                    if student_id in key:
                        keys_to_delete.append(key)
                
                if keys_to_delete:
                    for k in keys_to_delete:
                        del face_data[k]
                    
                    with open(pkl_path, 'wb') as f:
                        pickle.dump(face_data, f)
                    
                    self.stdout.write(self.style.SUCCESS(f'Successfully deleted face pictures for {keys_to_delete} from face_data.pkl.'))
                else:
                    self.stdout.write(self.style.WARNING(f'No face pictures found for {student_id} in face_data.pkl.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error modifying face_data.pkl: {e}'))
        else:
            self.stdout.write(self.style.WARNING(f'face_data.pkl not found at {pkl_path}.'))
