# hr_payroll/urls.py
from django.urls import path
from . import views

app_name = 'zkteco'

urlpatterns = [
    # Main Views
    path('devices/', views.device_list, name='device_list'),
    path('attendance-logs/', views.attendance_logs, name='attendance_logs'),
    path('attendance-generation/', views.attendance_generation, name='attendance_generation'),
    
    # Device Management AJAX API Endpoints
    path('api/test-connections/', views.test_connections, name='test_connections'),
    path('api/clear-device-data/', views.clear_device_data, name='clear_device_data'),
    
    # User Management AJAX API Endpoints  
    path('api/fetch-users/', views.fetch_users_data, name='fetch_users_data'),
    path('api/import-users/', views.import_users_data, name='import_users_data'),
    
    # Attendance Management AJAX API Endpoints
    path('api/fetch-attendance/', views.fetch_attendance_data, name='fetch_attendance_data'),
    path('api/import-attendance/', views.import_attendance_data, name='import_attendance_data'),
    path('api/generate-attendance/', views.generate_attendance_records, name='generate_attendance_records'),
    path('api/attendance-generation-preview/', views.attendance_generation_preview, name='attendance_generation_preview'),
]