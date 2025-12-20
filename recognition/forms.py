from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Student


class StudentSignUpForm(forms.ModelForm):
    """Student signup form using Date of Birth as password instead of traditional password."""
    
    dob = forms.DateField(
        label='Date of Birth (Password)',
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'placeholder': 'DD/MM/YYYY',
            }
        ),
        help_text='Your date of birth will be used as your password (DD/MM/YYYY)'
    )
    
    parent_email = forms.EmailField(
        label="Parent's Email Address",
        required=True,
        help_text='Required for attendance notifications.'
    )

    class Meta:
        model = Student
        fields = ('name', 'rollno', 'department', 'year', 'dob', 'parent_email')
        
    def clean_rollno(self):
        rollno = self.cleaned_data.get('rollno')
        if rollno:
            # Normalize to uppercase and remove spaces
            rollno = rollno.upper().replace(" ", "")
            
            # Check for alphanumeric
            if not rollno.isalnum():
                raise forms.ValidationError("Roll number must be alphanumeric (letters and numbers only).")
                
            # Check for uniqueness
            if Student.objects.filter(rollno__iexact=rollno).exists():
                raise forms.ValidationError("A student with this Roll Number already exists.")
                
        return rollno
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.rollno
        # Set password as DOB in DD/MM/YYYY format
        dob = self.cleaned_data['dob']
        password = dob.strftime('%d/%m/%Y')  # e.g. 12/08/2005
        user.set_password(password)
        if commit:
            user.save()
        return user


class StudentLoginForm(AuthenticationForm):
    # Form for login, will use rollno as username
    pass


class TeacherSignUpForm(UserCreationForm):
    # Reuse rollno field for Staff ID
    rollno = forms.CharField(label='Staff ID', max_length=20)

    class Meta:
        model = Student
        fields = ('name', 'rollno')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'teacher'
        if commit:
            user.save()
        return user
