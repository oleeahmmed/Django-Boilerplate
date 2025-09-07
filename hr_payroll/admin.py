from django.contrib import admin
from unfold.admin import ModelAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib import messages

from .models import (
    Department, Designation, ShiftType, Shift, Employee,
    EmployeeSeparation, Roster, RosterAssignment, Holiday,
    LeaveType, LeaveBalance, LeaveApplication, ZkDevice,
    AttendanceLog, Attendance
)

class RosterAssignmentInline(admin.TabularInline):
    model = RosterAssignment
    extra = 1
    fields = ('employee', 'shift', 'date')
    autocomplete_fields = ['employee', 'shift']

class LeaveBalanceInline(admin.TabularInline):
    model = LeaveBalance
    extra = 1
    fields = ('leave_type', 'entitled_days', 'used_days', 'remaining_days')
    readonly_fields = ('remaining_days',)
    autocomplete_fields = ['leave_type']

class LeaveApplicationInline(admin.TabularInline):
    model = LeaveApplication
    extra = 1
    fields = ('leave_type', 'start_date', 'end_date', 'status', 'reason')
    autocomplete_fields = ['leave_type', 'approved_by']
    fk_name = 'employee'

@admin.register(Department)
class DepartmentAdmin(ModelAdmin):
    list_display = ('name', 'code', 'company', 'created_at')
    list_filter = ('company',)
    search_fields = ('name', 'code')
    ordering = ('name',)

@admin.register(Designation)
class DesignationAdmin(ModelAdmin):
    list_display = ('name', 'code', 'company', 'department', 'created_at')
    list_filter = ('company', 'department')
    search_fields = ('name', 'code')
    ordering = ('name',)

@admin.register(ShiftType)
class ShiftTypeAdmin(ModelAdmin):
    list_display = ('name', 'code', 'company', 'start_time', 'end_time')
    list_filter = ('company',)
    search_fields = ('name', 'code')
    ordering = ('name',)

@admin.register(Shift)
class ShiftAdmin(ModelAdmin):
    list_display = ('shift_type', 'date', 'company')
    list_filter = ('company', 'shift_type')
    search_fields = ('shift_type__name',)
    ordering = ('-date',)

@admin.register(Employee)
class EmployeeAdmin(ModelAdmin):
    list_display = ('employee_id', 'name', 'company', 'department', 'designation', 'default_shift', 'is_active', 'created_at')
    list_filter = ('company', 'department', 'designation', 'is_active', 'created_at')
    search_fields = ('employee_id', 'name', 'zkteco_id')
    ordering = ('-created_at', 'employee_id')
    inlines = [LeaveBalanceInline, LeaveApplicationInline]
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'employee_id',
                'zkteco_id',
                'name',
            ),
            'classes': ('wide',)
        }),
        ('Company & Position', {
            'fields': (
                'company',
                'department', 'designation', 'default_shift',
                'is_active'
            ),
            'classes': ('wide',)
        }),
        ('Work Configuration', {
            'fields': (
                'expected_working_hours', 'overtime_grace_minutes'
            ),
            'classes': ('collapse', 'wide')
        }),
        ('System Information', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ['created_at', 'updated_at']

@admin.register(EmployeeSeparation)
class EmployeeSeparationAdmin(ModelAdmin):
    list_display = ('employee', 'separation_type', 'separation_date', 'clearance_completed', 'created_at')
    list_filter = ('separation_type', 'clearance_completed', 'created_at')
    search_fields = ('employee__employee_id', 'employee__name')
    ordering = ('-created_at',)

@admin.register(Roster)
class RosterAdmin(ModelAdmin):
    list_display = ('name', 'company', 'start_date', 'end_date', 'created_at')
    list_filter = ('company', 'start_date', 'end_date')
    search_fields = ('name',)
    ordering = ('-start_date',)
    inlines = [RosterAssignmentInline]

@admin.register(RosterAssignment)
class RosterAssignmentAdmin(ModelAdmin):
    list_display = ('employee', 'roster', 'shift', 'date', 'created_at')
    list_filter = ('roster', 'shift', 'date')
    search_fields = ('employee__employee_id', 'employee__name', 'roster__name')
    ordering = ('-date',)

@admin.register(Holiday)
class HolidayAdmin(ModelAdmin):
    list_display = ('name', 'company', 'date', 'created_at')
    list_filter = ('company', 'date')
    search_fields = ('name',)
    ordering = ('-date',)

@admin.register(LeaveType)
class LeaveTypeAdmin(ModelAdmin):
    list_display = ('name', 'code', 'company', 'paid', 'max_days', 'created_at')
    list_filter = ('company', 'paid', 'created_at')
    search_fields = ('name', 'code')
    ordering = ('name',)

@admin.register(LeaveBalance)
class LeaveBalanceAdmin(ModelAdmin):
    list_display = ('employee', 'leave_type', 'entitled_days', 'used_days', 'remaining_days', 'created_at')
    list_filter = ('leave_type', 'created_at')
    search_fields = ('employee__employee_id', 'employee__name', 'leave_type__name')
    ordering = ('-created_at',)

@admin.register(LeaveApplication)
class LeaveApplicationAdmin(ModelAdmin):
    list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'status', 'created_at')
    list_filter = ('leave_type', 'status', 'start_date', 'end_date')
    search_fields = ('employee__employee_id', 'employee__name', 'leave_type__name')
    ordering = ('-created_at',)

@admin.register(ZkDevice)
class ZkDeviceAdmin(ModelAdmin):
    list_display = ('name', 'company', 'ip_address', 'port', 'is_active', 'last_synced', 'created_at')
    list_filter = ('company', 'is_active', 'last_synced')
    search_fields = ('name', 'ip_address')
    ordering = ('name',)
    
    fieldsets = (
        ('Device Information', {
            'fields': ('name', 'company', 'description')
        }),
        ('Connection Settings', {
            'fields': ('ip_address', 'port', 'password', 'is_active')
        }),
        ('System Information', {
            'fields': ('last_synced', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ('last_synced', 'created_at', 'updated_at')
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj:  # editing an existing object
            readonly_fields.extend(['ip_address', 'port'])
        return readonly_fields

@admin.register(AttendanceLog)
class AttendanceLogAdmin(ModelAdmin):
    list_display = ('employee', 'device', 'timestamp', 'source_type', 'created_at')
    list_filter = ('source_type', 'device', 'timestamp')
    search_fields = ('employee__employee_id', 'employee__name')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('employee', 'device')

@admin.register(Attendance)
class AttendanceAdmin(ModelAdmin):
    list_display = ('employee', 'date', 'shift', 'status', 'work_hours', 'overtime_hours', 'created_at')
    list_filter = ('status', 'date', 'shift')
    search_fields = ('employee__employee_id', 'employee__name')
    ordering = ('-date',)
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('employee', 'shift__shift_type')