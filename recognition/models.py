from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager

class StudentManager(BaseUserManager):
    def create_user(self, rollno, password=None, **extra_fields):
        if not rollno:
            raise ValueError('The Roll Number is required')
        extra_fields.setdefault('username', rollno)
        user = self.model(rollno=rollno, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, rollno, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(rollno, password, **extra_fields)

class Student(AbstractUser):
    rollno = models.CharField(max_length=20, unique=True, verbose_name="Roll Number")
    name = models.CharField(max_length=100, verbose_name="Full Name")
    
    DEPT_CHOICES = [
        ('BCS_CS', 'BSc Computer Science'),
        ('BCOM', 'B.Com'),
        ('BA_TAMIL', 'BA Tamil'),
        ('BA_ENGLISH', 'BA English'),
        ('BA_HISTORY', 'BA History'),
        ('BSC_PSY', 'BSc Psychology'),
        ('BSC_PHY', 'BSc Physics'),
        ('BSC_CHEM', 'BSc Chemistry'),
        ('BSC_MATHS', 'BSc Maths'),
        ('BSC_ZOO', 'BSc Zology'),
        ('BSC_MICRO', 'BSc Micro Biology'),
    ]
    
    YEAR_CHOICES = [
        ('I', 'I YEAR'),
        ('II', 'II YEAR'),
        ('III', 'III YEAR'),
    ]
    
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    ]

    department = models.CharField(max_length=20, choices=DEPT_CHOICES, blank=True, null=True, verbose_name="Department")
    year = models.CharField(max_length=5, choices=YEAR_CHOICES, blank=True, null=True, verbose_name="Year")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    
    parent_email = models.EmailField(verbose_name="Parent's Email", blank=True, null=True)
    dob = models.DateField(verbose_name="Date of Birth", blank=True, null=True)

    USERNAME_FIELD = 'rollno'
    REQUIRED_FIELDS = ['name']
    
    objects = StudentManager()
    
    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.rollno
        super().save(*args, **kwargs)

    def get_recent_attendance_stats(self, days=90):
        from .utils import calculate_recent_attendance_stats
        records = Attendance.objects.filter(student=self).order_by('date')
        return calculate_recent_attendance_stats(records, days=days)

    def get_attendance_percentage(self, days=90):
        stats = self.get_recent_attendance_stats(days=days)
        return stats[3] if stats else 0

    def __str__(self):
        return f"{self.name} ({self.rollno})"

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    time = models.TimeField(auto_now_add=True)
    PERIOD_CHOICES = [
        ('1', 'First Period'),
        ('2', 'Second Period'),
        ('3', 'Third Period'),
        ('4', 'Fourth Period'),
        ('5', 'Fifth Period'),
    ]
    period = models.CharField(max_length=1, choices=PERIOD_CHOICES)
    status = models.CharField(max_length=10, default='Present')

    class Meta:
        unique_together = ('student', 'date', 'period')
    
    def __str__(self):
        return f"{self.student.name} - {self.get_period_display()} - {self.date}"

    def get_subject_name(self):
        from datetime import datetime
        start_date = datetime(2026, 2, 15).date()
        current_date = self.date
        delta = (current_date - start_date).days
        
        if delta < 0:
            return self.get_period_display()
            
        cycle = ['A', 'B', 'C', 'D', 'E', 'F']
        index = delta % 6
        day_order = cycle[index]
        
        try:
            schedule = OrderSchedule.objects.get(day_order=day_order, period=self.period, department=self.student.department)
            return schedule.subject
        except OrderSchedule.DoesNotExist:
            return self.get_period_display()

class OrderSchedule(models.Model):
    """
    Stores the class schedule for each Day Order (A-F)
    """
    ORDER_CHOICES = [
        ('A', 'Order A'),
        ('B', 'Order B'),
        ('C', 'Order C'),
        ('D', 'Order D'),
        ('E', 'Order E'),
        ('F', 'Order F'),
    ]
    
    PERIOD_CHOICES = [
        ('1', 'First Period'),
        ('2', 'Second Period'),
        ('3', 'Third Period'),
        ('4', 'Fourth Period'),
        ('5', 'Fifth Period'),
    ]
    
    day_order = models.CharField(max_length=1, choices=ORDER_CHOICES)
    period = models.CharField(max_length=1, choices=PERIOD_CHOICES)
    department = models.CharField(max_length=20, choices=Student.DEPT_CHOICES, default='BCS_CS')
    subject = models.CharField(max_length=100)

    class Meta:
        unique_together = ('day_order', 'period', 'department')
        
    def __str__(self):
        return f"{self.get_day_order_display()} - {self.get_period_display()} - {self.subject}"

class PeriodFinalization(models.Model):
    """
    Tracks when a teacher has officially clicked 'Finalize Attendance & Notify Parents'
    for a specific period on a specific day.
    """
    date = models.DateField(auto_now_add=True)
    period = models.CharField(max_length=10)
    finalized_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('date', 'period')
        
    def __str__(self):
        return f"Finalized Period {self.period} on {self.date}"
