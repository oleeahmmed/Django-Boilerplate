from django.contrib import admin
from unfold.admin import ModelAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib import messages

from .models import (
    Department, Designation, Shift, Employee,
    EmployeeSeparation, Roster, RosterAssignment, RosterDay,
    Holiday, LeaveType, LeaveBalance, LeaveApplication,
    ZkDevice, AttendanceLog, Attendance
)

class RosterAssignmentInline(admin.TabularInline):
    model = RosterAssignment
    extra = 1
    fields = ('employee', 'shift')
    autocomplete_fields = ['employee', 'shift']

class RosterDayInline(admin.TabularInline):
    model = RosterDay
    extra = 1
    fields = ('date', 'shift')
    autocomplete_fields = ['shift']

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

@admin.register(Shift)
class ShiftAdmin(ModelAdmin):
    list_display = ('name', 'company', 'start_time', 'end_time', 'duration')
    list_filter = ('company',)
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Employee)
class EmployeeAdmin(ModelAdmin):
    list_display = ('employee_id', 'name', 'first_name', 'last_name', 'company', 'department', 'designation', 'is_active')
    list_filter = ('company', 'department', 'designation', 'is_active')
    search_fields = ('employee_id', 'name', 'first_name', 'last_name', 'zkteco_id')
    ordering = ('employee_id',)
    inlines = [LeaveBalanceInline, LeaveApplicationInline, RosterAssignmentInline]

@admin.register(EmployeeSeparation)
class EmployeeSeparationAdmin(ModelAdmin):
    list_display = ('employee', 'separation_date', 'is_voluntary', 'created_at')
    list_filter = ('is_voluntary', 'separation_date')
    search_fields = ('employee__employee_id', 'employee__name')
    ordering = ('-separation_date',)

@admin.register(Roster)
class RosterAdmin(ModelAdmin):
    list_display = ('name', 'company', 'start_date', 'end_date', 'created_at')
    list_filter = ('company', 'start_date', 'end_date')
    search_fields = ('name',)
    ordering = ('-start_date',)
    inlines = [RosterAssignmentInline]

@admin.register(RosterAssignment)
class RosterAssignmentAdmin(ModelAdmin):
    list_display = ('roster', 'employee', 'shift', 'created_at')
    list_filter = ('roster', 'shift')
    search_fields = ('employee__employee_id', 'employee__name', 'employee__first_name', 'employee__last_name', 'roster__name')
    ordering = ('roster__name', 'employee__first_name')
    inlines = [RosterDayInline]

@admin.register(RosterDay)
class RosterDayAdmin(ModelAdmin):
    list_display = ('roster_assignment', 'date', 'shift', 'created_at')
    list_filter = ('shift', 'date')
    search_fields = ('roster_assignment__employee__employee_id', 'roster_assignment__employee__name', 'roster_assignment__employee__first_name', 'roster_assignment__employee__last_name')
    ordering = ('date',)

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
    search_fields = ('employee__employee_id', 'employee__name', 'employee__first_name', 'employee__last_name', 'leave_type__name')
    ordering = ('-created_at',)

@admin.register(LeaveApplication)
class LeaveApplicationAdmin(ModelAdmin):
    list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'status', 'created_at')
    list_filter = ('leave_type', 'status', 'start_date', 'end_date')
    search_fields = ('employee__employee_id', 'employee__name', 'employee__first_name', 'employee__last_name', 'leave_type__name')
    ordering = ('-created_at',)

@admin.register(ZkDevice)
class ZkDeviceAdmin(ModelAdmin):
    list_display = ('name', 'company', 'ip_address', 'port', 'is_active', 'last_synced', 'created_at')
    list_filter = ('company', 'is_active', 'last_synced')
    search_fields = ('name', 'ip_address')
    ordering = ('name',)

@admin.register(AttendanceLog)
class AttendanceLogAdmin(ModelAdmin):
    list_display = ('employee', 'device', 'timestamp', 'source_type', 'created_at')
    list_filter = ('source_type', 'timestamp')
    search_fields = ('employee__employee_id', 'employee__name', 'employee__first_name', 'employee__last_name')
    ordering = ('-timestamp',)

@admin.register(Attendance)
class AttendanceAdmin(ModelAdmin):
    list_display = ('employee', 'date', 'shift', 'status', 'work_hours', 'overtime_hours', 'created_at')
    list_filter = ('status', 'date', 'shift')
    search_fields = ('employee__employee_id', 'employee__name', 'employee__first_name', 'employee__last_name')
    ordering = ('-date',)