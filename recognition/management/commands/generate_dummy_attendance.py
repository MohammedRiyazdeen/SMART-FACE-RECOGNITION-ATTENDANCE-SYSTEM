from django.core.management.base import BaseCommand
from recognition.models import Student, Attendance
from datetime import datetime, timedelta, time
import random

class Command(BaseCommand):
    help = 'Wipes existing attendance and generates realistic dummy data from Dec 3, 2025 to today'

    def handle(self, *args, **kwargs):
        # 1. Wipe existing data
        self.stdout.write("Deleting ALL old attendance records...")
        Attendance.objects.all().delete()

        # 2. IMPORTANT FIX: Temporarily disable auto_now_add on the model level
        # so Django bulk_create respects our explicit past dates instead of forcing "today"
        date_field = Attendance._meta.get_field('date')
        time_field = Attendance._meta.get_field('time')
        
        original_date_auto = date_field.auto_now_add
        original_time_auto = time_field.auto_now_add
        
        date_field.auto_now_add = False
        time_field.auto_now_add = False

        try:
            # 3. Setup dates
            start_date = datetime(2025, 12, 3).date()
            today = datetime(2026, 4, 15).date()  # Generate up to today only

            students = list(Student.objects.filter(role='student').order_by('rollno'))
            if not students:
                self.stdout.write(self.style.ERROR("No students found."))
                return

            self.stdout.write(f"Found {len(students)} students:")
            
            # Target percentages using rollno indices
            student_profiles = {}
            profile_configs = [
                {'label': '~95%', 'full_absent': 0.02, 'partial_2': 0.02, 'partial_3': 0.01, 'single': 0.02},   # ~93% present days
                {'label': '~88%', 'full_absent': 0.05, 'partial_2': 0.04, 'partial_3': 0.02, 'single': 0.03},   # ~86%
                {'label': '~80%', 'full_absent': 0.10, 'partial_2': 0.05, 'partial_3': 0.03, 'single': 0.04},   # ~78%
                {'label': '~92%', 'full_absent': 0.03, 'partial_2': 0.03, 'partial_3': 0.01, 'single': 0.02},   # ~91%
                {'label': '~70%', 'full_absent': 0.32, 'partial_2': 0.06, 'partial_3': 0.04, 'single': 0.03},   # ~68% DEFAULTER
                {'label': '~65%', 'full_absent': 0.38, 'partial_2': 0.06, 'partial_3': 0.04, 'single': 0.03},   # ~62% DEFAULTER
                {'label': '~73%', 'full_absent': 0.28, 'partial_2': 0.06, 'partial_3': 0.04, 'single': 0.03},   # ~72% DEFAULTER
            ]

            for i, student in enumerate(students):
                profile = profile_configs[i % len(profile_configs)]
                student_profiles[student.id] = profile
                self.stdout.write(f"  {student.rollno} -> target {profile['label']}")

            # 4. Build working days list (skip Sundays, skip ~40% of Saturdays)
            random.seed(42)  # Seed for reproducibility
            working_days = []
            current_date = start_date
            while current_date <= today:
                if current_date.weekday() == 6:  # Sunday - always skip
                    current_date += timedelta(days=1)
                    continue
                if current_date.weekday() == 5:  # Saturday - 60% chance working
                    if random.random() > 0.60:
                        current_date += timedelta(days=1)
                        continue
                working_days.append(current_date)
                current_date += timedelta(days=1)

            self.stdout.write(f"Total working days: {len(working_days)} (Dec 3 to Apr 15)")

            # 5. Generate attendance per student per day
            random.seed(None)  # Back to true random for attendance patterns
            attendance_records = []
            student_stats = {s.id: {'present_days': 0, 'absent_days': 0, 'partial_days': 0} for s in students}

            for cd in working_days:
                for student in students:
                    profile = student_profiles[student.id]

                    r = random.random()
                    cumulative = 0

                    cumulative += profile['full_absent']
                    if r < cumulative:
                        statuses = ['Absent'] * 5
                        student_stats[student.id]['absent_days'] += 1
                    else:
                        cumulative += profile['partial_2']
                        if r < cumulative:
                            pattern = random.choice([
                                ['Absent', 'Absent', 'Present', 'Present', 'Present'],
                                ['Present', 'Present', 'Present', 'Absent', 'Absent'],
                                ['Present', 'Absent', 'Absent', 'Present', 'Present'],
                                ['Present', 'Present', 'Absent', 'Absent', 'Present'],
                            ])
                            statuses = pattern
                            student_stats[student.id]['partial_days'] += 1
                        else:
                            cumulative += profile['partial_3']
                            if r < cumulative:
                                pattern = random.choice([
                                    ['Absent', 'Absent', 'Absent', 'Present', 'Present'],
                                    ['Present', 'Present', 'Absent', 'Absent', 'Absent'],
                                    ['Absent', 'Present', 'Absent', 'Absent', 'Present'],
                                    ['Present', 'Absent', 'Absent', 'Absent', 'Present'],
                                ])
                                statuses = pattern
                                student_stats[student.id]['partial_days'] += 1
                            else:
                                cumulative += profile['single']
                                if r < cumulative:
                                    statuses = ['Present'] * 5
                                    miss_idx = random.randint(0, 4)
                                    statuses[miss_idx] = 'Absent'
                                    student_stats[student.id]['partial_days'] += 1
                                else:
                                    statuses = ['Present'] * 5
                                    student_stats[student.id]['present_days'] += 1

                    base_time = datetime.combine(cd, time(9, 0))
                    for i in range(1, 6):
                        period_time = (base_time + timedelta(hours=i - 1)).time()
                        obj = Attendance(
                            student=student,
                            period=str(i),
                            status=statuses[i - 1],
                        )
                        # Explicitly set the past dates
                        obj.date = cd
                        obj.time = period_time
                        attendance_records.append(obj)

            # 6. Insert
            self.stdout.write(f"\nGenerated {len(attendance_records)} records. Saving to database...")
            Attendance.objects.bulk_create(attendance_records, batch_size=1000)

            # 7. Print summary
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("ATTENDANCE SUMMARY")
            self.stdout.write("=" * 60)
            total_days = len(working_days)
            for student in students:
                stats = student_stats[student.id]
                present = stats['present_days'] + stats['partial_days'] 
                pct = round((present / total_days) * 100, 1) if total_days > 0 else 0
                self.stdout.write(
                    f"  {student.rollno:10s} {student.name:20s} | "
                    f"Full: {stats['present_days']:3d}  Partial: {stats['partial_days']:3d}  "
                    f"Absent: {stats['absent_days']:3d}  | "
                    f"{'! DEFAULTER' if pct < 75 else 'OK':>14s} {pct:5.1f}%"
                )
            self.stdout.write("=" * 60)
            self.stdout.write(self.style.SUCCESS(f"\nDone! {len(attendance_records)} records from {start_date} to {today}"))

        finally:
            # Revert the auto_now_add setting so the app works normally
            date_field.auto_now_add = original_date_auto
            time_field.auto_now_add = original_time_auto
