# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Min, Max
from django.utils import timezone
from datetime import datetime, date, timedelta
from django.utils.dateparse import parse_date

import json
import logging

from .models import ZkDevice, AttendanceLog, Employee, Attendance, Shift, Department, Designation
from .zkteco_device_manager import ZKTecoDeviceManager
from core.models import Company

logger = logging.getLogger(__name__)

# Initialize device manager
device_manager = ZKTecoDeviceManager()

def get_company_from_request(request):
    """Helper to get company - modify based on your auth system"""
    try:
        # Get first company or implement your company selection logic
        company = Company.objects.first()
        if company:
            return company
        return None
    except Exception as e:
        logger.error(f"Error getting company: {str(e)}")
        return None

@login_required
def device_list(request):
    """Display list of ZKTeco devices with enhanced UI"""
    company = get_company_from_request(request)
    if not company:
        messages.error(request, "No company access found.")
        return render(request, 'zkteco/device_list.html', {
            'objects': [], 
            'total_devices': 0,
            'error_message': 'No company access found'
        })
    
    devices = ZkDevice.objects.filter(company=company).order_by('name')
    active_devices = devices.filter(is_active=True)
    
    # Get attendance log counts for each device
    device_stats = {}
    total_attendance_records = 0
    
    for device in devices:
        attendance_count = AttendanceLog.objects.filter(device=device).count()
        device_stats[str(device.id)] = {
            'attendance_count': attendance_count,
            'last_synced': device.last_synced.isoformat() if device.last_synced else None,
            'is_active': device.is_active
        }
        total_attendance_records += attendance_count
    
    context = {
        'objects': devices,
        'total_devices': devices.count(),
        'active_devices': active_devices.count(),
        'inactive_devices': devices.filter(is_active=False).count(),
        'total_attendance_records': total_attendance_records,
        'device_stats': json.dumps(device_stats),
        'company': company,
    }
    return render(request, 'zkteco/device_list.html', context)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def test_connections(request):
    """AJAX endpoint to test connections to multiple selected devices"""
    try:
        data = json.loads(request.body)
        device_ids = data.get('device_ids', [])
        
        if not device_ids:
            return JsonResponse({'success': False, 'error': 'No devices selected'})
        
        company = get_company_from_request(request)
        if not company:
            return JsonResponse({'success': False, 'error': 'No company access found'})
        
        devices = ZkDevice.objects.filter(id__in=device_ids, company=company)
        device_list = []
        
        for device in devices:
            device_data = {
                'ip': device.ip_address,
                'port': device.port,
                'id': device.id,
                'name': device.name,
                'password': device.password if device.password else 0
            }
            device_list.append(device_data)
        
        results = device_manager.test_multiple_connections(device_list)
        
        # Update device status in database
        response_data = []
        for device in devices:
            device_ip = device.ip_address
            if device_ip in results:
                test_result = results[device_ip]
                
                if test_result['success']:
                    device.is_active = True
                    device.last_synced = timezone.now()
                    status_message = "Connected successfully"
                    
                    info = test_result.get('info', {})
                    if info:
                        status_message += f" - Users: {info.get('user_count', 0)}, Records: {info.get('attendance_count', 0)}"
                else:
                    device.is_active = False
                    status_message = test_result.get('error', 'Connection failed')
                
                device.save()
                
                response_data.append({
                    'device_id': device.id,
                    'device_name': device.name,
                    'success': test_result['success'],
                    'message': status_message,
                    'info': test_result.get('info', {}) if test_result['success'] else None
                })
        
        return JsonResponse({
            'success': True,
            'results': response_data,
            'message': f'Tested {len(results)} devices'
        })
        
    except Exception as e:
        logger.error(f"Error testing connections: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def fetch_users_data(request):
    """AJAX endpoint to fetch users from selected devices (preview before import)"""
    try:
        data = json.loads(request.body)
        device_ids = data.get('device_ids', [])
        
        if not device_ids:
            return JsonResponse({'success': False, 'error': 'No devices selected'})
        
        company = get_company_from_request(request)
        if not company:
            return JsonResponse({'success': False, 'error': 'No company access found'})
        
        devices = ZkDevice.objects.filter(id__in=device_ids, company=company)
        device_list = []
        
        for device in devices:
            device_data = {
                'ip': device.ip_address,
                'port': device.port,
                'id': device.id,
                'name': device.name,
                'password': device.password if device.password else 0
            }
            device_list.append(device_data)
        
        all_users, results = device_manager.get_multiple_users_data(device_list)
        
        # Format users data for response and check duplicates
        formatted_users = []
        for user in all_users:
            existing_employee = Employee.objects.filter(
                Q(zkteco_id=user['user_id']) | Q(employee_id=user['user_id']),
                company=company
            ).first()
            
            formatted_users.append({
                'user_id': user['user_id'],
                'name': user['name'],
                'privilege': user.get('privilege', 0),
                'device_ip': user['device_ip'],
                'device_name': user['device_name'],
                'existing_employee': existing_employee.name if existing_employee else None,
                'existing_employee_id': existing_employee.employee_id if existing_employee else None,
                'is_existing': bool(existing_employee),
                'can_import': not bool(existing_employee)  # Can only import if not existing
            })
        
        # Store in session for import
        request.session['fetched_users_data'] = [
            {
                'user_id': user['user_id'],
                'name': user['name'],
                'privilege': user.get('privilege', 0),
                'device_ip': user['device_ip'],
                'device_name': user['device_name']
            }
            for user in formatted_users if user['can_import']
        ]
        
        return JsonResponse({
            'success': True,
            'users_data': formatted_users,
            'results': results,
            'total_users': len(all_users),
            'new_users': len([u for u in formatted_users if u['can_import']]),
            'existing_users': len([u for u in formatted_users if not u['can_import']]),
            'message': f'Retrieved {len(all_users)} users from {len(devices)} devices'
        })
        
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def import_users_data(request):
    """AJAX endpoint to import selected users as employees"""
    try:
        data = json.loads(request.body)
        selected_indices = data.get('selected_indices', [])
        import_all = data.get('import_all', False)
        
        fetched_data = request.session.get('fetched_users_data', [])
        
        if not fetched_data:
            return JsonResponse({'success': False, 'error': 'No data to import. Please fetch data first.'})
        
        company = get_company_from_request(request)
        if not company:
            return JsonResponse({'success': False, 'error': 'No company access found'})
        
        # Get default department and designation
        default_dept = Department.objects.filter(company=company).first()
        default_designation = Designation.objects.filter(company=company).first()
        
        if not default_dept:
            return JsonResponse({'success': False, 'error': 'No department found. Please create at least one department first.'})
        
        if not default_designation:
            return JsonResponse({'success': False, 'error': 'No designation found. Please create at least one designation first.'})
        
        if import_all:
            users_to_import = fetched_data
        else:
            if not selected_indices:
                return JsonResponse({'success': False, 'error': 'No users selected for import'})
            users_to_import = [fetched_data[i] for i in selected_indices if i < len(fetched_data)]
        
        imported_count = 0
        duplicate_count = 0
        error_count = 0
        
        with transaction.atomic():
            for user in users_to_import:
                try:
                    # Check for duplicates again
                    existing = Employee.objects.filter(
                        Q(zkteco_id=user['user_id']) | Q(employee_id=user['user_id']),
                        company=company
                    ).exists()
                    
                    if existing:
                        duplicate_count += 1
                        continue
                    
                    # Create employee
                    Employee.objects.create(
                        company=company,
                        department=default_dept,
                        designation=default_designation,
                        employee_id=user['user_id'],
                        zkteco_id=user['user_id'],
                        name=user['name'] or f"User_{user['user_id']}",
                        expected_working_hours=8.00,
                        overtime_grace_minutes=15,
                        is_active=True
                    )
                    
                    imported_count += 1
                    
                except Exception as e:
                    logger.error(f"Error importing user {user}: {str(e)}")
                    error_count += 1
        
        # Clear session data after successful import
        if 'fetched_users_data' in request.session:
            del request.session['fetched_users_data']
        
        return JsonResponse({
            'success': True,
            'imported_count': imported_count,
            'duplicate_count': duplicate_count,
            'error_count': error_count,
            'message': f'Import completed: {imported_count} imported, {duplicate_count} duplicates skipped, {error_count} errors.'
        })
        
    except Exception as e:
        logger.error(f"Error importing users: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def fetch_attendance_data(request):
    """AJAX endpoint to fetch attendance data from selected devices (preview before import)"""
    try:
        data = json.loads(request.body)
        device_ids = data.get('device_ids', [])
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not device_ids:
            return JsonResponse({'success': False, 'error': 'No devices selected'})
        
        company = get_company_from_request(request)
        if not company:
            return JsonResponse({'success': False, 'error': 'No company access found'})
        
        devices = ZkDevice.objects.filter(id__in=device_ids, company=company)
        device_list = []
        
        for device in devices:
            device_data = {
                'ip': device.ip_address,
                'port': device.port,
                'id': device.id,
                'name': device.name,
                'password': device.password if device.password else 0
            }
            device_list.append(device_data)
        
        # Convert string dates to date objects
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
        
        attendance_data, fetch_results = device_manager.get_multiple_attendance_data(
            device_list, start_date_obj, end_date_obj
        )
        
        # Process and format the data with duplicate checking
        formatted_data = []
        for record in attendance_data:
            # Find matching employee
            employee = Employee.objects.filter(
                Q(zkteco_id=record['zkteco_id']) | Q(employee_id=record['zkteco_id']),
                company=company
            ).first()
            
            # Check if already imported (duplicate check)
            is_imported = False
            if employee:
                is_imported = AttendanceLog.objects.filter(
                    employee=employee,
                    timestamp=record['timestamp'],
                    device__ip_address=record['device_ip']
                ).exists()
            
            formatted_record = {
                'device_name': record['device_name'],
                'device_ip': record['device_ip'],
                'zkteco_id': record['zkteco_id'],
                'employee_id': employee.employee_id if employee else record['zkteco_id'],
                'employee_name': employee.name if employee else 'Unknown Employee',
                'timestamp': record['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'date': record['timestamp'].strftime('%Y-%m-%d'),
                'time': record['timestamp'].strftime('%H:%M:%S'),
                'punch_type': record.get('punch_type', 0),
                'verify_type': record.get('verify_type', 0),
                'source_type': record.get('source_type', 'device'),
                'is_imported': is_imported,
                'has_employee': bool(employee),
                'can_import': bool(employee) and not is_imported,
                'raw_timestamp': record['timestamp']
            }
            formatted_data.append(formatted_record)
        
        # Sort by timestamp (newest first)
        formatted_data.sort(key=lambda x: x['raw_timestamp'], reverse=True)
        
        # Store in session for import (only importable records)
        session_data = []
        for record in formatted_data:
            if record['can_import']:
                session_record = {
                    'zkteco_id': record['zkteco_id'],
                    'timestamp': record['raw_timestamp'].isoformat(),
                    'device_ip': record['device_ip'],
                    'punch_type': record['punch_type'],
                    'verify_type': record['verify_type'],
                    'source_type': record['source_type']
                }
                session_data.append(session_record)
        
        request.session['fetched_attendance_data'] = session_data
        
        return JsonResponse({
            'success': True,
            'data': formatted_data,
            'total_records': len(formatted_data),
            'new_records': len([r for r in formatted_data if r['can_import']]),
            'imported_records': len([r for r in formatted_data if r['is_imported']]),
            'missing_employee_records': len([r for r in formatted_data if not r['has_employee']]),
            'fetch_results': fetch_results,
            'message': f'Fetched {len(formatted_data)} attendance records'
        })
        
    except Exception as e:
        logger.error(f"Error fetching attendance data: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def import_attendance_data(request):
    """AJAX endpoint to import selected attendance data to database"""
    try:
        data = json.loads(request.body)
        selected_indices = data.get('selected_indices', [])
        import_all = data.get('import_all', False)
        
        fetched_data = request.session.get('fetched_attendance_data', [])
        
        if not fetched_data:
            return JsonResponse({'success': False, 'error': 'No data to import. Please fetch data first.'})
        
        company = get_company_from_request(request)
        if not company:
            return JsonResponse({'success': False, 'error': 'No company access found'})
        
        if import_all:
            records_to_import = fetched_data
        else:
            if not selected_indices:
                return JsonResponse({'success': False, 'error': 'No records selected for import'})
            records_to_import = [fetched_data[i] for i in selected_indices if i < len(fetched_data)]
        
        imported_count = 0
        duplicate_count = 0
        error_count = 0
        missing_employee_count = 0
        
        with transaction.atomic():
            for record in records_to_import:
                try:
                    # Find employee
                    employee = Employee.objects.filter(
                        Q(zkteco_id=record['zkteco_id']) | Q(employee_id=record['zkteco_id']),
                        company=company
                    ).first()
                    
                    if not employee:
                        missing_employee_count += 1
                        continue
                    
                    # Find device
                    device = ZkDevice.objects.filter(
                        ip_address=record['device_ip'], 
                        company=company
                    ).first()
                    
                    # Convert timestamp back to datetime
                    timestamp = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                    if timestamp.tzinfo is None:
                        timestamp = timezone.make_aware(timestamp)
                    
                    # Final duplicate check
                    existing = AttendanceLog.objects.filter(
                        employee=employee,
                        timestamp=timestamp,
                        device=device
                    ).exists()
                    
                    if existing:
                        duplicate_count += 1
                        continue
                    
                    # Create attendance log
                    AttendanceLog.objects.create(
                        employee=employee,
                        device=device,
                        timestamp=timestamp,
                        source_type=record.get('source_type', 'device')
                    )
                    
                    imported_count += 1
                    
                except Exception as e:
                    logger.error(f"Error importing record {record}: {str(e)}")
                    error_count += 1
        
        # Clear session data after successful import
        if 'fetched_attendance_data' in request.session:
            del request.session['fetched_attendance_data']
        
        return JsonResponse({
            'success': True,
            'imported_count': imported_count,
            'duplicate_count': duplicate_count,
            'error_count': error_count,
            'missing_employee_count': missing_employee_count,
            'message': f'Import completed: {imported_count} imported, {duplicate_count} duplicates skipped, {missing_employee_count} missing employees, {error_count} errors.'
        })
        
    except Exception as e:
        logger.error(f"Error importing attendance data: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def clear_device_data(request):
    """AJAX endpoint to clear attendance data from devices"""
    try:
        data = json.loads(request.body)
        device_ids = data.get('device_ids', [])
        
        if not device_ids:
            return JsonResponse({'success': False, 'error': 'No devices selected'})
        
        company = get_company_from_request(request)
        if not company:
            return JsonResponse({'success': False, 'error': 'No company access found'})
        
        devices = ZkDevice.objects.filter(id__in=device_ids, company=company)
        results = []
        
        for device in devices:
            try:
                success, message = device_manager.clear_attendance_data(device.ip_address)
                results.append({
                    'device_name': device.name,
                    'success': success,
                    'message': message
                })
            except Exception as e:
                results.append({
                    'device_name': device.name,
                    'success': False,
                    'message': str(e)
                })
        
        success_count = sum(1 for r in results if r['success'])
        
        return JsonResponse({
            'success': True,
            'results': results,
            'message': f'Data cleared from {success_count} out of {len(devices)} devices'
        })
        
    except Exception as e:
        logger.error(f"Error clearing device data: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def attendance_logs(request):
    """Display imported attendance logs with enhanced filtering and pagination"""
    company = get_company_from_request(request)
    if not company:
        messages.error(request, "No company access found.")
        return render(request, 'zkteco/attendance_log_list.html', {
            'logs': [], 
            'devices': [], 
            'employees': [],
            'total_logs': 0
        })
    
    # Base queryset
    logs = AttendanceLog.objects.filter(
        employee__company=company
    ).select_related('employee', 'device').order_by('-timestamp')
    
    # Get filter parameters
    device_id = request.GET.get('device')
    employee_id = request.GET.get('employee')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    search = request.GET.get('search')
    source_type = request.GET.get('source_type')
    date_range = request.GET.get('date_range')  # today, yesterday, this_week, last_week, this_month, last_month
    
    # Handle predefined date ranges
    today = timezone.now().date()
    if date_range:
        if date_range == 'today':
            start_date = end_date = today.isoformat()
        elif date_range == 'yesterday':
            yesterday = today - timedelta(days=1)
            start_date = end_date = yesterday.isoformat()
        elif date_range == 'this_week':
            start_of_week = today - timedelta(days=today.weekday())
            start_date = start_of_week.isoformat()
            end_date = today.isoformat()
        elif date_range == 'last_week':
            start_of_last_week = today - timedelta(days=today.weekday() + 7)
            end_of_last_week = start_of_last_week + timedelta(days=6)
            start_date = start_of_last_week.isoformat()
            end_date = end_of_last_week.isoformat()
        elif date_range == 'this_month':
            start_date = today.replace(day=1).isoformat()
            end_date = today.isoformat()
        elif date_range == 'last_month':
            first_day_this_month = today.replace(day=1)
            last_day_last_month = first_day_this_month - timedelta(days=1)
            first_day_last_month = last_day_last_month.replace(day=1)
            start_date = first_day_last_month.isoformat()
            end_date = last_day_last_month.isoformat()
    
    # Apply filters
    if device_id and device_id.isdigit():
        logs = logs.filter(device_id=int(device_id))
    
    if employee_id and employee_id.isdigit():
        logs = logs.filter(employee_id=int(employee_id))
    
    if start_date:
        try:
            parsed_start_date = parse_date(start_date)
            if parsed_start_date:
                logs = logs.filter(timestamp__date__gte=parsed_start_date)
        except ValueError:
            pass
    
    if end_date:
        try:
            parsed_end_date = parse_date(end_date)
            if parsed_end_date:
                logs = logs.filter(timestamp__date__lte=parsed_end_date)
        except ValueError:
            pass
    
    if search:
        logs = logs.filter(
            Q(employee__name__icontains=search) |
            Q(employee__employee_id__icontains=search) |
            Q(employee__zkteco_id__icontains=search)
        )
    
    if source_type:
        logs = logs.filter(source_type=source_type)
    
    # Get statistics for filtered results
    total_logs = logs.count()
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    devices = ZkDevice.objects.filter(company=company).order_by('name')
    employees = Employee.objects.filter(company=company, is_active=True).order_by('name')
    
    # Get date range statistics
    date_stats = logs.aggregate(
        earliest=Min('timestamp'),
        latest=Max('timestamp')
    )
    
    context = {
        'logs': page_obj,
        'devices': devices,
        'employees': employees,
        'total_logs': total_logs,
        'company': company,
        'date_stats': date_stats,
        # Current filter values
        'current_device': device_id,
        'current_employee': employee_id,
        'current_start_date': start_date,
        'current_end_date': end_date,
        'current_search': search,
        'current_source_type': source_type,
        'current_date_range': date_range,
    }
    return render(request, 'zkteco/attendance_log_list.html', context)

@login_required
def attendance_generation(request):
    """Display attendance generation page with comprehensive options"""
    company = get_company_from_request(request)
    if not company:
        messages.error(request, "No company access found.")
        return redirect('zkteco:device_list')
    
    # Get statistics for guidance
    logs_stats = AttendanceLog.objects.filter(
        employee__company=company
    ).aggregate(
        total_logs=Count('id'),
        earliest=Min('timestamp'),
        latest=Max('timestamp')
    )
    
    # Get attendance records statistics
    attendance_stats = Attendance.objects.filter(
        employee__company=company
    ).aggregate(
        total_records=Count('id'),
        earliest=Min('date'),
        latest=Max('date')
    )
    
    # Get employees with attendance logs but no attendance records
    employees_with_logs = Employee.objects.filter(
        company=company,
        attendancelog__isnull=False
    ).distinct()
    
    # Get available departments and shifts
    departments = Department.objects.filter(company=company).order_by('name')
    shifts = Shift.objects.filter(company=company).order_by('name')
    devices = ZkDevice.objects.filter(company=company).order_by('name')
    
    context = {
        'company': company,
        'logs_stats': logs_stats,
        'attendance_stats': attendance_stats,
        'employees_with_logs': employees_with_logs,
        'departments': departments,
        'shifts': shifts,
        'devices': devices,
        'today': timezone.now().date(),
    }
    
    return render(request, 'zkteco/attendance_generation.html', context)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def attendance_generation_preview(request):
    """Preview attendance records that will be generated based on criteria"""
    try:
        data = json.loads(request.body)
        company = get_company_from_request(request)
        if not company:
            return JsonResponse({'success': False, 'error': 'No company access found'})
        
        # Extract parameters
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        department_ids = data.get('departments', [])
        employee_ids = data.get('employees', [])
        device_ids = data.get('devices', [])
        regenerate_existing = data.get('regenerate_existing', False)
        min_work_hours = float(data.get('min_work_hours', 0))
        punch_matching_strategy = data.get('punch_matching_strategy', 'first_last')
        break_time_minutes = int(data.get('break_time_minutes', 60))
        overtime_threshold_hours = float(data.get('overtime_threshold_hours', 8))
        
        # Parse dates
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Build employee filter
        employees = Employee.objects.filter(company=company, is_active=True)
        if department_ids:
            employees = employees.filter(department_id__in=department_ids)
        if employee_ids:
            employees = employees.filter(id__in=employee_ids)
        
        # Get attendance logs
        logs_query = AttendanceLog.objects.filter(
            employee__company=company,
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date,
            employee__in=employees
        )
        
        if device_ids:
            logs_query = logs_query.filter(device_id__in=device_ids)
        
        logs = logs_query.select_related('employee', 'device').order_by('employee', 'timestamp__date', 'timestamp')
        
        # Preview generation logic
        preview_data = []
        processed_combinations = set()
        
        current_employee = None
        current_date = None
        daily_logs = []
        
        for log in logs:
            log_date = log.timestamp.date()
            
            # Process previous day's logs when we move to new employee/date
            if (current_employee != log.employee or current_date != log_date) and daily_logs:
                result = preview_daily_attendance(
                    current_employee, current_date, daily_logs, 
                    regenerate_existing, min_work_hours, punch_matching_strategy,
                    break_time_minutes, overtime_threshold_hours
                )
                if result:
                    preview_data.append(result)
                    processed_combinations.add((current_employee.id, current_date))
                daily_logs = []
            
            current_employee = log.employee
            current_date = log_date
            daily_logs.append(log)
        
        # Process the last group
        if daily_logs:
            result = preview_daily_attendance(
                current_employee, current_date, daily_logs,
                regenerate_existing, min_work_hours, punch_matching_strategy,
                break_time_minutes, overtime_threshold_hours
            )
            if result:
                preview_data.append(result)
        
        # Sort by date and employee
        preview_data.sort(key=lambda x: (x['date'], x['employee_name']))
        
        # Calculate summary statistics
        summary = {
            'total_records': len(preview_data),
            'employees_affected': len(set(item['employee_id'] for item in preview_data)),
            'date_range': f"{start_date} to {end_date}",
            'new_records': len([item for item in preview_data if item['action'] == 'create']),
            'updated_records': len([item for item in preview_data if item['action'] == 'update']),
            'present_days': len([item for item in preview_data if item['status'] == 'P']),
            'absent_days': len([item for item in preview_data if item['status'] == 'A']),
            'total_work_hours': sum(item['work_hours'] for item in preview_data),
            'total_overtime_hours': sum(item['overtime_hours'] for item in preview_data),
        }
        
        return JsonResponse({
            'success': True,
            'preview_data': preview_data[:100],  # Limit for performance
            'summary': summary,
            'has_more': len(preview_data) > 100
        })
        
    except Exception as e:
        logger.error(f"Error in attendance generation preview: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

def preview_daily_attendance(employee, date, logs, regenerate_existing, min_work_hours, 
                           punch_matching_strategy, break_time_minutes, overtime_threshold_hours):
    """Preview what will happen for a single employee-date combination"""
    try:
        # Check if attendance record already exists
        existing_attendance = Attendance.objects.filter(employee=employee, date=date).first()
        
        if existing_attendance and not regenerate_existing:
            return None  # Skip existing records
        
        # Sort logs by timestamp
        logs.sort(key=lambda x: x.timestamp)
        
        # Apply punch matching strategy
        check_in_time = None
        check_out_time = None
        
        if punch_matching_strategy == 'first_last':
            # First punch as check-in, last as check-out
            check_in_time = logs[0].timestamp if logs else None
            check_out_time = logs[-1].timestamp if len(logs) > 1 else None
        elif punch_matching_strategy == 'first_two':
            # First two punches (in-out pattern)
            check_in_time = logs[0].timestamp if len(logs) >= 1 else None
            check_out_time = logs[1].timestamp if len(logs) >= 2 else None
        elif punch_matching_strategy == 'smart_pairing':
            # Smart pairing based on time gaps
            if logs:
                check_in_time = logs[0].timestamp
                if len(logs) > 1:
                    # Find the last punch that's at least 4 hours after check-in
                    for log in reversed(logs):
                        if (log.timestamp - check_in_time).total_seconds() >= 4 * 3600:
                            check_out_time = log.timestamp
                            break
                    if not check_out_time and len(logs) > 1:
                        check_out_time = logs[-1].timestamp
        
        # Calculate work hours
        work_hours = 0
        if check_in_time and check_out_time:
            delta = check_out_time - check_in_time
            work_hours = round(delta.total_seconds() / 3600, 2)
            # Subtract break time
            work_hours = max(0, work_hours - (break_time_minutes / 60))
        
        # Determine status
        status = 'P' if work_hours >= min_work_hours else 'A'
        if not check_in_time:
            status = 'A'
        
        # Calculate overtime
        overtime_hours = max(0, work_hours - overtime_threshold_hours) if work_hours > overtime_threshold_hours else 0
        
        return {
            'employee_id': employee.id,
            'employee_name': employee.name,
            'employee_code': employee.employee_id,
            'department': employee.department.name if employee.department else 'N/A',
            'date': date.isoformat(),
            'check_in_time': check_in_time.strftime('%H:%M:%S') if check_in_time else None,
            'check_out_time': check_out_time.strftime('%H:%M:%S') if check_out_time else None,
            'work_hours': work_hours,
            'overtime_hours': round(overtime_hours, 2),
            'status': status,
            'punches_count': len(logs),
            'action': 'update' if existing_attendance else 'create',
            'existing_record': bool(existing_attendance)
        }
        
    except Exception as e:
        logger.error(f"Error previewing daily attendance for {employee.employee_id} on {date}: {str(e)}")
        return None

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def generate_attendance_records(request):
    """Generate attendance records with enhanced options and controls"""
    try:
        data = json.loads(request.body)
        company = get_company_from_request(request)
        if not company:
            return JsonResponse({'success': False, 'error': 'No company access found'})
        
        # Extract parameters with defaults
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        department_ids = data.get('departments', [])
        employee_ids = data.get('employees', [])
        device_ids = data.get('devices', [])
        regenerate_existing = data.get('regenerate_existing', False)
        min_work_hours = float(data.get('min_work_hours', 0))
        punch_matching_strategy = data.get('punch_matching_strategy', 'first_last')
        break_time_minutes = int(data.get('break_time_minutes', 60))
        overtime_threshold_hours = float(data.get('overtime_threshold_hours', 8))
        consider_holidays = data.get('consider_holidays', True)
        consider_leaves = data.get('consider_leaves', True)
        
        if not start_date_str or not end_date_str:
            return JsonResponse({'success': False, 'error': 'Start date and end date are required'})
        
        # Parse dates
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Validate date range
        if end_date < start_date:
            return JsonResponse({'success': False, 'error': 'End date must be after start date'})
        
        if (end_date - start_date).days > 90:
            return JsonResponse({'success': False, 'error': 'Date range cannot exceed 90 days'})
        
        # Build employee filter
        employees = Employee.objects.filter(company=company, is_active=True)
        if department_ids:
            employees = employees.filter(department_id__in=department_ids)
        if employee_ids:
            employees = employees.filter(id__in=employee_ids)
        
        # Get attendance logs
        logs_query = AttendanceLog.objects.filter(
            employee__company=company,
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date,
            employee__in=employees
        )
        
        if device_ids:
            logs_query = logs_query.filter(device_id__in=device_ids)
        
        logs = logs_query.select_related('employee', 'device').order_by('employee', 'timestamp__date', 'timestamp')
        
        # Get holidays and leaves if considering them
        holidays = set()
        employee_leaves = {}
        
        if consider_holidays:
            company_holidays = Holiday.objects.filter(
                company=company,
                date__gte=start_date,
                date__lte=end_date
            ).values_list('date', flat=True)
            holidays = set(company_holidays)
        
        if consider_leaves:
            approved_leaves = LeaveApplication.objects.filter(
                employee__company=company,
                status='A',
                start_date__lte=end_date,
                end_date__gte=start_date
            ).select_related('employee')
            
            for leave in approved_leaves:
                if leave.employee.id not in employee_leaves:
                    employee_leaves[leave.employee.id] = set()
                
                # Add all leave dates
                current_date = max(leave.start_date, start_date)
                end_leave_date = min(leave.end_date, end_date)
                
                while current_date <= end_leave_date:
                    employee_leaves[leave.employee.id].add(current_date)
                    current_date += timedelta(days=1)
        
        # Process logs and generate attendance records
        generated_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        current_employee = None
        current_date = None
        daily_logs = []
        
        with transaction.atomic():
            for log in logs:
                log_date = log.timestamp.date()
                
                # Process previous day's logs when we move to new employee/date
                if (current_employee != log.employee or current_date != log_date) and daily_logs:
                    result = process_daily_attendance_enhanced(
                        current_employee, current_date, daily_logs,
                        regenerate_existing, min_work_hours, punch_matching_strategy,
                        break_time_minutes, overtime_threshold_hours,
                        holidays, employee_leaves.get(current_employee.id, set())
                    )
                    if result == 'created':
                        generated_count += 1
                    elif result == 'updated':
                        updated_count += 1
                    elif result == 'skipped':
                        skipped_count += 1
                    elif result == 'error':
                        error_count += 1
                    
                    daily_logs = []
                
                current_employee = log.employee
                current_date = log_date
                daily_logs.append(log)
            
            # Process the last group
            if daily_logs:
                result = process_daily_attendance_enhanced(
                    current_employee, current_date, daily_logs,
                    regenerate_existing, min_work_hours, punch_matching_strategy,
                    break_time_minutes, overtime_threshold_hours,
                    holidays, employee_leaves.get(current_employee.id, set())
                )
                if result == 'created':
                    generated_count += 1
                elif result == 'updated':
                    updated_count += 1
                elif result == 'skipped':
                    skipped_count += 1
                elif result == 'error':
                    error_count += 1
        
        return JsonResponse({
            'success': True,
            'generated_count': generated_count,
            'updated_count': updated_count,
            'skipped_count': skipped_count,
            'error_count': error_count,
            'total_processed': generated_count + updated_count + skipped_count,
            'message': f'Processing completed: {generated_count} created, {updated_count} updated, {skipped_count} skipped, {error_count} errors.'
        })
        
    except Exception as e:
        logger.error(f"Error generating attendance records: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

def process_daily_attendance_enhanced(employee, date, logs, regenerate_existing, min_work_hours,
                                   punch_matching_strategy, break_time_minutes, overtime_threshold_hours,
                                   holidays, employee_leaves):
    """Enhanced daily attendance processing with comprehensive options"""
    try:
        # Check if this date is a holiday
        is_holiday = date in holidays
        is_on_leave = date in employee_leaves
        
        # Check if attendance record already exists
        existing_attendance = Attendance.objects.filter(employee=employee, date=date).first()
        
        if existing_attendance and not regenerate_existing:
            return 'skipped'
        
        # Sort logs by timestamp
        logs.sort(key=lambda x: x.timestamp)
        
        # Apply punch matching strategy
        check_in_time = None
        check_out_time = None
        
        if punch_matching_strategy == 'first_last':
            check_in_time = logs[0].timestamp if logs else None
            check_out_time = logs[-1].timestamp if len(logs) > 1 else None
        elif punch_matching_strategy == 'first_two':
            check_in_time = logs[0].timestamp if len(logs) >= 1 else None
            check_out_time = logs[1].timestamp if len(logs) >= 2 else None
        elif punch_matching_strategy == 'smart_pairing':
            if logs:
                check_in_time = logs[0].timestamp
                if len(logs) > 1:
                    for log in reversed(logs):
                        if (log.timestamp - check_in_time).total_seconds() >= 4 * 3600:
                            check_out_time = log.timestamp
                            break
                    if not check_out_time and len(logs) > 1:
                        check_out_time = logs[-1].timestamp
        
        # Calculate work hours
        work_hours = 0
        if check_in_time and check_out_time:
            delta = check_out_time - check_in_time
            work_hours = round(delta.total_seconds() / 3600, 2)
            work_hours = max(0, work_hours - (break_time_minutes / 60))
        
        # Determine status based on conditions
        if is_holiday:
            status = 'H'
        elif is_on_leave:
            status = 'L'
        elif work_hours >= min_work_hours:
            status = 'P'
        elif check_in_time:
            status = 'P'  # Present but insufficient hours
        else:
            status = 'A'
        
        # Calculate overtime
        overtime_hours = 0
        if work_hours > overtime_threshold_hours and status == 'P':
            overtime_hours = round(work_hours - overtime_threshold_hours, 2)
        
        # Get employee's shift
        shift = employee.default_shift
        
        # Create or update attendance record
        attendance_data = {
            'employee': employee,
            'shift': shift,
            'date': date,
            'check_in_time': check_in_time,
            'check_out_time': check_out_time,
            'status': status,
            'overtime_hours': overtime_hours
        }
        
        if existing_attendance:
            # Update existing record
            for field, value in attendance_data.items():
                setattr(existing_attendance, field, value)
            existing_attendance.save()
            return 'updated'
        else:
            # Create new record
            Attendance.objects.create(**attendance_data)
            return 'created'
            
    except Exception as e:
        logger.error(f"Error processing daily attendance for {employee.employee_id} on {date}: {str(e)}")
        return 'error'