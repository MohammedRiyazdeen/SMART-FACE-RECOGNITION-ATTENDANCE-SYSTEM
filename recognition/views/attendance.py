from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, time
from ..models import Student, Attendance, OrderSchedule, PeriodFinalization
from ..face_system import face_system
from ..services.email_service import send_absence_alert



def get_attendance_windows():
   
    return [
        ('1', 'First Period', time(8, 30), time(8, 40)),
        ('2', 'Second Period', time(9, 00), time(10, 00)),
        ('3', 'Third Period', time(10, 15), time(11, 15)),
        ('4', 'Fourth Period', time(11, 15), time(12, 15)),
        ('5', 'Fifth Period', time(12, 15), time(13, 15)),
    ]


def get_day_order():
    
    start_date = datetime(2026, 2, 15).date()
    current_date = datetime.now().date()
    delta = (current_date - start_date).days

    if delta < 0:
        return "-"  # Before start date

    cycle = ['A', 'B', 'C', 'D', 'E', 'F']
    index = delta % 6
    return cycle[index]


def is_attendance_open(period):

    now = datetime.now().time()

   
    windows_list = get_attendance_windows()

    
    windows_dict = {pid: (start, end) for pid, label, start, end in windows_list}

    if period not in windows_dict:
        return False, "Invalid Period"

    start, end = windows_dict[period]
    if start <= now <= end:
        return True, "Open"
    return False, f"Attendance Closed for Period {period} (Open {start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')})"


@login_required
def reset_attendance(request):
    if request.method == 'POST':
        # If teacher, pass student_id to reset specific student
        student_id = request.POST.get('student_id')
        if student_id and request.user.role == 'teacher':
             Attendance.objects.filter(student_id=student_id).delete()
             messages.success(request, "Student attendance reset successfully!")
             return redirect('student_detail', student_id=student_id)

        # If student, delete own
        Attendance.objects.filter(student=request.user).delete()
        messages.success(request, "Attendance history reset successfully!")
    return redirect('index')


def select_period(request):
    """Public period selection - no login required"""
    if request.method == 'POST':
        period = request.POST.get('period')

        # Check if attendance is open
        is_open, msg = is_attendance_open(period)
        if not is_open:
            messages.error(request, msg)
            return redirect('select_period')

        request.session['active_period'] = period
        return redirect('recognize')

    # 1. Get Schedule Data
    day_order = get_day_order()
    # Subjects wait until face recognition
    schedule_map = {}

    # 2. Get Time Slots (from centralized config)
    windows = get_attendance_windows()
    now = datetime.now().time()

    # 3. Determine Status: Active, Upcoming, or Done?
    active_period = None
    next_up_period = None
    all_done = False

    # Check if we are Inside a window
    for pid, label, start, end in windows:
        if start <= now <= end:
            # ACTIVE!
            active_period = {
                'id': pid,
                'label': label,
                'time': f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}",
                'subject': None,
                'title': f"Period {pid}"
            }
            break

    # If not active, find the NEXT one
    if not active_period:
        for pid, label, start, end in windows:
            if now < start:
                # This is the next one!
                next_up_period = {
                    'id': pid,
                    'label': label,
                    'start_time': start.strftime('%I:%M %p'),
                    'subject': None,
                    'title': f"Period {pid}"
                }
                break

        # If no next period found, and not active -> All done for today (or it's late)
        if not next_up_period:
            all_done = True

    return render(request, 'recognition/select_period.html', {
        'is_registered': True,
        'day_order': day_order,
        'active_period': active_period,
        'next_up_period': next_up_period,
        'all_done': all_done
    })


@csrf_exempt
def mark_attendance(request):
    """Public attendance marking - identifies student by face recognition"""
    if request.method == 'POST':
        period = request.session.get('active_period')
        if not period:
            return JsonResponse({'success': False, 'error': 'Session expired. Select period again.'})

        is_open, msg = is_attendance_open(period)
        if not is_open:
             return JsonResponse({'success': False, 'error': msg})

        # CRITICAL: Identify student from face recognition result
        current = face_system.get_current_recognition()
        if not current or current.get('name') == 'Unknown':
            return JsonResponse({
                'success': False,
                'error': 'Face not recognized. Please show your face to the camera.'
            })

        # Look up the student by rollno from face recognition
        recognized_rollno = current.get('name')  # face_system stores rollno as 'name'
        try:
            student = Student.objects.get(rollno=recognized_rollno)
        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Student not found in system.'})

        # Check duplicate
        today = datetime.now().date()
        if Attendance.objects.filter(student=student, date=today, period=period).exists():
             return JsonResponse({'success': False, 'already_marked': True, 'error': f'{student.name} is already marked Present for this period!'})

        attendance_record = Attendance.objects.create(student=student, period=period)
        subject_name = attendance_record.get_subject_name()
        return JsonResponse({'success': True, 'message': f'Attendance Marked for {student.name} ({subject_name})!'})

    return JsonResponse({'success': False, 'error': 'Invalid Method'})

@login_required
def finalize_period_attendance(request):
    """Teacher triggered endpoint to lock a period and send emails to absentees."""
    if request.user.role != 'teacher':
        messages.error(request, "Only teachers can finalize periods.")
        return redirect('index')
        
    if request.method == 'POST':
        period_id = request.POST.get('period_id')
        if not period_id:
            messages.error(request, "No period selected.")
            return redirect('teacher_dashboard')
            
        today = datetime.now().date()
        
        # 1. Double check it hasn't already been sent
        if PeriodFinalization.objects.filter(date=today, period=period_id).exists():
            messages.warning(request, f"Period {period_id} has already been finalized today!")
            return redirect('teacher_dashboard')
            
        # 2. Get the period label/subject 
        windows = get_attendance_windows()
        period_label = f"Period {period_id}"
        for pid, label, start_t, end_t in windows:
            if pid == period_id:
                period_label = label
                
        # Fetch subject dynamically per student based on their department
        pass
                
        # 3. Find missing students with emails
        students = Student.objects.filter(role='student').exclude(parent_email__isnull=True).exclude(parent_email__exact='')
        emails_sent = 0
        
        for student in students:
            attended = Attendance.objects.filter(student=student, date=today, period=period_id).exists()
            if not attended:
                # Find the specific subject for this student's department
                student_subject = period_label
                day_order = get_day_order()
                if day_order != "-":
                    try:
                        s_sched = OrderSchedule.objects.get(day_order=day_order, period=period_id, department=student.department)
                        student_subject = s_sched.subject
                    except OrderSchedule.DoesNotExist:
                        pass
                
                success = send_absence_alert(student, today, period_label, student_subject)
                if success:
                    emails_sent += 1
                    
        # 4. Mark as finalized in DB
        PeriodFinalization.objects.create(date=today, period=period_id)
        
        # Adding success message including automated note
        messages.success(request, f"Manual Override: Successfully finalized {period_label}. Sent {emails_sent} email alerts to parents of absent students.")
        
    return redirect('teacher_dashboard')
