from collections import defaultdict
from datetime import datetime

def calculate_recent_attendance_stats(records, days=90):
    """
    Calculates day-based attendance statistics over the last N days.
    A day is considered 'Present' if the student was present for at least one period.
    
    Args:
        records: QuerySet or list of Attendance records
        days: Limit to last N days (default 90)
        
    Returns:
        tuple: (total_days, present_days, absent_days, percentage, daily_attendance_dict)
    """
    today = datetime.now().date()
    daily_attendance = defaultdict(list)
    
    for r in records:
        if (today - r.date).days <= days:
            daily_attendance[r.date].append(r.status)
            
    total_days = len(daily_attendance)
    
    if total_days == 0:
        return 0, 0, 0, 0, daily_attendance
        
    present_days = sum(1 for statuses in daily_attendance.values() if 'Present' in statuses)
    absent_days = total_days - present_days
    percentage = round((present_days / total_days) * 100, 1)
    
    return total_days, present_days, absent_days, percentage, daily_attendance
