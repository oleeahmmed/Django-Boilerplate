import logging
from django.utils import timezone
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.core.exceptions import ObjectDoesNotExist
from typing import List, Dict, Any, Tuple, Optional
import json

try:
    from zk import ZK
    from zk.exception import ZKNetworkError, ZKErrorResponse
    ZK_AVAILABLE = True
except ImportError:
    ZK_AVAILABLE = False
    logging.warning("ZK library not available. Please install it with 'pip install pyzk'")

from .models import ZkDevice, Employee, AttendanceLog, Company, Department, Designation, ShiftType

logger = logging.getLogger(__name__)

class ZKTecoDeviceManager:
    """Main manager class for ZKTeco device operations"""
    
    def __init__(self):
        self.connection_timeout = 30
        self.max_retry_attempts = 3
    
    def _get_zk_connection(self, device: ZkDevice):
        """Establish connection to ZKTeco device"""
        if not ZK_AVAILABLE:
            raise Exception("ZK library not available. Please install with 'pip install pyzk'")
        
        password = int(device.password) if device.password and str(device.password).isdigit() else 0
        zk = ZK(device.ip_address, port=device.port, timeout=self.connection_timeout, 
                password=password, force_udp=True, ommit_ping=True)
        
        for attempt in range(self.max_retry_attempts):
            try:
                conn = zk.connect()
                if conn:
                    return conn
                else:
                    logger.warning(f"Connection attempt {attempt + 1} failed for device {device.name}")
            except (ZKNetworkError, ZKErrorResponse) as e:
                logger.warning(f"Connection attempt {attempt + 1} failed for device {device.name}: {str(e)}")
                if attempt == self.max_retry_attempts - 1:
                    raise e
        
        raise Exception("Failed to establish connection after maximum retry attempts")

class ZKTecoConnectionChecker:
    """Handle ZKTeco device connection testing"""
    
    def __init__(self):
        self.manager = ZKTecoDeviceManager()
    
    def check_single_device(self, device: ZkDevice) -> Dict[str, Any]:
        """Test connection to a single ZKTeco device"""
        if not ZK_AVAILABLE:
            return {
                'device_id': device.id,
                'device_name': device.name,
                'success': False,
                'message': 'ZK library not available. Please install with pip install pyzk',
                'details': {}
            }
        
        try:
            conn = self.manager._get_zk_connection(device)
            
            # Get device information
            device_name = conn.get_device_name()
            firmware_version = conn.get_firmware_version()
            platform = conn.get_platform()
            device_time = conn.get_time()
            
            # Get counts
            users = conn.get_users()
            attendance_logs = conn.get_attendance()
            
            conn.disconnect()
            
            # Update device last sync time
            device.last_synced = timezone.now()
            device.save(update_fields=['last_synced'])
            
            return {
                'device_id': device.id,
                'device_name': device.name,
                'success': True,
                'message': 'Connected successfully',
                'details': {
                    'device_name': device_name,
                    'firmware_version': firmware_version,
                    'platform': platform,
                    'device_time': device_time.isoformat() if device_time else None,
                    'total_users': len(users),
                    'total_attendance': len(attendance_logs),
                }
            }
            
        except ZKNetworkError as e:
            logger.error(f"Network error for device {device.name}: {str(e)}")
            return {
                'device_id': device.id,
                'device_name': device.name,
                'success': False,
                'message': f'Network error: {str(e)}',
                'details': {}
            }
        except ZKErrorResponse as e:
            logger.error(f"ZK error for device {device.name}: {str(e)}")
            return {
                'device_id': device.id,
                'device_name': device.name,
                'success': False,
                'message': f'ZK device error: {str(e)}',
                'details': {}
            }
        except Exception as e:
            logger.error(f"Unexpected error for device {device.name}: {str(e)}")
            return {
                'device_id': device.id,
                'device_name': device.name,
                'success': False,
                'message': f'Connection failed: {str(e)}',
                'details': {}
            }
    
    def check_multiple_devices(self, devices: List[ZkDevice]) -> List[Dict[str, Any]]:
        """Test connection to multiple ZKTeco devices"""
        results = []
        for device in devices:
            result = self.check_single_device(device)
            results.append(result)
        return results

class ZKTecoEmployeeImporter:
    """Handle employee import from ZKTeco devices"""
    
    def __init__(self):
        self.manager = ZKTecoDeviceManager()
    
    def import_from_single_device(self, device: ZkDevice) -> Dict[str, Any]:
        """Import employees from a single ZKTeco device"""
        if not ZK_AVAILABLE:
            raise Exception("ZK library not available. Please install with 'pip install pyzk'")
        
        imported_count = 0
        updated_count = 0
        error_count = 0
        errors = []
        
        try:
            conn = self.manager._get_zk_connection(device)
            users = conn.get_users()
            conn.disconnect()
            
            # Get default values
            default_company = device.company
            default_department = self._get_or_create_default_department(default_company)
            default_designation = self._get_or_create_default_designation(default_company)
            default_shift = self._get_default_shift(default_company)
            
            if not default_shift:
                raise Exception("No shift type found. Please create at least one shift type for the company.")
            
            with transaction.atomic():
                for user in users:
                    try:
                        # Create or update employee
                        employee, created = Employee.objects.get_or_create(
                            zkteco_id=str(user.uid),
                            defaults={
                                'company': default_company,
                                'department': default_department,
                                'designation': default_designation,
                                'default_shift': default_shift,
                                'employee_id': user.user_id or f"EMP{user.uid}",
                                'name': user.name or f"User {user.uid}",
                                'expected_working_hours': 8.0,
                                'overtime_grace_minutes': 15,
                                'is_active': True
                            }
                        )
                        
                        if created:
                            imported_count += 1
                            logger.info(f"Created employee: {employee.name} (ZK ID: {user.uid})")
                        else:
                            # Update existing employee
                            updated_fields = []
                            if user.name and employee.name != user.name:
                                employee.name = user.name
                                updated_fields.append('name')
                            if user.user_id and employee.employee_id != user.user_id:
                                employee.employee_id = user.user_id
                                updated_fields.append('employee_id')
                            if not employee.is_active:
                                employee.is_active = True
                                updated_fields.append('is_active')
                            
                            if updated_fields:
                                employee.save(update_fields=updated_fields + ['updated_at'])
                                updated_count += 1
                                logger.info(f"Updated employee: {employee.name} (ZK ID: {user.uid})")
                            
                    except Exception as e:
                        error_message = f"Error processing user {user.uid}: {str(e)}"
                        logger.error(error_message)
                        errors.append(error_message)
                        error_count += 1
                        continue
            
            return {
                'device_id': device.id,
                'device_name': device.name,
                'imported_count': imported_count,
                'updated_count': updated_count,
                'error_count': error_count,
                'errors': errors
            }
            
        except Exception as e:
            error_message = f"Failed to import employees from {device.name}: {str(e)}"
            logger.error(error_message)
            raise Exception(error_message)
    
    def import_from_multiple_devices(self, devices: List[ZkDevice]) -> List[Dict[str, Any]]:
        """Import employees from multiple ZKTeco devices"""
        results = []
        for device in devices:
            try:
                result = self.import_from_single_device(device)
                results.append(result)
            except Exception as e:
                results.append({
                    'device_id': device.id,
                    'device_name': device.name,
                    'imported_count': 0,
                    'updated_count': 0,
                    'error_count': 1,
                    'errors': [str(e)]
                })
        return results
    
    def _get_or_create_default_department(self, company: Company) -> Department:
        """Get or create default department"""
        department, created = Department.objects.get_or_create(
            company=company,
            code='DEFAULT',
            defaults={
                'name': 'Default Department',
                'description': 'Default department for imported employees'
            }
        )
        return department
    
    def _get_or_create_default_designation(self, company: Company) -> Designation:
        """Get or create default designation"""
        designation, created = Designation.objects.get_or_create(
            company=company,
            code='DEFAULT',
            defaults={
                'name': 'Default Employee',
                'description': 'Default designation for imported employees'
            }
        )
        return designation
    
    def _get_default_shift(self, company: Company) -> Optional[ShiftType]:
        """Get default shift type"""
        return ShiftType.objects.filter(company=company).first()

class ZKTecoAttendanceImporter:
    """Handle attendance import from ZKTeco devices"""
    
    def __init__(self):
        self.manager = ZKTecoDeviceManager()
    
    def sync_attendance_data(self, device: ZkDevice, date_from: Optional[str] = None, date_to: Optional[str] = None) -> Tuple[bool, List[Dict], str]:
        """Sync attendance data from ZKTeco device for preview"""
        if not ZK_AVAILABLE:
            return False, [], "ZK library not available. Please install with 'pip install pyzk'"
        
        try:
            conn = self.manager._get_zk_connection(device)
            attendance_logs = conn.get_attendance()
            conn.disconnect()
            
            logger.info(f"Retrieved {len(attendance_logs)} attendance logs from {device.name}")
            
            logs_for_preview = []
            
            for log in attendance_logs:
                try:
                    # Find employee by ZKTeco ID or Employee ID
                    employee = self._find_employee_by_uid(device.company, str(log.user_id))
                    
                    log_data = {
                        'user_id': str(log.user_id),
                        'employee_id': employee.employee_id if employee else None,
                        'employee_name': employee.name if employee else "Unknown Employee",
                        'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                        'device_name': device.name,
                        'raw_timestamp': log.timestamp,
                    }
                    
                    # Check if log already exists
                    if employee and self._attendance_log_exists(employee, log.timestamp, device):
                        log_data['status'] = 'duplicate'
                        log_data['status_message'] = 'Already imported'
                    elif not employee:
                        log_data['status'] = 'error'
                        log_data['status_message'] = f'Employee not found for User ID: {log.user_id}'
                    else:
                        log_data['status'] = 'ready'
                        log_data['status_message'] = 'Ready to import'
                    
                    logs_for_preview.append(log_data)
                    
                except Exception as log_error:
                    logger.error(f"Error processing log for user {log.user_id}: {str(log_error)}")
                    logs_for_preview.append({
                        'user_id': str(log.user_id),
                        'employee_id': None,
                        'employee_name': 'Unknown Employee',
                        'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                        'device_name': device.name,
                        'status': 'error',
                        'status_message': f'Processing error: {str(log_error)}',
                        'raw_timestamp': log.timestamp,
                    })
            
            # Update device sync time
            device.last_synced = timezone.now()
            device.save(update_fields=['last_synced'])
            
            ready_count = sum(1 for log in logs_for_preview if log['status'] == 'ready')
            message = f"Found {len(logs_for_preview)} attendance logs. {ready_count} ready to import."
            
            return True, logs_for_preview, message
            
        except ZKNetworkError as e:
            error_msg = f"Network error connecting to {device.name}: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg
        except ZKErrorResponse as e:
            error_msg = f"ZKTeco device error from {device.name}: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg
        except Exception as e:
            error_msg = f"Unexpected error syncing from {device.name}: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg
    
    def import_selected_logs(self, device: ZkDevice, selected_logs: List[Dict]) -> Dict[str, Any]:
        """Import selected attendance logs"""
        imported_count = 0
        error_count = 0
        errors = []
        
        try:
            with transaction.atomic():
                for log_data in selected_logs:
                    try:
                        if log_data.get('status') != 'ready':
                            continue
                        
                        # Find employee
                        employee = Employee.objects.get(
                            company=device.company,
                            employee_id=log_data['employee_id']
                        )
                        
                        # Parse timestamp
                        if 'raw_timestamp' in log_data and log_data['raw_timestamp']:
                            timestamp = log_data['raw_timestamp']
                        else:
                            timestamp = parse_datetime(log_data['timestamp'])
                        
                        if not timestamp:
                            error_count += 1
                            errors.append(f"Invalid timestamp for employee {log_data['employee_id']}")
                            continue
                        
                        # Ensure timezone aware
                        if not timezone.is_aware(timestamp):
                            timestamp = timezone.make_aware(timestamp)
                        
                        # Check if already exists (double-check)
                        if not self._attendance_log_exists(employee, timestamp, device):
                            AttendanceLog.objects.create(
                                employee=employee,
                                timestamp=timestamp,
                                source_type='device',
                                device=device
                            )
                            imported_count += 1
                            logger.info(f"Imported attendance log for {employee.employee_id} at {timestamp}")
                        
                    except Employee.DoesNotExist:
                        error_count += 1
                        error_msg = f"Employee not found: {log_data.get('employee_id', 'Unknown')}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                    except Exception as e:
                        error_count += 1
                        error_msg = f"Error importing log for {log_data.get('employee_id', 'Unknown')}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
            
            return {
                'device_id': device.id,
                'device_name': device.name,
                'imported_count': imported_count,
                'error_count': error_count,
                'errors': errors
            }
            
        except Exception as e:
            error_msg = f"Failed to import attendance logs for {device.name}: {str(e)}"
            logger.error(error_msg)
            return {
                'device_id': device.id,
                'device_name': device.name,
                'imported_count': 0,
                'error_count': len(selected_logs),
                'errors': [error_msg]
            }
    
    def _find_employee_by_uid(self, company: Company, user_id: str) -> Optional[Employee]:
        """Find employee by ZKTeco User ID or Employee ID"""
        try:
            # First try to find by zkteco_id
            return Employee.objects.get(company=company, zkteco_id=user_id)
        except Employee.DoesNotExist:
            try:
                # Then try by employee_id
                return Employee.objects.get(company=company, employee_id=user_id)
            except Employee.DoesNotExist:
                return None
    
    def _attendance_log_exists(self, employee: Employee, timestamp, device: ZkDevice) -> bool:
        """Check if attendance log already exists"""
        return AttendanceLog.objects.filter(
            employee=employee,
            timestamp=timestamp,
            device=device
        ).exists()