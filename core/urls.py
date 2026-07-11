# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ---------- HOME / AUTH ----------
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ---------- USERS ----------
    path('users/', views.user_list_view, name='user_list'),
    path('users/add-trainee/', views.add_trainee, name='add_trainee'),
    path('users/add-trainer/', views.add_trainer, name='add_trainer'),
    path('users/edit-trainee/<int:user_id>/', views.edit_trainee, name='edit_trainee'),
    path('users/delete-trainee/<int:user_id>/', views.delete_trainee, name='delete_trainee'),

    # ---------- MEASUREMENTS ----------
    path('measurements/', views.measurement_list, name='measurement_list'),
    path('measurements/add/', views.add_measurement, name='add_measurement'),
    path('measurements/detail/<int:pk>/', views.measurement_detail, name='measurement_detail'),
    path('measurements/charts/<int:user_id>/', views.measurement_charts, name='measurement_charts'),


    path('trainee/<int:user_id>/photos/', views.compare_photos, name='compare_photos'),


    # ---------- GOALS ----------
    path('goals/', views.goal_list, name='goal_list'),
    path('goals/add/', views.goal_add, name='add_goal'),
    path('goals/toggle/<int:pk>/', views.goal_toggle_complete, name='goal_toggle_complete'),

    # ---------- CHAT ----------
    path('chat/<int:user_id>/', views.chat_view, name='chat'),

    # ---------- PHOTO COMPARISON ----------
    path('trainee/<int:user_id>/photos/', views.compare_photos, name='compare_photos'),
]
