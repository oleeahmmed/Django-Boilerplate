from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import logging
from django.utils.dateparse import parse_datetime

# Import Company model from custom_auth app
from core.models import Company

try:
    from zk import ZK
    from zk.exception import ZKNetworkError, ZKErrorResponse
    ZK_AVAILABLE = True
except ImportError:
    ZK_AVAILABLE = False
    logging.warning("ZK library not available. Please install it with 'pip install pyzk'")

logger = logging.getLogger(__name__)

# ==================== EMPLOYEE INFORMATION ====================

class Department(models.Model):
    """
    প্রতিষ্ঠানের একটি বিভাগকে উপস্থাপন করে।
    এখন Company মডেলের সাথে ForeignKey সম্পর্ক রয়েছে।
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name=_("Company"))
    name = models.CharField(_("Name"), max_length=100)
    code = models.CharField(_("Code"), max_length=20)
    description = models.TextField(_("Description"), blank=True, null=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.company.name}"

    class Meta:
        verbose_name = _("Department")
        verbose_name_plural = _("Departments")
        unique_together = ('company', 'code')
        ordering = ['name']

class Designation(models.Model):
    """
    একটি বিভাগের মধ্যে একটি কাজের পদকে উপস্থাপন করে।
    এখন Company এবং Department এর সাথে ForeignKey সম্পর্ক রয়েছে।
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name=_("Company"))
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name=_("Department"), blank=True, null=True)
    name = models.CharField(_("Name"), max_length=100)
    code = models.CharField(_("Code"), max_length=20)
    description = models.TextField(_("Description"), blank=True, null=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.company.name}"

    class Meta:
        verbose_name = _("Designation")
        verbose_name_plural = _("Designations")
        unique_together = ('company', 'code')
        ordering = ['name']

class Employee(models.Model):
    """
    প্রতিষ্ঠানের একজন কর্মচারীকে উপস্থাপন করে।
    Simplified to include only requested fields: employee_id, zkteco_id, name, department, designation, default_shift, expected_working_hours, overtime_grace_minutes, company, is_active, created_at, updated_at.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name=_("Company"))
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name=_("Department"))
    designation = models.ForeignKey(Designation, on_delete=models.CASCADE, verbose_name=_("Designation"))
    default_shift = models.ForeignKey('ShiftType', on_delete=models.SET_NULL, verbose_name=_("Default Shift"), null=True, blank=True)
    employee_id = models.CharField(_("Employee ID"), max_length=20, unique=True)
    zkteco_id = models.CharField(_("ZKTeco ID"), max_length=100, blank=True, null=True, help_text="ZKTeco Device User ID")
    name = models.CharField(_("Name"), max_length=100)
    expected_working_hours = models.DecimalField(_("Expected Working Hours"), max_digits=5, decimal_places=2, default=8.00)
    overtime_grace_minutes = models.IntegerField(_("Overtime Grace Minutes"), default=15)
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    def __str__(self):
        return f"{self.employee_id} - {self.name}"

    class Meta:
        verbose_name = _("Employee")
        verbose_name_plural = _("Employees")
        ordering = ['employee_id']
        indexes = [
            models.Index(fields=['zkteco_id']),
            models.Index(fields=['employee_id']),
        ]


class EmployeeSeparation(models.Model):
    """
    কর্মচারীর চাকরি শেষ হওয়ার তথ্য সংরক্ষণ করে।
    """
    SEPARATION_TYPE_CHOICES = (
        ('resignation', 'Resignation'),
        ('termination', 'Termination'),
        ('retirement', 'Retirement'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_("Employee"))
    separation_type = models.CharField(_("Separation Type"), max_length=20, choices=SEPARATION_TYPE_CHOICES)
    separation_date = models.DateField(_("Separation Date"))
    reason = models.TextField(_("Reason"), blank=True, null=True)
    clearance_completed = models.BooleanField(_("Clearance Completed"), default=False)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    def __str__(self):
        return f"{self.employee.employee_id} - {self.separation_type}"

    class Meta:
        verbose_name = _("Employee Separation")
        verbose_name_plural = _("Employee Separations")
        ordering = ['-separation_date']

class ShiftType(models.Model):
    """
    শিফটের ধরন সংরক্ষণ করে।
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name=_("Company"))
    name = models.CharField(_("Name"), max_length=100)
    code = models.CharField(_("Code"), max_length=20)
    start_time = models.TimeField(_("Start Time"))
    end_time = models.TimeField(_("End Time"))
    description = models.TextField(_("Description"), blank=True, null=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.company.name}"

    class Meta:
        verbose_name = _("Shift Type")
        verbose_name_plural = _("Shift Types")
        unique_together = ('company', 'code')
        ordering = ['name']

class Shift(models.Model):
    """
    নির্দিষ্ট দিনের জন্য শিফট সংরক্ষণ করে।
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name=_("Company"))
    shift_type = models.ForeignKey(ShiftType, on_delete=models.CASCADE, verbose_name=_("Shift Type"))
    date = models.DateField(_("Date"))
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    def __str__(self):
        return f"{self.shift_type.name} - {self.date}"

    class Meta:
        verbose_name = _("Shift")
        verbose_name_plural = _("Shifts")
        unique_together = ('company', 'shift_type', 'date')
        ordering = ['-date']

class Roster(models.Model):
    """
    কর্মচারীদের জন্য শিফট রোস্টার সংরক্ষণ করে।
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name=_("Company"))
    name = models.CharField(_("Name"), max_length=100)
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"))
    description = models.TextField(_("Description"), blank=True, null=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"

    class Meta:
        verbose_name = _("Roster")
        verbose_name_plural = _("Rosters")
        ordering = ['-start_date']

class RosterAssignment(models.Model):
    """
    কর্মচারীদের শিফট এবং রোস্টারের সাথে সংযুক্ত করে।
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_("Employee"))
    roster = models.ForeignKey(Roster, on_delete=models.CASCADE, verbose_name=_("Roster"))
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, verbose_name=_("Shift"))
    date = models.DateField(_("Date"))
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    def __str__(self):
        return f"{self.employee.employee_id} - {self.roster.name} - {self.date}"

    class Meta:
        verbose_name = _("Roster Assignment")
        verbose_name_plural = _("Roster Assignments")
        unique_together = ('employee', 'roster', 'date')
        ordering = ['-date']

class Holiday(models.Model):
    """
    প্রতিষ্ঠানের ছুটির দিন সংরক্ষণ করে।
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name=_("Company"))
    name = models.CharField(_("Name"), max_length=100)
    date = models.DateField(_("Date"))
    description = models.TextField(_("Description"), blank=True, null=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.date}"

    class Meta:
        verbose_name = _("Holiday")
        verbose_name_plural = _("Holidays")
        unique_together = ('company', 'date')
        ordering = ['-date']

class LeaveType(models.Model):
    """
    ছুটির ধরন সংরক্ষণ করে।
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name=_("Company"))
    name = models.CharField(_("Name"), max_length=100)
    code = models.CharField(_("Code"), max_length=20)
    paid = models.BooleanField(_("Paid Leave"), default=True)
    max_days = models.IntegerField(_("Maximum Days"), default=0)
    description = models.TextField(_("Description"), blank=True, null=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.company.name}"

    class Meta:
        verbose_name = _("Leave Type")
        verbose_name_plural = _("Leave Types")
        unique_together = ('company', 'code')
        ordering = ['name']

class LeaveBalance(models.Model):
    """
    কর্মচারীদের ছুটির ব্যালেন্স সংরক্ষণ করে।
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_("Employee"))
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, verbose_name=_("Leave Type"))
    entitled_days = models.IntegerField(_("Entitled Days"), default=0)
    used_days = models.IntegerField(_("Used Days"), default=0)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    @property
    def remaining_days(self):
        return self.entitled_days - self.used_days

    def __str__(self):
        return f"{self.employee.employee_id} - {self.leave_type.name}"

    class Meta:
        verbose_name = _("Leave Balance")
        verbose_name_plural = _("Leave Balances")
        unique_together = ('employee', 'leave_type')
        ordering = ['-created_at']

class LeaveApplication(models.Model):
    """
    কর্মচারীদের ছুটির আবেদন সংরক্ষণ করে।
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_("Employee"))
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, verbose_name=_("Leave Type"))
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"))
    reason = models.TextField(_("Reason"), blank=True, null=True)
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, verbose_name=_("Approved By"), null=True, blank=True, related_name='approved_leaves')
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    def __str__(self):
        return f"{self.employee.employee_id} - {self.start_date} to {self.end_date}"

    class Meta:
        verbose_name = _("Leave Application")
        verbose_name_plural = _("Leave Applications")
        ordering = ['-created_at']

class ZkDevice(models.Model):
    """
    ZK Teco বায়োমেট্রিক ডিভাইসের তথ্য সংরক্ষণ করে।
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name=_("Company"))
    name = models.CharField(_("Name"), max_length=100)
    ip_address = models.GenericIPAddressField(_("IP Address"))
    port = models.IntegerField(_("Port"), default=4370)
    password = models.CharField(_("Password"), max_length=50, null=True, blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)
    description = models.TextField(_("Description"), blank=True, null=True)
    last_synced = models.DateTimeField(_("Last Synced"), null=True, blank=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.ip_address})"

    class Meta:
        verbose_name = _("ZK Device")
        verbose_name_plural = _("ZK Devices")
        ordering = ['name']
        unique_together = ('company', 'ip_address', 'port')
        indexes = [
            models.Index(fields=['ip_address', 'port']),
        ]

class AttendanceLog(models.Model):
    """
    বায়োমেট্রিক ডিভাইসের Raw ডেটা সংরক্ষণ করে।
   এখন Employee এবং ZkDevice এর সাথে ForeignKey সম্পর্ক রয়েছে।
    """
    SOURCE_TYPE_CHOICES = (
        ('device', 'Device'),
        ('manual', 'Manual'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_("Employee"))
    device = models.ForeignKey(ZkDevice, on_delete=models.CASCADE, verbose_name=_("Device"), blank=True, null=True)
    timestamp = models.DateTimeField(_("Timestamp"))
    source_type = models.CharField(_("Source Type"), max_length=10, choices=SOURCE_TYPE_CHOICES, default='device')
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    def __str__(self):
        return f"{self.employee.employee_id} - {self.timestamp}"

    class Meta:
        verbose_name = _("Attendance Log")
        verbose_name_plural = _("Attendance Logs")
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['employee', 'timestamp']),
            models.Index(fields=['device', 'timestamp']),
        ]

class Attendance(models.Model):
    """
    প্রতিটি কর্মচারীর জন্য দৈনিক উপস্থিতি রেকর্ড সংরক্ষণ করে।
    এখন Employee এবং Shift এর সাথে ForeignKey সম্পর্ক রয়েছে।
    """
    STATUS_CHOICES = (
        ('A', 'Absent'),
        ('P', 'Present'),
        ('W', 'Weekly Off'),
        ('H', 'Holiday'),
        ('L', 'Leave'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_("Employee"))
    shift = models.ForeignKey(Shift, on_delete=models.SET_NULL, verbose_name=_("Shift"), blank=True, null=True)
    date = models.DateField(_("Date"))
    check_in_time = models.DateTimeField(_("Check In Time"), null=True, blank=True)
    check_out_time = models.DateTimeField(_("Check Out Time"), null=True, blank=True)
    status = models.CharField(_("Status"), max_length=10, choices=STATUS_CHOICES, default='A')
    overtime_hours = models.DecimalField(_("Overtime Hours"), max_digits=5, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    def __str__(self):
        return f"{self.employee.employee_id} on {self.date}"

    @property
    def work_hours(self):
        """কাজের মোট সময় (ঘণ্টা) গণনা করে।"""
        if self.check_in_time and self.check_out_time:
            delta = self.check_out_time - self.check_in_time
            return round(delta.total_seconds() / 3600, 2)
        return 0

    class Meta:
        verbose_name = _("Attendance")
        verbose_name_plural = _("Attendance")
        unique_together = ('employee', 'date')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date']),
        ]
