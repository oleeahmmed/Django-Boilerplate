import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView

from .models import (
    Employee, Department, Designation, Attendance, 
    LeaveApplication, ZkDevice, AttendanceLog
)
from .zkteco_device_manager import (
    ZKTecoConnectionChecker,
    ZKTecoEmployeeImporter,
    ZKTecoAttendanceImporter
)

logger = logging.getLogger(__name__)

@method_decorator(staff_member_required, name='dispatch')
class HRDashboardView(PermissionRequiredMixin, TemplateView):
    template_name = 'admin/hr_dashboard.html'
    permission_required = 'hr_payroll.view_dashboard'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context.update({
            'total_employees': Employee.objects.filter(is_active=True).count(),
            'total_departments': Department.objects.count(),
            'total_designations': Designation.objects.count(),
            'active_devices': ZkDevice.objects.filter(is_active=True).count(),
        })
        
        today = timezone.now().date()
        today_attendance = Attendance.objects.filter(date=today).aggregate(
            present=Count('id', filter=Q(status='P')),
            absent=Count('id', filter=Q(status='A')),
            leave=Count('id', filter=Q(status='L'))
        )
        context.update({
            'today_present': today_attendance['present'] or 0,
            'today_absent': today_attendance['absent'] or 0,
            'today_leave': today_attendance['leave'] or 0,
        })
        
        context['pending_leaves'] = LeaveApplication.objects.filter(status='pending').count()
        
        dept_stats = Department.objects.annotate(
            employee_count=Count('employee', filter=Q(employee__is_active=True))
        ).values('name', 'employee_count')
        context['department_stats'] = list(dept_stats)
        
        context['recent_logs'] = AttendanceLog.objects.select_related('employee', 'device').order_by('-timestamp')[:10]
        
        return context

@method_decorator(staff_member_required, name='dispatch')
class ZKDeviceDashboardView(PermissionRequiredMixin, TemplateView):
    template_name = 'zkteco/dashboard.html'
    permission_required = 'hr_payroll.view_zkteco_dashboard'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['total_devices'] = ZkDevice.objects.filter(is_active=True).count()
        context['total_employees'] = Employee.objects.filter(is_active=True).count()
        
        yesterday = timezone.now() - timedelta(days=1)
        context['recent_attendance'] = AttendanceLog.objects.filter(
            timestamp__gte=yesterday
        ).count()
        
        context['devices_by_company'] = ZkDevice.objects.filter(
            is_active=True
        ).values('company__name').annotate(
            device_count=Count('id')
        )
        
        context['devices'] = ZkDevice.objects.select_related('company').filter(is_active=True)
        
        return context

@method_decorator(staff_member_required, name='dispatch')
class ZKDeviceListView(PermissionRequiredMixin, ListView):
    model = ZkDevice
    template_name = 'zkteco/device_list.html'
    context_object_name = 'devices'
    paginate_by = 20
    permission_required = 'hr_payroll.view_zkdevice'
    
    def get_queryset(self):
        queryset = ZkDevice.objects.select_related('company')
        
        company_id = self.request.GET.get('company')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        
        is_active = self.request.GET.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active == 'true')
        
        return queryset.order_by('-created_at')

@method_decorator(staff_member_required, name='dispatch')
class ZKDeviceDetailView(PermissionRequiredMixin, DetailView):
    model = ZkDevice
    template_name = 'zkteco/device_detail.html'
    context_object_name = 'device'
    permission_required = 'hr_payroll.view_zkdevice'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        device = self.get_object()
        
        context['employees_count'] = Employee.objects.filter(
            company=device.company,
            is_active=True
        ).count()
        
        context['recent_logs'] = AttendanceLog.objects.filter(
            device=device
        ).select_related('employee').order_by('-timestamp')[:10]
        
        week_ago = timezone.now() - timedelta(days=7)
        context['weekly_attendance'] = AttendanceLog.objects.filter(
            device=device,
            timestamp__gte=week_ago
        ).count()
        
        return context

# ZKTeco Connection Testing Views
@method_decorator(staff_member_required, name='dispatch')
class ZKConnectionTestView(PermissionRequiredMixin, View):
    permission_required = 'hr_payroll.test_zkdevice_connection'
    
    def post(self, request):
        try:
            device_ids = request.POST.getlist('device_ids')
            if not device_ids:
                return JsonResponse({'error': 'No devices selected'}, status=400)
            
            # Convert to integers and validate
            try:
                device_ids = [int(device_id) for device_id in device_ids]
            except (ValueError, TypeError):
                return JsonResponse({'error': 'Invalid device IDs provided'}, status=400)
            
            # Get devices
            devices = ZkDevice.objects.filter(id__in=device_ids, is_active=True)
            if not devices.exists():
                return JsonResponse({'error': 'No valid devices found'}, status=400)
            
            # Test connections
            checker = ZKTecoConnectionChecker()
            results = checker.check_multiple_devices(devices)
            
            return JsonResponse({'results': results})
            
        except Exception as e:
            logger.error(f"Error in connection test: {str(e)}")
            return JsonResponse({'error': f'Connection test failed: {str(e)}'}, status=500)

@method_decorator(staff_member_required, name='dispatch')
class ZKConnectionTestPageView(PermissionRequiredMixin, TemplateView):
    template_name = 'zkteco/connection_test.html'
    permission_required = 'hr_payroll.test_zkdevice_connection'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['devices'] = ZkDevice.objects.select_related('company').filter(is_active=True)
        return context

# ZKTeco Employee Import Views
@method_decorator(staff_member_required, name='dispatch')
class ZKEmployeeImportView(PermissionRequiredMixin, View):
    permission_required = 'hr_payroll.import_employees'
    
    def post(self, request):
        device_ids = request.POST.getlist('device_ids')
        if not device_ids:
            return JsonResponse({'error': 'No devices selected'}, status=400)
        
        try:
            device_ids = [int(device_id) for device_id in device_ids]
            devices = ZkDevice.objects.filter(id__in=device_ids)
            
            importer = ZKTecoEmployeeImporter()
            results = importer.import_from_multiple_devices(devices)
            
            return JsonResponse({'results': results})
            
        except ValueError:
            return JsonResponse({'error': 'Invalid device IDs'}, status=400)
        except Exception as e:
            logger.error(f"Error importing employees: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(staff_member_required, name='dispatch')
class ZKEmployeeImportPageView(PermissionRequiredMixin, TemplateView):
    template_name = 'zkteco/employee_import.html'
    permission_required = 'hr_payroll.import_employees'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['devices'] = ZkDevice.objects.select_related('company').filter(is_active=True)
        return context

# ZKTeco Attendance Import Views
@method_decorator(staff_member_required, name='dispatch')
class ZKAttendanceSyncView(PermissionRequiredMixin, View):
    permission_required = 'hr_payroll.sync_attendance'
    
    def post(self, request):
        device_ids = request.POST.getlist('device_ids')
        if not device_ids:
            return JsonResponse({'error': 'No devices selected'}, status=400)
        
        try:
            device_ids = [int(device_id) for device_id in device_ids]
            devices = ZkDevice.objects.filter(id__in=device_ids)
            
            importer = ZKTecoAttendanceImporter()
            sync_results = []
            
            for device in devices:
                success, logs, message = importer.sync_attendance_data(device)
                sync_results.append({
                    'device_id': device.id,
                    'device_name': device.name,
                    'success': success,
                    'message': message,
                    'logs_count': len(logs),
                    'ready_count': sum(1 for log in logs if log.get('status') == 'ready')
                })
                
                if success:
                    # Store logs in session for preview
                    session_key = f'attendance_sync_data_{device.id}'
                    request.session[session_key] = {
                        'device_id': device.id,
                        'device_name': device.name,
                        'logs': logs,
                        'synced_at': timezone.now().isoformat()
                    }
            
            request.session.modified = True
            return JsonResponse({'results': sync_results})
            
        except ValueError:
            return JsonResponse({'error': 'Invalid device IDs'}, status=400)
        except Exception as e:
            logger.error(f"Error syncing attendance: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(staff_member_required, name='dispatch')
class ZKAttendancePreviewView(PermissionRequiredMixin, TemplateView):
    template_name = 'zkteco/attendance_preview.html'
    permission_required = 'hr_payroll.sync_attendance'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        device_id = kwargs.get('device_id')
        
        session_key = f'attendance_sync_data_{device_id}'
        sync_data = self.request.session.get(session_key)
        
        if not sync_data:
            context['error'] = 'No attendance data found. Please sync again.'
            return context
        
        # Filter logs by status
        logs = sync_data.get('logs', [])
        context['device_name'] = sync_data.get('device_name')
        context['device_id'] = device_id
        context['all_logs'] = logs
        context['ready_logs'] = [log for log in logs if log.get('status') == 'ready']
        context['duplicate_logs'] = [log for log in logs if log.get('status') == 'duplicate']
        context['error_logs'] = [log for log in logs if log.get('status') == 'error']
        context['synced_at'] = sync_data.get('synced_at')
        context['total_logs'] = len(logs)
        
        return context

@method_decorator(staff_member_required, name='dispatch')
class ZKAttendanceImportView(PermissionRequiredMixin, View):
    permission_required = 'hr_payroll.import_attendance'
    
    def post(self, request, device_id):
        try:
            device = get_object_or_404(ZkDevice, id=device_id)
            
            # Get selected logs from request
            selected_log_indices = request.POST.getlist('selected_logs')
            if not selected_log_indices:
                return JsonResponse({'error': 'No logs selected for import'}, status=400)
            
            # Get sync data from session
            session_key = f'attendance_sync_data_{device_id}'
            sync_data = request.session.get(session_key)
            
            if not sync_data:
                return JsonResponse({'error': 'No sync data found. Please sync again.'}, status=400)
            
            # Filter selected logs
            all_logs = sync_data.get('logs', [])
            selected_logs = []
            
            try:
                selected_indices = [int(i) for i in selected_log_indices]
                selected_logs = [all_logs[i] for i in selected_indices if i < len(all_logs)]
            except (ValueError, IndexError):
                return JsonResponse({'error': 'Invalid log selection'}, status=400)
            
            # Import selected logs
            importer = ZKTecoAttendanceImporter()
            result = importer.import_selected_logs(device, selected_logs)
            
            # Clear session data after successful import
            if result['imported_count'] > 0:
                if session_key in request.session:
                    del request.session[session_key]
                    request.session.modified = True
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Error importing attendance logs: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(staff_member_required, name='dispatch')
class ZKAttendanceImportPageView(PermissionRequiredMixin, TemplateView):
    template_name = 'zkteco/attendance_import.html'
    permission_required = 'hr_payroll.import_attendance'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['devices'] = ZkDevice.objects.select_related('company').filter(is_active=True)
        return context

# Multi-device operations view
@method_decorator(staff_member_required, name='dispatch')
class ZKMultiDeviceOperationsView(PermissionRequiredMixin, TemplateView):
    template_name = 'zkteco/multi_device_operations.html'
    permission_required = 'hr_payroll.view_zkdevice'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['devices'] = ZkDevice.objects.select_related('company').filter(is_active=True)
        return context

# API Views for AJAX operations
@method_decorator(staff_member_required, name='dispatch')
class ZKDeviceStatusAPI(PermissionRequiredMixin, View):
    permission_required = 'hr_payroll.view_zkdevice'
    
    def get(self, request):
        devices = ZkDevice.objects.select_related('company').filter(is_active=True)
        devices_data = []
        
        for device in devices:
            devices_data.append({
                'id': device.id,
                'name': device.name,
                'ip_address': device.ip_address,
                'port': device.port,
                'company_name': device.company.name,
                'last_synced': device.last_synced.isoformat() if device.last_synced else None,
                'is_active': device.is_active
            })
        
        return JsonResponse({'devices': devices_data})

# Clear session data view
@method_decorator(staff_member_required, name='dispatch')
class ZKClearSessionView(PermissionRequiredMixin, View):
    permission_required = 'hr_payroll.sync_attendance'
    
    def post(self, request, device_id):
        session_key = f'attendance_sync_data_{device_id}'
        if session_key in request.session:
            del request.session[session_key]
            request.session.modified = True
            return JsonResponse({'success': True, 'message': 'Session data cleared'})
        return JsonResponse({'success': False, 'message': 'No session data found'})

# Search and filter views
@method_decorator(staff_member_required, name='dispatch')
class SearchView(PermissionRequiredMixin, TemplateView):
    template_name = 'admin/search.html'
    permission_required = 'hr_payroll.view_search'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '')
        if query:
            context['employees'] = Employee.objects.filter(
                Q(name__icontains=query) | Q(employee_id__icontains=query),
                is_active=True
            ).select_related('department', 'designation')[:50]
        else:
            context['employees'] = []
        return context

# Employee analytics view
@method_decorator(staff_member_required, name='dispatch')
class EmployeeAnalyticsView(PermissionRequiredMixin, TemplateView):
    template_name = 'admin/employee_analytics.html'
    permission_required = 'hr_payroll.view_employee_analytics'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        dept_data = Department.objects.annotate(
            count=Count('employee', filter=Q(employee__is_active=True))
        ).values('name', 'count')
        context['dept_chart_data'] = {
            'labels': [item['name'] for item in dept_data],
            'data': [item['count'] for item in dept_data]
        }
        
        desig_data = Employee.objects.filter(is_active=True).values('designation__name').annotate(
            count=Count('id')
        )
        context['desig_chart_data'] = {
            'labels': [item['designation__name'] for item in desig_data],
            'data': [item['count'] for item in desig_data]
        }
        
        return context

# Attendance analytics view
@method_decorator(staff_member_required, name='dispatch')
class AttendanceAnalyticsView(PermissionRequiredMixin, TemplateView):
    template_name = 'admin/attendance_analytics.html'
    permission_required = 'hr_payroll.view_attendance_analytics'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        if 'start_date' in self.request.GET and 'end_date' in self.request.GET:
            try:
                start_date = datetime.strptime(self.request.GET['start_date'], '%Y-%m-%d').date()
                end_date = datetime.strptime(self.request.GET['end_date'], '%Y-%m-%d').date()
            except ValueError:
                pass
        
        daily_attendance = Attendance.objects.filter(
            date__gte=start_date, date__lte=end_date
        ).values('date').annotate(
            present=Count('id', filter=Q(status='P')),
            absent=Count('id', filter=Q(status='A')),
            leave=Count('id', filter=Q(status='L'))
        ).order_by('date')
        
        context['daily_attendance_chart'] = {
            'labels': [item['date'].strftime('%Y-%m-%d') for item in daily_attendance],
            'present_data': [item['present'] for item in daily_attendance],
            'absent_data': [item['absent'] for item in daily_attendance],
            'leave_data': [item['leave'] for item in daily_attendance],
        }

        overall_stats = Attendance.objects.filter(
            date__gte=start_date, date__lte=end_date
        ).aggregate(
            total_present=Count('id', filter=Q(status='P')),
            total_absent=Count('id', filter=Q(status='A')),
            total_leave=Count('id', filter=Q(status='L'))
        )
        
        context['overall_attendance_summary'] = {
            'total_present': overall_stats['total_present'] or 0,
            'total_absent': overall_stats['total_absent'] or 0,
            'total_leave': overall_stats['total_leave'] or 0,
        }
        
        return context
