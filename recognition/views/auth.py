from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from ..forms import StudentSignUpForm, StudentLoginForm, TeacherSignUpForm


def signup_view(request):
    if request.method == 'POST':
        form = StudentSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect('login')
    else:
        form = StudentSignUpForm()
    return render(request, 'recognition/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = StudentLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            selected_role = request.POST.get('login_role', 'student')

            # Enforce role-based login
            if selected_role == 'student' and user.role != 'student':
                messages.error(request, "This is a teacher account. Please use the Teacher tab to login.")
                return render(request, 'recognition/login.html', {'form': StudentLoginForm()})
            elif selected_role == 'teacher' and user.role != 'teacher':
                messages.error(request, "This is a student account. Please use the Student tab to login.")
                return render(request, 'recognition/login.html', {'form': StudentLoginForm()})

            login(request, user)
            if user.role == 'teacher':
                return redirect('teacher_dashboard')
            elif user.role == 'admin':
                return redirect('/admin/')
            return redirect('index')
    else:
        form = StudentLoginForm()
    return render(request, 'recognition/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


def teacher_signup_view(request):
    if request.method == 'POST':
        form = TeacherSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect('login')
    else:
        form = TeacherSignUpForm()
    return render(request, 'recognition/teacher_signup.html', {'form': form})
