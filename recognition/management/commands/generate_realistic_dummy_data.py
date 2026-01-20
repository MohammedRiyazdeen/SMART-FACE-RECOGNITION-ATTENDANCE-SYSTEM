import random
from datetime import timedelta, date
from django.core.management.base import BaseCommand
from django.utils import timezone
from recognition.models import Student, Attendance, OrderSchedule

class Command(BaseCommand):
    help = 'Generates highly realistic and varied dummy attendance data'

    def handle(self, *args, **kwargs):
        # Temporarily disable auto_now_add so we can insert historical dates manually!
        Attendance._meta.get_field('date').auto_now_add = False
        Attendance._meta.get_field('time').auto_now_add = False

        self.stdout.write('Deleting old attendance records...')
        Attendance.objects.all().delete()

        students = Student.objects.filter(role='student')
        if not students.exists():
            self.stdout.write(self.style.ERROR('No students found.'))
            return

        # Fetch schedules to map day order to subjects
        schedules = OrderSchedule.objects.all()
        schedule_map = {(s.day_order, s.period): s.subject for s in schedules}
        
        cycle = ['A', 'B', 'C', 'D', 'E', 'F']

        end_date = timezone.now().date() - timedelta(days=1)
        start_date = end_date - timedelta(days=90)
        end_date = timezone.now().date() - timedelta(days=1)

        if end_date < start_date:
            end_date = timezone.now().date()

        current_date = start_date
        records_to_create = []

        self.stdout.write(f'Generating records from {start_date} to {end_date}...')

        while current_date <= end_date:
            # Skip Sundays
            if current_date.weekday() != 6:
                delta_days = (current_date - date(2026, 2, 15)).days
                if delta_days >= 0:
                    day_order = cycle[delta_days % 6]
                else:
                    # Randomly assign a day order for dates before the official cycle start
                    day_order = random.choice(cycle)

                for student in students:
                    # Determine this student's "day profile" via weighted probability
                    # 50% Perfect Attendance (All 5 periods)
                    # 10% Fully Absent (0 periods)
                    # 40% Partial Attendance (1 to 4 periods)
                    profile_roll = random.randint(1, 100)
                    
                    if profile_roll <= 50:
                        periods_present = [1, 2, 3, 4, 5]
                    elif profile_roll <= 60:
                        periods_present = []
                    else:
                        num_present = random.randint(1, 4)
                        periods_present = random.sample([1, 2, 3, 4, 5], num_present)

                    for period in range(1, 6):
                        status = 'Present' if period in periods_present else 'Absent'

                        # Just assigning an arbitrary valid time based on the period
                        period_time = timezone.now().replace(
                            hour=8 + period, minute=0, second=0, microsecond=0
                        ).time()
                        
                        records_to_create.append(
                            Attendance(
                                student=student,
                                date=current_date,
                                time=period_time,
                                status=status,
                                period=str(period)
                            )
                        )

            current_date += timedelta(days=1)

            # Batch create every 5000 to save memory footprint during massive loops
            if len(records_to_create) >= 5000:
                Attendance.objects.bulk_create(records_to_create, ignore_conflicts=True)
                self.stdout.write(f'Bulk created 5000 records up to {current_date}...')
                records_to_create = []

        # Create any remaining records
        if records_to_create:
            Attendance.objects.bulk_create(records_to_create, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(f'Successfully generated realistic data for {students.count()} students!'))
