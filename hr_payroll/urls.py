from django.urls import path
from . import views

app_name = 'hr_payroll'

urlpatterns = [
    # General HR Dashboard and Analytics
    path('hr/dashboard/', views.HRDashboardView.as_view(), name='hr_dashboard'),
    path('hr/employee-analytics/', views.EmployeeAnalyticsView.as_view(), name='employee_analytics'),
    path('hr/attendance-analytics/', views.AttendanceAnalyticsView.as_view(), name='attendance_analytics'),
    path('hr/search/', views.SearchView.as_view(), name='search'),
    
    # ZKTeco Device Management Dashboard
    path('zkteco/dashboard/', views.ZKDeviceDashboardView.as_view(), name='zkteco_dashboard'),
    path('zkteco/devices/', views.ZKDeviceListView.as_view(), name='zkteco_device_list'),
    path('zkteco/devices/<int:pk>/', views.ZKDeviceDetailView.as_view(), name='zkteco_device_detail'),
    path('zkteco/multi-operations/', views.ZKMultiDeviceOperationsView.as_view(), name='zkteco_multi_operations'),
    
    # ZKTeco Connection Testing
    path('zkteco/connection-test/', views.ZKConnectionTestPageView.as_view(), name='zkteco_connection_test_page'),
    path('zkteco/api/test-connection/', views.ZKConnectionTestView.as_view(), name='zkteco_test_connection_api'),
    
    # ZKTeco Employee Import
    path('zkteco/employee-import/', views.ZKEmployeeImportPageView.as_view(), name='zkteco_employee_import_page'),
    path('zkteco/api/import-employees/', views.ZKEmployeeImportView.as_view(), name='zkteco_import_employees_api'),
    
    # ZKTeco Attendance Management
    path('zkteco/attendance-import/', views.ZKAttendanceImportPageView.as_view(), name='zkteco_attendance_import_page'),
    path('zkteco/api/sync-attendance/', views.ZKAttendanceSyncView.as_view(), name='zkteco_sync_attendance_api'),
    path('zkteco/attendance-preview/<int:device_id>/', views.ZKAttendancePreviewView.as_view(), name='zkteco_attendance_preview'),
    path('zkteco/api/import-attendance/<int:device_id>/', views.ZKAttendanceImportView.as_view(), name='zkteco_import_attendance_api'),
    path('zkteco/api/clear-session/<int:device_id>/', views.ZKClearSessionView.as_view(), name='zkteco_clear_session'),
    
    # API Endpoints
    path('zkteco/api/device-status/', views.ZKDeviceStatusAPI.as_view(), name='zkteco_device_status_api'),
]