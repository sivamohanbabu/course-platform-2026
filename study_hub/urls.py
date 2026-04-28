from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    DashboardView, DocumentUploadView, IncrementalProgressView, 
    TaskToggleView, RegisterView, AddTaskView, StudyStatView,
    CalendarEventsView, AddReminderView, UpdateReminderView, DeleteReminderView,
    AnalyticsView, SaveReviewView, GetReviewView, AddCourseView,
    DeleteDocumentView, DeleteTaskView
)

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('delete-doc/<int:pk>/', DeleteDocumentView.as_view(), name='delete_doc'),
    path('delete-task/<int:pk>/', DeleteTaskView.as_view(), name='delete_task'),
    path('add-course/', AddCourseView.as_view(), name='add_course'),
    path('analytics/data/', AnalyticsView.as_view(), name='analytics_data'),
    path('review/save/<int:pk>/', SaveReviewView.as_view(), name='save_review'),
    path('review/get/<int:pk>/', GetReviewView.as_view(), name='get_review'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('upload-doc/', DocumentUploadView.as_view(), name='upload_doc'),
    path('add-task/', AddTaskView.as_view(), name='add_task'),
    path('update-progress/<int:pk>/', IncrementalProgressView.as_view(), name='update_progress'),
    path('toggle-task/<int:pk>/', TaskToggleView.as_view(), name='toggle_task'),
    path('study-stat/', StudyStatView.as_view(), name='study_stat'),
    
    # Calendar URLs
    path('calendar/events/', CalendarEventsView.as_view(), name='calendar_events'),
    path('calendar/add/', AddReminderView.as_view(), name='calendar_add'),
    path('calendar/update/<int:pk>/', UpdateReminderView.as_view(), name='calendar_update'),
    path('calendar/delete/<int:pk>/', DeleteReminderView.as_view(), name='calendar_delete'),
]
