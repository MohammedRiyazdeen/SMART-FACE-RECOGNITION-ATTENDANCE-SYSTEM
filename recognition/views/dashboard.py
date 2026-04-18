from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import datetime
import json
from collections import defaultdict
from ..models import Student, Attendance, OrderSchedule, PeriodFinalization
from .attendance import get_day_order, get_attendance_windows

def get_student_analytics(student):
    """Helper to calculate analytics for a specific student"""
    records = Attendance.objects.filter(student=student).order_by('date')
    # Day-based analytics over the last 90 days
    total_days, present_days, absent_days, percentage, daily_attendance = student.get_recent_attendance_stats(days=90)
    
    if total_days == 0:
        return {
            'total': 0, 'present': 0, 'absent': 0, 'percentage': 0, 'is_warning': False,
            'chart_data': json.dumps({'heatmap': [], 'pie': {'labels': ['Present', 'Absent'], 'data': [0, 0]}, 'subject': {'labels': [], 'data': []}})
        }
        
    # Pre-fetch schedule to avoid N+1 queries
    schedules = OrderSchedule.objects.filter(department=student.department)
    schedule_map = {(s.day_order, s.period): s.subject for s in schedules}
    
    # Setup for stats
    start_date = datetime(2026, 2, 15).date()
    cycle = ['A', 'B', 'C', 'D', 'E', 'F']
    
    def shorten_subject(subj_name):
        s = subj_name.upper().strip()
        if 'DATA COMMUNICATION' in s or 'DATA COMMUCATION' in s or 'NETWORKING' in s: return 'DCN', 'Data Communication & Networking'
        if 'ORACLE PRACTICAL' in s or ('ORACLE' in s and 'PRAC' in s): return 'ORC PRAC', 'Oracle Practical'
        if 'ORACLE' in s: return 'ORC', 'Oracle'
        if 'C#' in s and 'PRAC' in s: return 'C# PRAC', 'C# Practical'
        if 'C#' in s: return 'C#', 'C# Programming'
        if 'INTERNET OF THINGS' in s or 'IOT' in s: return 'IOT', 'Internet of Things'
        if 'PROJECT' in s: return 'PROJ', 'Project'
        if 'OPERATING SYSTEM' in s or 'OS' == s: return 'OS', 'Operating System'
        return subj_name, subj_name

    daily_stats = defaultdict(int)
    subject_stats = defaultdict(lambda: {'total': 0, 'present': 0, 'full_name': ''})
    subject_avoidance = {}
    
    for r in records:
        # Daily Heatmap count (max 5 periods usually)
        date_str = r.date.strftime('%Y-%m-%d')
        if r.status == 'Present':
            daily_stats[date_str] += 1
        elif date_str not in daily_stats:
            daily_stats[date_str] = 0 # Ensure days with all absences show as 0, not empty
            
        # Subject stats - calculate subject dynamically but efficiently
        delta = (r.date - start_date).days
        day_order = cycle[delta % 6]
        subject = schedule_map.get((day_order, r.period), f"Period {r.period}")
            
        short_subj, full_subj = shorten_subject(subject)
        
        # Avoidance metric: Exclude Practicals & Projects
        if short_subj not in ['C# PRAC', 'PROJ', 'ORC PRAC']:
            if short_subj not in subject_avoidance:
                subject_avoidance[short_subj] = 0
            if r.status == 'Absent':
                subject_avoidance[short_subj] += 1
                
        subject_stats[short_subj]['total'] += 1
        if r.status == 'Present':
            subject_stats[short_subj]['present'] += 1
        subject_stats[short_subj]['full_name'] = full_subj
            
    # Format for Chart.js and Heatmap
    heatmap_data = [{'date': k, 'count': v} for k, v in daily_stats.items()]
    
    # Sort subjects by name
    sorted_subjects = sorted(subject_stats.keys())
    subject_labels = sorted_subjects
    subject_percentages = [round((subject_stats[s]['present'] / subject_stats[s]['total']) * 100, 1) for s in sorted_subjects]
    
    # Subject Avoidance processing
    avoidance_labels = sorted(subject_avoidance.keys())
    avoidance_data = [subject_avoidance[s] for s in avoidance_labels]
    
    # Generate Legend mapping to pass to template
    subject_legend = {s: subject_stats[s]['full_name'] for s in sorted_subjects if s != subject_stats[s]['full_name']}
    
    return {
        'total': total_days,
        'present': present_days,
        'absent': absent_days,
        'percentage': percentage,
        'is_warning': percentage < 75,
        'subject_legend': subject_legend,
        'chart_data': json.dumps({
            'heatmap': heatmap_data,
            'pie': {'labels': ['Present Days', 'Absent Days'], 'data': [present_days, absent_days]},
            'subject': {'labels': subject_labels, 'data': subject_percentages},
            'subject_avoidance': {
                'labels': avoidance_labels,
                'data': avoidance_data
            }
        })
    }


@login_required
def index(request):
    """Home page - Student dashboard with profile card"""
    if request.user.role == 'teacher':
        return redirect('teacher_dashboard')
    elif request.user.role == 'admin':
        return redirect('/admin/')

    day_order = get_day_order()
    return render(request, 'recognition/index.html', {
        'student': request.user,
        'day_order': day_order,
        'analytics': get_student_analytics(request.user),
    })


@login_required
def attendance_history(request):
    """Attendance history page with filters"""
    if request.user.role == 'teacher':
        return redirect('teacher_dashboard')
    elif request.user.role == 'admin':
        return redirect('/admin/')

    # Start with all records for this student
    qs = Attendance.objects.filter(student=request.user).order_by('-date', '-time')

    # Get filter parameters
    filter_date = request.GET.get('date', '').strip()
    filter_status = request.GET.get('status', '').strip()
    filter_period = request.GET.get('period', '').strip()
    filter_subject = request.GET.get('subject', '').strip()

    # Apply database-level filters
    if filter_date:
        qs = qs.filter(date=filter_date)
    if filter_status:
        qs = qs.filter(status=filter_status)
    if filter_period:
        qs = qs.filter(period=filter_period)

    # If no explicitly chosen filters are active, default to showing only the most recent date 
    # that has records, rather than the entire history.
    no_filters = not (filter_date or filter_status or filter_period or filter_subject)
    if no_filters and qs.exists():
        latest_date = qs.first().date
        qs = qs.filter(date=latest_date)

    # Evaluate the QuerySet and apply Python-level filters for dynamic fields
    history = []
    # Get all subjects from the schedule so students can search for any subject
    available_subjects = list(OrderSchedule.objects.filter(department=request.user.department).values_list('subject', flat=True).distinct().order_by('subject'))
    
    for record in qs:
        rec_subject = record.get_subject_name()
        record.display_subject = rec_subject

        # Apply Subject filter (Exact match)
        if filter_subject and filter_subject != rec_subject:
            continue

        history.append(record)

    # Get all distinct dates this student has attendance records for
    raw_dates = Attendance.objects.filter(student=request.user).values_list('date', flat=True).distinct().order_by('-date')
    available_dates = [{'value': d.strftime('%Y-%m-%d'), 'label': d.strftime('%A, %b %d, %Y')} for d in raw_dates]

    # Predefine the exact periods
    available_periods = [
        {'value': '1', 'label': 'First Period'},
        {'value': '2', 'label': 'Second Period'},
        {'value': '3', 'label': 'Third Period'},
        {'value': '4', 'label': 'Fourth Period'},
        {'value': '5', 'label': 'Fifth Period'},
    ]

    day_order = get_day_order()
    return render(request, 'recognition/attendance_history.html', {
        'student': request.user,
        'history': history,
        'day_order': day_order,
        'available_subjects': available_subjects,
        'available_dates': available_dates,
        'available_periods': available_periods,
        'filter_date': filter_date,
        'filter_status': filter_status,
        'filter_period': filter_period,
        'filter_subject': filter_subject,
        'is_filtered': bool(filter_date or filter_status or filter_period or filter_subject),
    })


@login_required
def teacher_dashboard(request):
    if request.user.role != 'teacher':
        messages.warning(request, "Access denied. Teachers only.")
        return redirect('index')

    # Get all students
    students = Student.objects.filter(role='student').order_by('rollno')
    
    # Calculate Class-Level Analytics
    total_classes_all = 0
    present_classes_all = 0
    
    # Defaulters (< 75%)
    defaulters = []
    
    # Class Comparison (by Year/Dept)
    class_stats = defaultdict(lambda: {'total': 0, 'present': 0})
    
    today = datetime.now().date()
    
    for student in students:
        records = Attendance.objects.filter(student=student)
        
        # Use DAY-BASED calculation
        total_days, _, _, percentage, _ = student.get_recent_attendance_stats(days=90)
        
        if total_days > 0:
            # For class-level analytics, still use period counts
            total_periods = records.count()
            present_periods = records.filter(status='Present').count()
            total_classes_all += total_periods
            present_classes_all += present_periods
            
            group_key = f"{student.year} {student.get_department_display()}"
            class_stats[group_key]['total'] += total_periods
            class_stats[group_key]['present'] += present_periods
            
            if percentage < 75:
                defaulters.append({
                    'student': student,
                    'percentage': percentage,
                    'short_dept': f"{student.year}-{student.department}"
                })
            
            student.attendance_percentage = percentage
        else:
            student.attendance_percentage = None

    defaulters.sort(key=lambda x: x['percentage'])
    
    overall_percentage = 0
    absent_classes_all = total_classes_all - present_classes_all
    if total_classes_all > 0:
        overall_percentage = round((present_classes_all / total_classes_all) * 100, 1)
    
    from datetime import timedelta
    from .attendance import get_attendance_windows
    
    total_students = students.count()
    
    today_records = Attendance.objects.filter(date=today)
    today_students_present = today_records.filter(status='Present').values('student').distinct().count()
    today_students_absent_count = total_students - today_students_present
    today_has_data = today_records.exists()
    today_percentage = round((today_students_present / total_students) * 100, 1) if total_students > 0 and today_has_data else 0
    
    week_start = today - timedelta(days=today.weekday())  # Monday
    last_week_start = week_start - timedelta(days=7)
    last_week_end = week_start - timedelta(days=1)
    
    # This week: unique (student, date) pairs with at least 1 Present
    this_week_records = Attendance.objects.filter(date__gte=week_start, date__lte=today)
    this_week_days = this_week_records.values('date').distinct().count()
    this_week_present_student_days = 0
    this_week_total_student_days = 0
    if this_week_days > 0:
        for d in this_week_records.values('date').distinct():
            day_date = d['date']
            day_students = this_week_records.filter(date=day_date).values('student').distinct().count()
            day_present = this_week_records.filter(date=day_date, status='Present').values('student').distinct().count()
            this_week_total_student_days += day_students
            this_week_present_student_days += day_present
    this_week_pct = round((this_week_present_student_days / this_week_total_student_days) * 100, 1) if this_week_total_student_days > 0 else 0
    
    last_week_records = Attendance.objects.filter(date__gte=last_week_start, date__lte=last_week_end)
    last_week_present_student_days = 0
    last_week_total_student_days = 0
    for d in last_week_records.values('date').distinct():
        day_date = d['date']
        day_students = last_week_records.filter(date=day_date).values('student').distinct().count()
        day_present = last_week_records.filter(date=day_date, status='Present').values('student').distinct().count()
        last_week_total_student_days += day_students
        last_week_present_student_days += day_present
    last_week_pct = round((last_week_present_student_days / last_week_total_student_days) * 100, 1) if last_week_total_student_days > 0 else 0
    
    week_change = round(this_week_pct - last_week_pct, 1)
    week_direction = 'up' if week_change > 0 else ('down' if week_change < 0 else 'same')
    
    windows = get_attendance_windows()
    period_breakdown = []
    for pid, label, start_t, end_t in windows:
        period_records = today_records.filter(period=pid)
        p_total = period_records.values('student').distinct().count()
        p_present = period_records.filter(status='Present').values('student').distinct().count()
        p_pct = round((p_present / p_total) * 100, 1) if p_total > 0 else 0
        period_breakdown.append({
            'id': pid,
            'label': label,
            'total': p_total,
            'present': p_present,
            'absent': p_total - p_present,
            'percentage': p_pct,
            'has_data': p_total > 0,
        })
    
    two_weeks_ago = today - timedelta(days=14)
    four_weeks_ago = today - timedelta(days=28)
    declining_students = []
    for student in students:
        recent_daily = defaultdict(list)
        older_daily = defaultdict(list)
        s_records = Attendance.objects.filter(student=student)
        for r in s_records:
            if two_weeks_ago <= r.date <= today:
                recent_daily[r.date].append(r.status)
            elif four_weeks_ago <= r.date < two_weeks_ago:
                older_daily[r.date].append(r.status)
        
        recent_days = len(recent_daily)
        older_days = len(older_daily)
        if recent_days >= 3 and older_days >= 3:
            recent_present = sum(1 for statuses in recent_daily.values() if 'Present' in statuses)
            older_present = sum(1 for statuses in older_daily.values() if 'Present' in statuses)
            recent_pct = round((recent_present / recent_days) * 100, 1)
            older_pct = round((older_present / older_days) * 100, 1)
            drop = older_pct - recent_pct
            if drop >= 10:  # 10%+ drop
                declining_students.append({
                    'student': student,
                    'recent_pct': recent_pct,
                    'older_pct': older_pct,
                    'drop': round(drop, 1),
                })
    declining_students.sort(key=lambda x: -x['drop'])
    
    class_analytics = {
        'total': total_classes_all,
        'present': present_classes_all,
        'absent': absent_classes_all,
        'percentage': overall_percentage,
        'defaulters': defaulters,
        'has_data': total_classes_all > 0,
        # Today's Snapshot
        'today_present': today_students_present,
        'today_absent': today_students_absent_count,
        'today_percentage': today_percentage,
        'today_has_data': today_has_data,
        'total_students': total_students,
        # Weekly Trend
        'this_week_pct': this_week_pct,
        'last_week_pct': last_week_pct,
        'week_change': abs(week_change),
        'week_direction': week_direction,
        # Period Breakdown
        'period_breakdown': period_breakdown,
        # Alerts
        'declining_students': declining_students[:5],  # top 5
        'defaulter_count': len(defaulters),
    }

    
    # Calculate Unfinalized Periods for the Manual Trigger Panel
    unfinalized_periods = []
    now = datetime.now()
    current_date = now.date()
    current_time = now.time()
    
    windows = get_attendance_windows()
    for pid, label, start_t, end_t in windows:
        if current_time >= end_t:
            # Period has ended. Check if it's already finalized.
            if not PeriodFinalization.objects.filter(date=current_date, period=pid).exists():
                unfinalized_periods.append({
                    'id': pid,
                    'label': label
                })

    day_order = get_day_order()
    return render(request, 'recognition/teacher_dashboard.html', {
        'students': students,
        'user': request.user,
        'day_order': day_order,
        'class_analytics': class_analytics,
        'unfinalized_periods': unfinalized_periods
    })

@login_required
def student_detail_view(request, student_id):
    if request.user.role != 'teacher':
        messages.warning(request, "Access denied. Teachers only.")
        return redirect('index')

    student = get_object_or_404(Student, id=student_id)
    
    # Base queryset
    attendance_qs = Attendance.objects.filter(student=student).order_by('-date', '-time')
    
    # Read filter params
    quick_filter = request.GET.get('filter', 'today')  # today, week, month, custom
    filter_date = request.GET.get('date', '')
    filter_subject = request.GET.get('subject', '')
    filter_status = request.GET.get('status', '')
    
    from datetime import timedelta
    today = datetime.now().date()
    
    showing_date = None
    is_fallback_date = False
    
    # Apply quick filter
    if filter_date:
        # Specific date from date picker
        quick_filter = 'custom'
        try:
            picked = datetime.strptime(filter_date, '%Y-%m-%d').date()
            attendance_qs = attendance_qs.filter(date=picked)
            showing_date = picked
        except ValueError:
            pass
    elif quick_filter == 'week':
        week_start = today - timedelta(days=today.weekday())  # Monday
        attendance_qs = attendance_qs.filter(date__gte=week_start, date__lte=today)
    elif quick_filter == 'month':
        attendance_qs = attendance_qs.filter(date__year=today.year, date__month=today.month)
    else:
        # Default: show TODAY's records strictly (do not fall back to latest date)
        quick_filter = 'today'
        attendance_qs = attendance_qs.filter(date=today)
        showing_date = today
        is_fallback_date = False
    
    # Apply subject filter
    if filter_subject:
        # Since subject is derived dynamically from OrderSchedule, filter in Python after query
        pass
    
    # Apply status filter  
    if filter_status:
        attendance_qs = attendance_qs.filter(status__iexact=filter_status)
    
    attendance_records = list(attendance_qs)
    
    # If subject filter is set, filter in Python since subject is dynamic
    if filter_subject:
        attendance_records = [r for r in attendance_records if r.get_subject_name().lower() == filter_subject.lower()]
    
    # Get distinct subjects for the dropdown (OrderSchedule is already imported at top)
    all_subjects = list(OrderSchedule.objects.filter(department=student.department).values_list('subject', flat=True).distinct().order_by('subject'))
    
    day_order = get_day_order()

    return render(request, 'recognition/student_detail.html', {
        'student': student,
        'attendance_records': attendance_records,
        'day_order': day_order,
        'analytics': get_student_analytics(student),
        'all_subjects': all_subjects,
        'active_filter': quick_filter,
        'filter_date': filter_date,
        'filter_subject': filter_subject,
        'filter_status': filter_status,
        'showing_date': showing_date,
        'is_fallback_date': is_fallback_date,
    })


@login_required
def today_attendance(request):
    """Teacher-only page: grid of all students × 5 periods for today."""
    if request.user.role != 'teacher':
        messages.warning(request, "Access denied. Teachers only.")
        return redirect('index')

    today = datetime.now().date()
    day_order = get_day_order()
    windows = get_attendance_windows()
    now = datetime.now().time()

    # Build period info with subject names
    # Since subjects can vary by department, we'll use a representative department
    # for headers, but show per-student subjects in tooltips
    period_info = []
    cycle = ['A', 'B', 'C', 'D', 'E', 'F']
    start_date = datetime(2026, 2, 15).date()
    delta = (today - start_date).days

    for pid, label, start_t, end_t in windows:
        # Check if period has ended, is active, or is upcoming
        if now >= end_t:
            time_status = 'ended'
        elif start_t <= now <= end_t:
            time_status = 'active'
        else:
            time_status = 'upcoming'

        period_info.append({
            'id': pid,
            'label': label,
            'time': f"{start_t.strftime('%I:%M %p')} - {end_t.strftime('%I:%M %p')}",
            'time_status': time_status,
        })

    # Get selected department filter if any
    selected_dept = request.GET.get('dept', '')

    # Get all students
    all_students = Student.objects.filter(role='student')
    if selected_dept:
        all_students = all_students.filter(department=selected_dept)
    all_students = all_students.order_by('rollno')

    # Pre-fetch subject names per department for today's day order
    dept_subjects = {}  # {dept: {period: subject_name}}
    if delta >= 0:
        current_day_order = cycle[delta % 6]
        schedules = OrderSchedule.objects.filter(day_order=current_day_order)
        for s in schedules:
            if s.department not in dept_subjects:
                dept_subjects[s.department] = {}
            dept_subjects[s.department][s.period] = s.subject
    
    # Shorten subject names for column headers
    def shorten(subj):
        s = subj.upper().strip()
        if 'DATA COMMUNICATION' in s or 'DATA COMMUCATION' in s or 'NETWORKING' in s: return 'DCN'
        if 'ORACLE PRACTICAL' in s or ('ORACLE' in s and 'PRAC' in s): return 'ORC PRAC'
        if 'ORACLE' in s: return 'ORC'
        if 'C#' in s and 'PRAC' in s: return 'C# PRAC'
        if 'C#' in s: return 'C#'
        if 'INTERNET OF THINGS' in s or 'IOT' in s: return 'IOT'
        if 'PROJECT' in s: return 'PROJ'
        if 'OPERATING SYSTEM' in s or 'OS' == s: return 'OS'
        return subj[:8]  # Fallback: first 8 chars

    # Get today's attendance records (batch query)
    today_records = Attendance.objects.filter(date=today, student__in=all_students).select_related('student')
    attendance_map = {}  # {student_id: {period: status}}
    for rec in today_records:
        if rec.student_id not in attendance_map:
            attendance_map[rec.student_id] = {}
        attendance_map[rec.student_id][rec.period] = rec.status

    # Group students by department
    from collections import OrderedDict
    dept_students = OrderedDict()
    for student in all_students:
        dept_key = student.department or 'UNKNOWN'
        if dept_key not in dept_students:
            dept_students[dept_key] = []
        dept_students[dept_key].append(student)

    # Build a dept_name lookup from DEPT_CHOICES
    dept_name_map = dict(Student.DEPT_CHOICES)

    # Build per-department table data
    dept_tables = []
    total_present_count = 0
    total_absent_count = 0
    total_pending_count = 0

    for dept_code, students_in_dept in dept_students.items():
        dept_name = dept_name_map.get(dept_code, dept_code)
        d_subjects = dept_subjects.get(dept_code, {})

        # Build header subjects for THIS department
        header_subjects = []
        for p in period_info:
            subj = d_subjects.get(p['id'], p['label'])
            header_subjects.append({
                'id': p['id'],
                'label': p['label'],
                'subject_short': shorten(subj),
                'subject_full': subj,
                'time': p['time'],
                'time_status': p['time_status'],
            })

        # Build student rows for this department
        student_rows = []
        dept_present = 0
        dept_absent = 0
        dept_pending = 0

        for student in students_in_dept:
            s_attendance = attendance_map.get(student.id, {})

            periods = []
            for p in period_info:
                pid = p['id']
                subject_full = d_subjects.get(pid, p['label'])
                subject_short = shorten(subject_full)

                if pid in s_attendance:
                    status = s_attendance[pid]
                elif p['time_status'] == 'ended':
                    status = 'Absent'
                else:
                    status = 'Pending'

                if status == 'Present':
                    dept_present += 1
                    total_present_count += 1
                elif status == 'Absent':
                    dept_absent += 1
                    total_absent_count += 1
                else:
                    dept_pending += 1
                    total_pending_count += 1

                periods.append({
                    'id': pid,
                    'status': status,
                    'subject_short': subject_short,
                    'subject_full': subject_full,
                })

            student_rows.append({
                'student': student,
                'periods': periods,
            })

        dept_tables.append({
            'dept_code': dept_code,
            'dept_name': dept_name,
            'header_subjects': header_subjects,
            'student_rows': student_rows,
            'student_count': len(students_in_dept),
            'present': dept_present,
            'absent': dept_absent,
            'pending': dept_pending,
        })

    departments = Student.DEPT_CHOICES

    return render(request, 'recognition/today_attendance.html', {
        'dept_tables': dept_tables,
        'day_order': day_order,
        'today': today,
        'total_students': all_students.count(),
        'total_present': total_present_count,
        'total_absent': total_absent_count,
        'total_pending': total_pending_count,
        'departments': departments,
        'selected_dept': selected_dept,
    })
