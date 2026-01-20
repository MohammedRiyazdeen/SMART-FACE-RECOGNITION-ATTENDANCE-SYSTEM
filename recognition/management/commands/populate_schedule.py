import random
from django.core.management.base import BaseCommand
from recognition.models import OrderSchedule, Student

class Command(BaseCommand):
    help = 'Populates the OrderSchedule model with initial mock data for all Departments'

    def handle(self, *args, **kwargs):
        # Base Subject Pools for Mock Generation
        subject_pools = {
            'BCS_CS': ['Data Communication and Network', 'C# Programming', 'Oracle', 'Operating System', 'IOT', 'Project', 'Oracle Practical', 'C# Practical'],
            'BCOM': ['Financial Accounting', 'Corporate Accounting', 'Business Law', 'Costing', 'Auditing', 'Income Tax', 'Economics', 'Business Statistics'],
            'BA_TAMIL': ['Ilakkaiyam', 'Ilakkanam', 'Ara Ilakkaiyam', 'Nannool', 'Purananooru', 'Tholkaappiyam', 'Tamil Varalaru'],
            'BA_ENGLISH': ['Modern English Grammar', 'British Literature', 'American Literature', 'Phonetics', 'Shakespeare', 'Literary Criticism', 'World Literature'],
            'BA_HISTORY': ['History of India', 'History of Tamil Nadu', 'World History', 'Indian Constitution', 'Archaeology', 'European History', 'Human Rights'],
            'BSC_PSY': ['General Psychology', 'Developmental Psychology', 'Abnormal Psychology', 'Social Psychology', 'Research Methodology', 'Counseling Psychology'],
            'BSC_PHY': ['Mechanics', 'Thermal Physics', 'Optics', 'Electromagnetism', 'Quantum Mechanics', 'Solid State Physics', 'Nuclear Physics'],
            'BSC_CHEM': ['Organic Chemistry', 'Inorganic Chemistry', 'Physical Chemistry', 'Analytical Chemistry', 'Polymer Chemistry', 'Biochemistry'],
            'BSC_MATHS': ['Calculus', 'Algebra', 'Real Analysis', 'Complex Analysis', 'Differential Equations', 'Mechanics', 'Discrete Mathematics'],
            'BSC_ZOO': ['Invertebrata', 'Chordata', 'Cell Biology', 'Genetics', 'Evolution', 'Ecology', 'Animal Physiology'],
            'BSC_MICRO': ['General Microbiology', 'Immunology', 'Microbial Genetics', 'Medical Microbiology', 'Industrial Microbiology', 'Virology']
        }

        # Clear existing data
        self.stdout.write('Clearing existing schedules...')
        OrderSchedule.objects.all().delete()

        orders = ['A', 'B', 'C', 'D', 'E', 'F']
        periods = ['1', '2', '3', '4', '5']

        # Get all mapped departments
        departments = [dept[0] for dept in Student.DEPT_CHOICES]

        schedules_to_create = []

        for dept in departments:
            # Get the pool for the department, or fallback
            pool = subject_pools.get(dept, [f'{dept} Subject 1', f'{dept} Subject 2', f'{dept} Subject 3', 'Project', 'Lab'])
            
            for order in orders:
                for period in periods:
                    subject = random.choice(pool)
                    schedules_to_create.append(
                        OrderSchedule(
                            day_order=order,
                            period=period,
                            department=dept,
                            subject=subject
                        )
                    )

        self.stdout.write('Writing dynamic schedules to database...')
        OrderSchedule.objects.bulk_create(schedules_to_create)

        self.stdout.write(self.style.SUCCESS(f'Successfully populated OrderSchedule with initial data for {len(departments)} departments.'))
