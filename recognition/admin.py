from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Student, Attendance

@admin.register(Student)
class StudentAdmin(UserAdmin):
    list_display = ('rollno', 'name', 'department', 'year', 'is_staff')
    list_filter = ('department', 'year', 'is_staff', 'is_active')
    search_fields = ('rollno', 'name')
    ordering = ('rollno',)
    
    # Custom fieldsets to replace default UserAdmin ones
    fieldsets = (
        (None, {'fields': ('rollno', 'password')}),
        ('Academic & Contact Info', {'fields': ('name', 'department', 'year', 'dob', 'parent_email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('rollno', 'name', 'department', 'year', 'dob', 'parent_email'),
        }),
    )

    def save_model(self, request, obj, form, change):
        # When an admin changes the DOB, automatically update the password
        if change and 'dob' in form.changed_data and obj.dob:
            obj.set_password(obj.dob.strftime('%d/%m/%Y'))
        # When creating a new student via admin and DOB is provided
        elif not change and obj.dob:
            obj.set_password(obj.dob.strftime('%d/%m/%Y'))
            
        super().save_model(request, obj, form, change)

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'period', 'date', 'time', 'status')
    list_filter = ('date', 'period', 'status')
    search_fields = ('student__name', 'student__rollno')
    date_hierarchy = 'date'
