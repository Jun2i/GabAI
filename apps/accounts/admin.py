from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, AuditLog
from apps.patients.models import PatientProfile
from apps.physicians.models import PhysicianProfile, HealthcareStaff, ClinicalRecord, FollowUp
from apps.assessments.models import QuestionnaireCategory, Question, Assessment, PatientResponse, ScreeningResult
from apps.safety.models import SafetyAssessment
from apps.ai_engine.models import AiAnalysis
from apps.recommendations.models import AiRecommendation, RecommendationVersion, PhysicianApproval
from apps.wellness.models import WellnessSchedule, WellnessActivity, ActivityProgress
from apps.appointments.models import Appointment
from apps.notifications.models import Notification
from apps.reports.models import GeneratedReport

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_verified', 'consent_given')
    list_filter = ('role', 'is_verified', 'consent_given')
    fieldsets = UserAdmin.fieldsets + (
        ('GabAI Profile', {'fields': ('role', 'phone_number', 'is_verified', 'consent_given', 'consent_date')}),
    )

@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_of_birth', 'gender', 'assigned_physician', 'has_active_safety_alert')
    list_filter = ('gender', 'has_active_safety_alert')

@admin.register(PhysicianProfile)
class PhysicianProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'license_number', 'specialization', 'hospital_affiliation', 'is_verified')
    list_filter = ('is_verified', 'specialization')

@admin.register(HealthcareStaff)
class HealthcareStaffAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'staff_id')

@admin.register(QuestionnaireCategory)
class QuestionnaireCategoryAdmin(admin.ModelAdmin):
    list_display = ('category_order', 'name', 'code', 'is_developmental', 'is_critical_safety')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('order', 'category', 'question_text', 'question_type', 'is_critical_safety')
    list_filter = ('category', 'question_type', 'is_critical_safety')

@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'status', 'phq9_score', 'gad7_score', 'has_safety_flag', 'created_at')
    list_filter = ('status', 'has_safety_flag')

@admin.register(SafetyAssessment)
class SafetyAssessmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'urgency_level', 'status', 'created_at')
    list_filter = ('urgency_level', 'status')

@admin.register(AiAnalysis)
class AiAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'assessment', 'analysis_pathway', 'safety_concerns_flagged', 'created_at')

@admin.register(AiRecommendation)
class AiRecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'pathway', 'status', 'current_version', 'is_visible_to_patient', 'created_at')
    list_filter = ('status', 'pathway', 'is_visible_to_patient')

@admin.register(RecommendationVersion)
class RecommendationVersionAdmin(admin.ModelAdmin):
    list_display = ('recommendation', 'version_number', 'modification_type', 'modified_by', 'created_at')

@admin.register(PhysicianApproval)
class PhysicianApprovalAdmin(admin.ModelAdmin):
    list_display = ('recommendation', 'physician', 'decision', 'reviewed_at')
    list_filter = ('decision',)

@admin.register(WellnessSchedule)
class WellnessScheduleAdmin(admin.ModelAdmin):
    list_display = ('title', 'patient', 'status', 'is_physician_approved', 'start_date')

@admin.register(WellnessActivity)
class WellnessActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'patient', 'category', 'status', 'scheduled_date', 'start_time')
    list_filter = ('status', 'category')

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'physician', 'appointment_date', 'start_time', 'status')
    list_filter = ('status', 'appointment_type')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'notification_type', 'title', 'is_read', 'is_urgent')

@admin.register(ClinicalRecord)
class ClinicalRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'physician', 'clinical_diagnosis', 'created_at')

@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'physician', 'scheduled_date', 'status')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'entity_name', 'entity_id')
    list_filter = ('action',)

