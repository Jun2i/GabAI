import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import AiRecommendation, RecommendationVersion, PhysicianApproval
from apps.wellness.models import WellnessSchedule, WellnessActivity
from apps.notifications.models import Notification
from apps.accounts.models import AuditLog
from apps.accounts.decorators import physician_required, staff_or_physician_required, patient_required
from apps.physicians.models import PhysicianProfile
from apps.ai_engine.gemini_service import generate_ai_analysis_and_recommendations
from datetime import time, timedelta, date

@login_required
@physician_required
def review_recommendation_view(request, rec_id):
    """
    Dedicated AI Recommendation Review Dashboard for Physicians.
    Displays original AI output, editable forms for modification,
    approval actions, rejection with required rationale, and audit history.
    """
    recommendation = get_object_or_404(
        AiRecommendation.objects.select_related('patient__user', 'assessment', 'approved_by__user'),
        id=rec_id
    )
    assessment = recommendation.assessment
    versions = recommendation.versions.all().order_by('-version_number')
    approval_history = recommendation.approval_reviews.select_related('physician__user').all()
    ai_analysis = getattr(assessment, 'ai_analysis', None)
    screening_results = assessment.screening_results.select_related('category').all()

    if request.method == 'POST':
        action = request.POST.get('action')
        decision_reason = request.POST.get('decision_reason', '').strip()
        instructions_for_patient = request.POST.get('instructions_for_patient', '').strip()
        physician_profile = get_object_or_404(PhysicianProfile, user=request.user)

        if action == 'APPROVE':
            recommendation.status = 'APPROVED'
            recommendation.approved_by = physician_profile
            recommendation.approved_at = timezone.now()
            recommendation.is_visible_to_patient = True
            if instructions_for_patient:
                recommendation.follow_up_guidance = instructions_for_patient
            recommendation.save()

            # Unlock patient wellness schedule
            WellnessSchedule.objects.filter(recommendation=recommendation).update(
                is_physician_approved=True,
                custom_physician_notes=instructions_for_patient
            )

            # Record approval audit
            PhysicianApproval.objects.create(
                recommendation=recommendation,
                physician=physician_profile,
                decision='APPROVED',
                reason_or_notes=decision_reason or 'Approved without clinical modifications.',
                instructions_for_patient=instructions_for_patient
            )

            # Notify patient
            Notification.send(
                recipient=recommendation.patient.user,
                notification_type='RECOMMENDATION_APPROVED',
                title="Physician-Approved Wellness Guidance Available",
                message=f"Dr. {physician_profile.user.last_name} has reviewed and approved your personalized mental wellness recommendations.",
                action_url=f"/recommendations/patient/{recommendation.id}/"
            )

            # Audit log
            AuditLog.objects.create(
                user=request.user,
                action='RECOMMENDATION_APPROVED',
                entity_name='AiRecommendation',
                entity_id=str(recommendation.id),
                details=f"Physician approved recommendation #{recommendation.id} for {recommendation.patient.user.get_full_name()}."
            )

            messages.success(request, f"Recommendation #{recommendation.id} approved and released to {recommendation.patient.user.get_full_name()}.")
            return redirect('physicians:dashboard')

        elif action == 'MODIFY':
            # Physician modified the recommendation
            new_title = request.POST.get('title', recommendation.title).strip()
            new_summary = request.POST.get('summary_content', recommendation.summary_content).strip()
            new_guidance = request.POST.get('follow_up_guidance', recommendation.follow_up_guidance).strip()
            
            # Raw JSON or edited lists
            raw_daily = request.POST.get('daily_schedule_json')
            raw_coping = request.POST.get('coping_strategies_text', '')

            try:
                daily_plan = json.loads(raw_daily) if raw_daily else recommendation.daily_schedule_plan
            except Exception:
                daily_plan = recommendation.daily_schedule_plan

            coping_list = [c.strip() for c in raw_coping.split('\n') if c.strip()] if raw_coping else recommendation.coping_strategies

            recommendation.title = new_title
            recommendation.summary_content = new_summary
            recommendation.follow_up_guidance = new_guidance
            recommendation.daily_schedule_plan = daily_plan
            recommendation.coping_strategies = coping_list
            recommendation.status = 'MODIFIED_AND_APPROVED'
            recommendation.approved_by = physician_profile
            recommendation.approved_at = timezone.now()
            recommendation.current_version += 1
            recommendation.is_visible_to_patient = True
            recommendation.save()

            # Create new version record
            RecommendationVersion.objects.create(
                recommendation=recommendation,
                version_number=recommendation.current_version,
                modification_type='PHYSICIAN_MODIFICATION',
                title=new_title,
                summary_content=new_summary,
                daily_schedule_plan=daily_plan,
                weekly_activities_plan=recommendation.weekly_activities_plan,
                coping_strategies=coping_list,
                preventive_strategies=recommendation.preventive_strategies,
                modified_by=request.user,
                change_summary=decision_reason or 'Clinical adjustments made by physician prior to patient release.'
            )

            # Update schedule and activities
            schedule = WellnessSchedule.objects.filter(recommendation=recommendation).first()
            if schedule:
                schedule.is_physician_approved = True
                schedule.custom_physician_notes = instructions_for_patient
                schedule.save()
                # Update activities with edited times/titles if modified
                if daily_plan:
                    WellnessActivity.objects.filter(schedule=schedule, status='PENDING').delete()
                    for idx, act in enumerate(daily_plan, 1):
                        try:
                            tp = act.get('time', '08:00').split(':')
                            at = time(int(tp[0]), int(tp[1]))
                        except Exception:
                            at = time(8, 0)
                        WellnessActivity.objects.create(
                            schedule=schedule,
                            patient=recommendation.patient,
                            title=act.get('activity', 'Scheduled Activity'),
                            description=act.get('description', ''),
                            category=act.get('category', 'MINDFULNESS'),
                            scheduled_date=date.today(),
                            start_time=at,
                            end_time=(timezone.datetime.combine(date.today(), at) + timedelta(minutes=30)).time(),
                            purpose=act.get('purpose', 'Wellness routine'),
                            status='PENDING',
                            order=idx
                        )

            # Record approval
            PhysicianApproval.objects.create(
                recommendation=recommendation,
                physician=physician_profile,
                decision='MODIFIED_AND_APPROVED',
                reason_or_notes=decision_reason or 'Clinical modifications applied by physician.',
                instructions_for_patient=instructions_for_patient
            )

            # Notify patient
            Notification.send(
                recipient=recommendation.patient.user,
                notification_type='RECOMMENDATION_MODIFIED',
                title="Physician-Modified Wellness Care Guidance Released",
                message=f"Dr. {physician_profile.user.last_name} personalized and approved your mental wellness program.",
                action_url=f"/recommendations/patient/{recommendation.id}/"
            )

            # Audit log
            AuditLog.objects.create(
                user=request.user,
                action='RECOMMENDATION_MODIFIED',
                entity_name='AiRecommendation',
                entity_id=str(recommendation.id),
                details=f"Physician revised and released recommendation #{recommendation.id} (Version {recommendation.current_version})."
            )

            messages.success(request, f"Recommendation #{recommendation.id} successfully modified and released to patient.")
            return redirect('physicians:dashboard')

        elif action == 'REJECT':
            if not decision_reason:
                messages.error(request, "A clinical justification reason is mandatory when rejecting a recommendation.")
                return redirect('recommendations:review', rec_id=recommendation.id)

            recommendation.status = 'REJECTED'
            recommendation.is_visible_to_patient = False
            recommendation.save()

            PhysicianApproval.objects.create(
                recommendation=recommendation,
                physician=physician_profile,
                decision='REJECTED',
                reason_or_notes=decision_reason
            )

            AuditLog.objects.create(
                user=request.user,
                action='RECOMMENDATION_REJECTED',
                entity_name='AiRecommendation',
                entity_id=str(recommendation.id),
                details=f"Physician rejected recommendation #{recommendation.id}. Reason: {decision_reason}"
            )

            messages.warning(request, f"Recommendation #{recommendation.id} rejected. Reason recorded in audit log.")
            return redirect('physicians:dashboard')

        elif action == 'REQUEST_FURTHER_ASSESSMENT':
            recommendation.status = 'FURTHER_ASSESSMENT_REQUIRED'
            recommendation.is_visible_to_patient = False
            recommendation.save()

            PhysicianApproval.objects.create(
                recommendation=recommendation,
                physician=physician_profile,
                decision='FURTHER_ASSESSMENT_REQUESTED',
                reason_or_notes=decision_reason or 'Additional clinical assessment or clinical interview needed.'
            )

            # Notify patient that additional assessment or appointment is requested
            Notification.send(
                recipient=recommendation.patient.user,
                notification_type='RECOMMENDATION_HOLD',
                title="Clinical Follow-up & Assessment Needed",
                message=f"Dr. {physician_profile.user.last_name} reviewed your screening and requested an additional clinical interview or follow-up before issuing guidance.",
                action_url="/appointments/request/",
                is_urgent=True
            )

            AuditLog.objects.create(
                user=request.user,
                action='RECOMMENDATION_HOLD',
                entity_name='AiRecommendation',
                entity_id=str(recommendation.id),
                details=f"Physician requested further assessment for patient {recommendation.patient.user.get_full_name()}."
            )

            messages.info(request, f"Recommendation #{recommendation.id} placed on hold pending additional assessment.")
            return redirect('physicians:dashboard')

        elif action == 'REGENERATE_AI':
            # Re-runs AI Engine
            new_rec = generate_ai_analysis_and_recommendations(assessment)
            messages.info(request, "AI Analysis & Recommendation regenerated successfully.")
            return redirect('recommendations:review', rec_id=new_rec.id)

    coping_text = "\n".join(recommendation.coping_strategies) if isinstance(recommendation.coping_strategies, list) else str(recommendation.coping_strategies)

    context = {
        'recommendation': recommendation,
        'assessment': assessment,
        'versions': versions,
        'approval_history': approval_history,
        'ai_analysis': ai_analysis,
        'screening_results': screening_results,
        'coping_text': coping_text,
        'daily_schedule_json': json.dumps(recommendation.daily_schedule_plan, indent=2)
    }
    return render(request, 'recommendations/physician_review.html', context)


@login_required
def patient_recommendation_view(request, rec_id):
    """
    Patient-facing view.
    STRICT SECURITY CHECK:
    - Only the owning patient (or their assigned physician/staff) can view.
    - AI recommendations that are NOT approved by a physician CANNOT be viewed
      as approved guidance; clear status badges and disclaimers are enforced.
    """
    recommendation = get_object_or_404(
        AiRecommendation.objects.select_related('patient__user', 'approved_by__user', 'assessment'),
        id=rec_id
    )

    # Permission check
    if request.user.is_patient and recommendation.patient.user != request.user:
        messages.error(request, "Unauthorized access to patient record.")
        return redirect('patients:dashboard')

    # If patient is viewing and recommendation is still pending approval, display pending state with banner
    is_approved = recommendation.is_visible_to_patient and recommendation.status in ['APPROVED', 'MODIFIED_AND_APPROVED']

    schedule = WellnessSchedule.objects.filter(recommendation=recommendation).first()
    activities = WellnessActivity.objects.filter(schedule=schedule).order_by('scheduled_date', 'start_time') if schedule else []

    context = {
        'recommendation': recommendation,
        'is_approved': is_approved,
        'schedule': schedule,
        'activities': activities,
        'assessment': recommendation.assessment,
        'approved_by': recommendation.approved_by,
    }
    return render(request, 'recommendations/patient_view.html', context)


@login_required
@physician_required
def version_history_view(request, rec_id):
    """
    Shows full audit history and side-by-side versions of AI generation vs physician modification.
    """
    recommendation = get_object_or_404(AiRecommendation, id=rec_id)
    versions = recommendation.versions.all().order_by('-version_number')
    approvals = recommendation.approval_reviews.select_related('physician__user').all()

    context = {
        'recommendation': recommendation,
        'versions': versions,
        'approvals': approvals
    }
    return render(request, 'recommendations/version_history.html', context)

