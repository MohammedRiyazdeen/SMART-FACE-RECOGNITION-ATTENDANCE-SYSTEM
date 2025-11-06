from django.urls import path
from ..views import auth

urlpatterns = [
    path('login/', auth.login_view, name='login'),
    path('signup/', auth.signup_view, name='signup'),
    path('logout/', auth.logout_view, name='logout'),
    path('teacher/signup/', auth.teacher_signup_view, name='teacher_signup'),
]
