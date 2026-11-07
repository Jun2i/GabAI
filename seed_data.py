import os
import django
from datetime import date, time, timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mindcare.settings')
django.setup()

from apps.accounts.models import User, AuditLog
from apps.patients.models import PatientProfile
from apps.physicians.models import PhysicianProfile, HealthcareStaff, ClinicalRecord, FollowUp
from apps.assessments.models import QuestionnaireCategory, Question, Assessment, PatientResponse, ScreeningResult
from apps.recommendations.models import AiRecommendation, RecommendationVersion, PhysicianApproval
from apps.wellness.models import WellnessSchedule, WellnessActivity, ActivityProgress
from apps.safety.models import SafetyAssessment
from apps.appointments.models import Appointment
from apps.notifications.models import Notification

def seed():
    print("Beginning GabAI comprehensive database seeding (28 Patients, 15 Physicians, 6 Categories)...")

    # Clean previous demo records for idempotent seeding
    PatientResponse.objects.all().delete()
    ScreeningResult.objects.all().delete()
    SafetyAssessment.objects.all().delete()
    RecommendationVersion.objects.all().delete()
    PhysicianApproval.objects.all().delete()
    AiRecommendation.objects.all().delete()
    WellnessActivity.objects.all().delete()
    WellnessSchedule.objects.all().delete()
    Assessment.objects.all().delete()
    Appointment.objects.all().delete()
    Notification.objects.all().delete()
    ClinicalRecord.objects.all().delete()
    FollowUp.objects.all().delete()
    Question.objects.all().delete()
    QuestionnaireCategory.objects.all().delete()

    # 1. SIX STREAMLINED QUESTIONNAIRE CATEGORIES
    categories_data = [
        {
            'code': 'ANXIETY',
            'name': 'Anxiety',
            'description': 'Screens for persistent worry, nervous anticipation, physical tension, and difficulty calming down.',
            'order': 1,
            'is_dev': False,
            'is_crit': False,
            'disclaimer': 'Informational screening for anxiety indicators. Does not constitute a psychiatric diagnosis.',
            'questions': [
                ("Feeling nervous, anxious, or constantly on edge?", "FREQUENCY"),
                ("Finding it difficult to stop or control worrying thoughts?", "FREQUENCY"),
                ("Feeling restless, irritable, or physically tense when stressed?", "FREQUENCY"),
            ]
        },
        {
            'code': 'DEPRESSION',
            'name': 'Depression',
            'description': 'Assesses depressed mood, loss of interest in daily activities, low energy, and discouragement.',
            'order': 2,
            'is_dev': False,
            'is_crit': False,
            'disclaimer': 'Informational screening for depressive symptoms based on core PHQ dimensions.',
            'questions': [
                ("Having little interest or pleasure in doing everyday activities?", "FREQUENCY"),
                ("Feeling down, depressed, discouraged, or hopeless?", "FREQUENCY"),
                ("Experiencing low energy, persistent exhaustion, or feelings of worthlessness?", "FREQUENCY"),
            ]
        },
        {
            'code': 'STRESS',
            'name': 'Stress',
            'description': 'Measures perceived daily pressure, cognitive exhaustion, and difficulty managing responsibilities.',
            'order': 3,
            'is_dev': False,
            'is_crit': False,
            'disclaimer': 'Evaluates stress resilience and burnout markers.',
            'questions': [
                ("Feeling overwhelmed or unable to manage your daily work or school responsibilities?", "FREQUENCY"),
                ("Finding it difficult to unwind, relax, or calm your racing mind after a stressful day?", "FREQUENCY"),
            ]
        },
        {
            'code': 'EMOTIONAL_WELLBEING',
            'name': 'Emotional Well-being',
            'description': 'Evaluates emotional balance, mood fluctuations, and feelings of interpersonal connection.',
            'order': 4,
            'is_dev': False,
            'is_crit': False,
            'disclaimer': 'Measures general affective stability and emotional coping.',
            'questions': [
                ("Experiencing sudden mood shifts or emotional sensitivity that feels difficult to manage?", "FREQUENCY"),
                ("Feeling emotionally detached, numb, or isolated from friends and loved ones?", "FREQUENCY"),
            ]
        },
        {
            'code': 'SLEEP_DAILY',
            'name': 'Sleep and Daily Activities',
            'description': 'Screens for sleep disruption, circadian irregularity, and interference with everyday functioning.',
            'order': 5,
            'is_dev': False,
            'is_crit': False,
            'disclaimer': 'Assesses behavioral wellness and lifestyle routine impact.',
            'questions': [
                ("Having trouble falling asleep, waking frequently during the night, or sleeping excessively?", "FREQUENCY"),
                ("Finding that stress or low mood interferes with completing your work, studies, or daily routine?", "FREQUENCY"),
            ]
        },
        {
            'code': 'SAFETY',
            'name': 'Safety and Self-Harm',
            'description': 'CRITICAL SAFETY: Evaluates personal safety, self-harm risk, and need for immediate crisis support.',
            'order': 6,
            'is_dev': False,
            'is_crit': True,
            'disclaimer': 'Immediate high-priority emergency triage triggered upon any positive indication.',
            'questions': [
                ("Over the past two weeks, have you had thoughts of hurting yourself or wishing you were no longer alive?", "FREQUENCY"),
                ("Do you currently feel unsafe or in need of immediate support or crisis intervention?", "YES_NO"),
            ]
        },
    ]

    cat_map = {}
    question_map = {}
    for cdata in categories_data:
        cat = QuestionnaireCategory.objects.create(
            code=cdata['code'],
            name=cdata['name'],
            description=cdata['description'],
            category_order=cdata['order'],
            is_developmental=cdata['is_dev'],
            is_critical_safety=cdata['is_crit'],
            disclaimer=cdata['disclaimer']
        )
        cat_map[cdata['code']] = cat
        question_map[cdata['code']] = []

        for idx, (qtext, qtype) in enumerate(cdata['questions'], 1):
            is_crit = (cdata['code'] == 'SAFETY')
            q = Question.objects.create(
                category=cat,
                question_text=qtext,
                question_type=qtype,
                order=idx,
                is_critical_safety=is_crit,
                help_text="Essential clinical screening indicator"
            )
            question_map[cdata['code']].append(q)

    print(f"Created {QuestionnaireCategory.objects.count()} categories and {Question.objects.count()} questions.")

    # 2. SYSTEM ADMIN
    admin_user, _ = User.objects.update_or_create(
        username='admin',
        defaults={
            'email': 'admin@gabai.ai',
            'first_name': 'System',
            'last_name': 'Administrator',
            'role': User.Role.ADMIN,
            'is_staff': True,
            'is_superuser': True,
            'is_verified': True,
            'consent_given': True,
            'consent_date': timezone.now()
        }
    )
    admin_user.set_password('AdminPass123!')
    admin_user.save()

    # 3. HEALTHCARE STAFF
    staff_user, _ = User.objects.update_or_create(
        username='staff.maria',
        defaults={
            'email': 'staff.maria@gabai.ai',
            'first_name': 'Maria',
            'last_name': 'Santos',
            'role': User.Role.STAFF,
            'is_verified': True,
            'consent_given': True,
            'consent_date': timezone.now()
        }
    )
    staff_user.set_password('StaffPass123!')
    staff_user.save()
    HealthcareStaff.objects.update_or_create(
        user=staff_user,
        defaults={
            'department': 'Triage & Patient Intake',
            'staff_id': 'STF-0842'
        }
    )

    # 4. 15 LICENSED PHYSICIANS
    physicians_raw = [
        ("dr.santos", "DoctorPass123!", "Sarah", "Santos", "PRC-0149823", "Adult Psychiatry & Affective Disorders", "Philippine General Hospital / GabAI Mental Health Center", "Mon, Wed, Fri 9:00 AM - 4:00 PM", True),
        ("dr.morales", "DoctorPass123!", "Rafael", "Morales", "PRC-0138910", "Child & Adolescent Psychiatry", "St. Luke's Medical Center - Global City", "Tue, Thu 10:00 AM - 5:00 PM", True),
        ("dr.reyes", "DoctorPass123!", "Angela", "Reyes", "PRC-0158201", "Cognitive Behavioral Therapy & Mood Disorders", "Makati Medical Center", "Mon-Fri 8:30 AM - 3:30 PM", True),
        ("dr.aquino", "DoctorPass123!", "Marcus", "Aquino", "PRC-0162940", "Consultation-Liaison Psychiatry", "The Medical City - Pasig", "Mon, Wed 1:00 PM - 6:00 PM", True),
        ("dr.villanueva", "DoctorPass123!", "Elena", "Villanueva", "PRC-0171829", "Neuropsychiatry & Sleep Medicine", "Cardinal Santos Medical Center", "Wed, Fri 9:00 AM - 3:00 PM", True),
        ("dr.tan", "DoctorPass123!", "David", "Tan", "PRC-0182741", "Anxiety Spectrum & Trauma Recovery", "Asian Hospital and Medical Center", "Mon, Thu 9:00 AM - 4:00 PM", True),
        ("dr.cruz", "DoctorPass123!", "Patricia", "Cruz", "PRC-0193852", "Addiction Medicine & Behavioral Health", "National Center for Mental Health", "Tue, Fri 10:00 AM - 4:00 PM", True),
        ("dr.delarosa", "DoctorPass123!", "Miguel", "Dela Rosa", "PRC-0204963", "Geriatric Psychiatry & Cognitive Health", "Manila Doctors Hospital", "Mon, Wed 9:00 AM - 1:00 PM", True),
        ("dr.lim", "DoctorPass123!", "Christine", "Lim", "PRC-0215074", "Adolescent Psychology & Life Transitions", "UST Hospital - Clinical Division", "Tue, Thu 1:00 PM - 5:00 PM", True),
        ("dr.castillo", "DoctorPass123!", "Gabriel", "Castillo", "PRC-0226185", "Clinical Neuropsychology & Stress Recovery", "De La Salle University Medical Center", "Mon, Fri 10:00 AM - 4:00 PM", True),
        ("dr.mendoza", "DoctorPass123!", "Joanna", "Mendoza", "PRC-0237296", "Occupational Burnout & Workplace Wellness", "GabAI Clinical Network - Ortigas Hub", "Mon-Fri 9:00 AM - 5:00 PM", True),
        ("dr.ramos", "DoctorPass123!", "Antonio", "Ramos", "PRC-0248307", "Psychosomatic & Integrative Psychiatry", "Chong Hua Hospital", "Wed, Sat 9:00 AM - 2:00 PM", True),
        ("dr.garcia", "DoctorPass123!", "Carmela", "Garcia", "PRC-0259418", "Interpersonal Psychotherapy & Family Counseling", "Capitol Medical Center", "Tue, Thu 9:00 AM - 3:00 PM", True),
        ("dr.navarro", "DoctorPass123!", "Kenneth", "Navarro", "PRC-0260529", "Crisis Intervention & Emergency Psychiatry", "Philippine Heart Center Clinical Liaison", "24/7 On-Call Rotation", True),
        ("dr.valdez", "DoctorPass123!", "Stephanie", "Valdez", "PRC-0271630", "Mindfulness-Based Clinical Psychology", "San Juan De Dios Hospital", "Mon, Thu 10:00 AM - 4:00 PM", True),
    ]

    physician_profiles = []
    for uname, pwd, fname, lname, lic, spec, hosp, hrs, ver in physicians_raw:
        u, _ = User.objects.update_or_create(
            username=uname,
            defaults={
                'email': f"{uname}@gabai.ai",
                'first_name': fname,
                'last_name': lname,
                'role': User.Role.PHYSICIAN,
                'is_verified': ver,
                'consent_given': True,
                'consent_date': timezone.now()
            }
        )
        u.set_password(pwd)
        u.save()

        p, _ = PhysicianProfile.objects.update_or_create(
            user=u,
            defaults={
                'license_number': lic,
                'specialization': spec,
                'hospital_affiliation': hosp,
                'consultation_hours': hrs,
                'is_verified': ver,
                'verified_at': timezone.now() if ver else None,
                'verified_by': admin_user
            }
        )
        physician_profiles.append(p)

    print(f"Created {len(physician_profiles)} licensed physicians.")

    # 5. 28 REALISTIC DUMMY PATIENT PROFILES
    patients_data = [
        # 1. Juan (Minimal, Pathway A, Approved)
        ("patient.juan", "PatientPass123!", "Juan", "Dela Cruz", "Male", 24, date(2002, 3, 15), "Software Engineering Intern [Demo Data]", "8:30 AM - 5:30 PM weekdays", 0, "APPROVED", "PATHWAY_A", {'ANXIETY': (1,0,1), 'DEPRESSION': (0,1,0), 'STRESS': (1,0), 'EMOTIONAL_WELLBEING': (0,0), 'SLEEP_DAILY': (1,0), 'SAFETY': (0,0)}, False),
        # 2. Ana (Moderate Anxiety & Depression, Pathway B, Approved)
        ("patient.ana", "PatientPass123!", "Ana Marie", "Santos", "Female", 29, date(1997, 8, 22), "Senior Financial Analyst [Demo Data]", "9:00 AM - 6:00 PM weekdays", 0, "APPROVED", "PATHWAY_B", {'ANXIETY': (3,2,3), 'DEPRESSION': (2,3,2), 'STRESS': (2,3), 'EMOTIONAL_WELLBEING': (2,2), 'SLEEP_DAILY': (3,2), 'SAFETY': (0,0)}, False),
        # 3. Carlos (Elevated ADHD & Stress, Pathway B, Pending Approval)
        ("patient.carlos", "PatientPass123!", "Carlos", "Mendoza", "Male", 22, date(2004, 11, 5), "University Senior Student [Demo Data]", "Irregular college schedule", 1, "PENDING_APPROVAL", "PATHWAY_B", {'ANXIETY': (2,2,2), 'DEPRESSION': (1,2,1), 'STRESS': (3,2), 'EMOTIONAL_WELLBEING': (2,1), 'SLEEP_DAILY': (2,3), 'SAFETY': (0,0)}, False),
        # 4. Elena (Acute Safety Alert, Active Emergency)
        ("patient.elena", "PatientPass123!", "Elena", "Rivera", "Female", 26, date(2000, 5, 12), "Freelance UX Designer [Demo Data]", "Flexible remote hours", 13, "PENDING_APPROVAL", "PATHWAY_B", {'ANXIETY': (3,3,3), 'DEPRESSION': (3,3,3), 'STRESS': (3,3), 'EMOTIONAL_WELLBEING': (3,3), 'SLEEP_DAILY': (3,3), 'SAFETY': (3,1)}, True),
        # 5. Miguel (Workplace Burnout & Insomnia, Approved)
        ("patient.miguel", "PatientPass123!", "Miguel", "Bautista", "Male", 31, date(1995, 4, 18), "Cloud Infrastructure Engineer [Demo Data]", "8:00 AM - 5:00 PM weekdays", 2, "APPROVED", "PATHWAY_A", {'ANXIETY': (1,1,0), 'DEPRESSION': (1,0,1), 'STRESS': (2,2), 'EMOTIONAL_WELLBEING': (1,0), 'SLEEP_DAILY': (2,1), 'SAFETY': (0,0)}, False),
        # 6. Sofia (Social Anxiety, Pending Approval)
        ("patient.sofia", "PatientPass123!", "Sofia", "Reyes", "Female", 19, date(2007, 9, 30), "College Sophomore [Demo Data]", "8:00 AM - 3:00 PM classes", 8, "PENDING_APPROVAL", "PATHWAY_B", {'ANXIETY': (3,3,2), 'DEPRESSION': (1,2,1), 'STRESS': (2,2), 'EMOTIONAL_WELLBEING': (2,2), 'SLEEP_DAILY': (1,2), 'SAFETY': (0,0)}, False),
        # 7. Roberto (Chronic Stress, Modified & Approved)
        ("patient.roberto", "PatientPass123!", "Roberto", "Dizon", "Male", 46, date(1980, 1, 14), "Bank Branch Head [Demo Data]", "8:00 AM - 6:00 PM weekdays", 3, "MODIFIED_AND_APPROVED", "PATHWAY_B", {'ANXIETY': (2,2,2), 'DEPRESSION': (1,2,1), 'STRESS': (3,3), 'EMOTIONAL_WELLBEING': (2,1), 'SLEEP_DAILY': (2,2), 'SAFETY': (0,0)}, False),
        # 8. Jasmine (Low Motivation, Pending Approval)
        ("patient.jasmine", "PatientPass123!", "Jasmine", "Flores", "Female", 27, date(1999, 7, 3), "Freelance Illustrator [Demo Data]", "Afternoons & late nights", 0, "PENDING_APPROVAL", "PATHWAY_B", {'ANXIETY': (2,1,2), 'DEPRESSION': (2,2,2), 'STRESS': (2,1), 'EMOTIONAL_WELLBEING': (2,2), 'SLEEP_DAILY': (3,2), 'SAFETY': (0,0)}, False),
        # 9. Mark (Mild Tension, Approved)
        ("patient.mark", "PatientPass123!", "Mark Anthony", "Tan", "Male", 34, date(1992, 12, 8), "Certified Public Accountant [Demo Data]", "9:00 AM - 6:00 PM weekdays", 4, "APPROVED", "PATHWAY_A", {'ANXIETY': (1,1,1), 'DEPRESSION': (0,1,0), 'STRESS': (2,1), 'EMOTIONAL_WELLBEING': (0,1), 'SLEEP_DAILY': (1,1), 'SAFETY': (0,0)}, False),
        # 10. Clara (Shift Work Sleep Disorder, Modified & Approved)
        ("patient.clara", "PatientPass123!", "Clara", "Evangelista", "Female", 21, date(2005, 6, 20), "Student Nurse [Demo Data]", "Rotating 12-hour hospital shifts", 4, "MODIFIED_AND_APPROVED", "PATHWAY_B", {'ANXIETY': (2,1,2), 'DEPRESSION': (1,1,1), 'STRESS': (2,2), 'EMOTIONAL_WELLBEING': (1,1), 'SLEEP_DAILY': (3,3), 'SAFETY': (0,0)}, False),
        # 11. Paolo (Depressive Burden, Further Assessment Required)
        ("patient.paolo", "PatientPass123!", "Paolo", "Soriano", "Male", 39, date(1987, 3, 27), "High School Science Teacher [Demo Data]", "7:00 AM - 4:00 PM weekdays", 2, "FURTHER_ASSESSMENT_REQUIRED", "PATHWAY_B", {'ANXIETY': (2,2,2), 'DEPRESSION': (3,2,3), 'STRESS': (2,3), 'EMOTIONAL_WELLBEING': (2,2), 'SLEEP_DAILY': (2,3), 'SAFETY': (0,0)}, False),
        # 12. Beatriz (Work-Life Imbalance, Approved)
        ("patient.beatriz", "PatientPass123!", "Beatriz", "Alcantara", "Female", 25, date(2001, 10, 11), "Brand Marketing Associate [Demo Data]", "9:00 AM - 5:30 PM weekdays", 5, "APPROVED", "PATHWAY_A", {'ANXIETY': (1,0,1), 'DEPRESSION': (0,0,1), 'STRESS': (1,2), 'EMOTIONAL_WELLBEING': (1,0), 'SLEEP_DAILY': (1,1), 'SAFETY': (0,0)}, False),
        # 13. Joshua (Attention Fatigue, Pending Approval)
        ("patient.joshua", "PatientPass123!", "Joshua", "Lim", "Male", 23, date(2003, 2, 17), "Junior Web Developer [Demo Data]", "Flexible work from home", 1, "PENDING_APPROVAL", "PATHWAY_B", {'ANXIETY': (2,2,1), 'DEPRESSION': (1,1,2), 'STRESS': (2,2), 'EMOTIONAL_WELLBEING': (2,2), 'SLEEP_DAILY': (2,2), 'SAFETY': (0,0)}, False),
        # 14. Isabella (Panic Tendencies, Approved)
        ("patient.isabella", "PatientPass123!", "Isabella", "Castro", "Female", 42, date(1984, 8, 9), "Retail Boutique Owner [Demo Data]", "10:00 AM - 7:00 PM Tue-Sun", 5, "APPROVED", "PATHWAY_B", {'ANXIETY': (3,2,2), 'DEPRESSION': (1,1,1), 'STRESS': (2,3), 'EMOTIONAL_WELLBEING': (2,1), 'SLEEP_DAILY': (2,1), 'SAFETY': (0,0)}, False),
        # 15. Ricardo (Sleep Disruption, Approved)
        ("patient.ricardo", "PatientPass123!", "Ricardo", "Pascual", "Male", 54, date(1972, 5, 25), "Manufacturing Plant Supervisor [Demo Data]", "6:00 AM - 3:00 PM weekdays", 7, "APPROVED", "PATHWAY_A", {'ANXIETY': (1,0,0), 'DEPRESSION': (1,0,0), 'STRESS': (1,1), 'EMOTIONAL_WELLBEING': (0,0), 'SLEEP_DAILY': (2,1), 'SAFETY': (0,0)}, False),
        # 16. Nicole (Academic Perfectionism, Approved)
        ("patient.nicole", "PatientPass123!", "Nicole", "Umali", "Female", 20, date(2006, 12, 1), "Psychology Major [Demo Data]", "University classes & study blocks", 8, "APPROVED", "PATHWAY_A", {'ANXIETY': (1,1,1), 'DEPRESSION': (0,1,0), 'STRESS': (1,1), 'EMOTIONAL_WELLBEING': (1,0), 'SLEEP_DAILY': (1,1), 'SAFETY': (0,0)}, False),
        # 17. Christian (Severe Emotional Exhaustion, Rejected)
        ("patient.christian", "PatientPass123!", "Christian", "Gomez", "Male", 36, date(1990, 7, 19), "Database Administrator [Demo Data]", "8:30 AM - 6:00 PM weekdays", 6, "REJECTED", "PATHWAY_B", {'ANXIETY': (2,3,2), 'DEPRESSION': (3,2,3), 'STRESS': (3,3), 'EMOTIONAL_WELLBEING': (3,2), 'SLEEP_DAILY': (3,2), 'SAFETY': (0,0)}, False),
        # 18. Patricia (Postpartum Sensitivity, Modified & Approved)
        ("patient.patricia", "PatientPass123!", "Patricia", "Domingo", "Female", 30, date(1996, 4, 30), "Clinical Pharmacist [Demo Data]", "7:00 AM - 3:00 PM shifts", 12, "MODIFIED_AND_APPROVED", "PATHWAY_B", {'ANXIETY': (2,2,2), 'DEPRESSION': (2,2,1), 'STRESS': (3,2), 'EMOTIONAL_WELLBEING': (3,2), 'SLEEP_DAILY': (3,2), 'SAFETY': (0,0)}, False),
        # 19. Gabriel (Culinary Stress, Pending Approval)
        ("patient.gabriel", "PatientPass123!", "Gabriel", "Hernandez", "Male", 28, date(1998, 11, 14), "Restaurant Head Chef [Demo Data]", "2:00 PM - 11:00 PM Tue-Sun", 10, "PENDING_APPROVAL", "PATHWAY_B", {'ANXIETY': (2,2,2), 'DEPRESSION': (1,1,2), 'STRESS': (3,3), 'EMOTIONAL_WELLBEING': (2,1), 'SLEEP_DAILY': (2,3), 'SAFETY': (0,0)}, False),
        # 20. Francesca (Workplace Routine Maintenance, Approved)
        ("patient.francesca", "PatientPass123!", "Francesca", "Villar", "Female", 33, date(1993, 2, 28), "Corporate HR Manager [Demo Data]", "9:00 AM - 5:00 PM weekdays", 10, "APPROVED", "PATHWAY_A", {'ANXIETY': (1,0,0), 'DEPRESSION': (0,0,1), 'STRESS': (1,1), 'EMOTIONAL_WELLBEING': (0,0), 'SLEEP_DAILY': (1,0), 'SAFETY': (0,0)}, False),
        # 21. Eduardo (Circadian Fatigue, Approved)
        ("patient.eduardo", "PatientPass123!", "Eduardo", "Macaraeg", "Male", 49, date(1977, 9, 7), "Logistics Fleet Coordinator [Demo Data]", "Night shifts 9:00 PM - 5:00 AM", 4, "APPROVED", "PATHWAY_B", {'ANXIETY': (2,1,1), 'DEPRESSION': (1,1,1), 'STRESS': (2,2), 'EMOTIONAL_WELLBEING': (1,1), 'SLEEP_DAILY': (3,2), 'SAFETY': (0,0)}, False),
        # 22. Alyssa (Situational Call Center Anxiety, Approved)
        ("patient.alyssa", "PatientPass123!", "Alyssa", "Pineda", "Female", 22, date(2004, 3, 23), "Customer Care Associate [Demo Data]", "Graveyard shift 10:00 PM - 6:00 AM", 9, "APPROVED", "PATHWAY_A", {'ANXIETY': (1,1,1), 'DEPRESSION': (0,1,0), 'STRESS': (2,1), 'EMOTIONAL_WELLBEING': (1,0), 'SLEEP_DAILY': (2,1), 'SAFETY': (0,0)}, False),
        # 23. Vincent (Architectural Project Pressure, Pending Approval)
        ("patient.vincent", "PatientPass123!", "Vincent", "Ocampo", "Male", 29, date(1997, 10, 16), "Licensed Architect [Demo Data]", "9:00 AM - 7:00 PM plus deadlines", 0, "PENDING_APPROVAL", "PATHWAY_B", {'ANXIETY': (3,2,2), 'DEPRESSION': (2,1,2), 'STRESS': (3,3), 'EMOTIONAL_WELLBEING': (2,2), 'SLEEP_DAILY': (2,2), 'SAFETY': (0,0)}, False),
        # 24. Maricel (Compassion Fatigue, Modified & Approved)
        ("patient.maricel", "PatientPass123!", "Maricel", "De Vera", "Female", 37, date(1989, 5, 19), "Special Education Teacher [Demo Data]", "7:30 AM - 4:00 PM weekdays", 11, "MODIFIED_AND_APPROVED", "PATHWAY_B", {'ANXIETY': (2,2,2), 'DEPRESSION': (2,2,1), 'STRESS': (3,2), 'EMOTIONAL_WELLBEING': (2,2), 'SLEEP_DAILY': (2,2), 'SAFETY': (0,0)}, False),
        # 25. Angelo (Adolescent Academic Strain, Further Assessment Required)
        ("patient.angelo", "PatientPass123!", "Angelo", "Tolentino", "Male", 18, date(2008, 1, 10), "Senior High School Student [Demo Data]", "7:00 AM - 3:30 PM weekdays", 8, "FURTHER_ASSESSMENT_REQUIRED", "PATHWAY_B", {'ANXIETY': (2,2,2), 'DEPRESSION': (2,2,2), 'STRESS': (2,2), 'EMOTIONAL_WELLBEING': (3,2), 'SLEEP_DAILY': (2,2), 'SAFETY': (0,0)}, False),
        # 26. Daniela (Actuarial Exhaustion, Pending Approval)
        ("patient.daniela", "PatientPass123!", "Daniela", "Magno", "Female", 35, date(1991, 6, 25), "Risk & Actuarial Consultant [Demo Data]", "8:30 AM - 6:30 PM weekdays", 9, "PENDING_APPROVAL", "PATHWAY_B", {'ANXIETY': (3,2,2), 'DEPRESSION': (1,2,2), 'STRESS': (3,3), 'EMOTIONAL_WELLBEING': (2,2), 'SLEEP_DAILY': (2,2), 'SAFETY': (0,0)}, False),
        # 27. Samuel (Logistics Minimal, Approved)
        ("patient.samuel", "PatientPass123!", "Samuel", "David", "Male", 41, date(1985, 4, 12), "Supply Chain Manager [Demo Data]", "8:00 AM - 5:00 PM weekdays", 7, "APPROVED", "PATHWAY_A", {'ANXIETY': (0,1,0), 'DEPRESSION': (0,0,0), 'STRESS': (1,0), 'EMOTIONAL_WELLBEING': (0,0), 'SLEEP_DAILY': (1,0), 'SAFETY': (0,0)}, False),
        # 28. Kristine (Acute Safety Concern, Active Emergency)
        ("patient.kristine", "PatientPass123!", "Kristine", "Salonga", "Female", 26, date(2000, 8, 18), "Multimedia Producer [Demo Data]", "Freelance media hours", 13, "PENDING_APPROVAL", "PATHWAY_B", {'ANXIETY': (3,3,3), 'DEPRESSION': (3,3,3), 'STRESS': (3,3), 'EMOTIONAL_WELLBEING': (3,3), 'SLEEP_DAILY': (3,3), 'SAFETY': (3,1)}, True),
    ]

    for pdata in patients_data:
        uname, pwd, fname, lname, gen, age, dob, occ, sched, doc_idx, rec_status, pathway, scores, is_crit = pdata

        u, _ = User.objects.update_or_create(
            username=uname,
            defaults={
                'email': f"{uname}@gabai.ai",
                'first_name': fname,
                'last_name': lname,
                'role': User.Role.PATIENT,
                'is_verified': True,
                'consent_given': True,
                'consent_date': timezone.now()
            }
        )
        u.set_password(pwd)
        u.save()

        doc_profile = physician_profiles[doc_idx] if doc_idx < len(physician_profiles) else physician_profiles[0]

        profile, _ = PatientProfile.objects.update_or_create(
            user=u,
            defaults={
                'date_of_birth': dob,
                'gender': gen,
                'occupation': occ,
                'work_or_school_schedule': sched,
                'personal_interests': 'Walking in nature, listening to acoustic music, reading non-fiction',
                'available_free_time': 'Evenings and weekends',
                'emergency_contact_name': f"Family Contact of {fname}",
                'emergency_contact_phone': '+63 917 555 0199',
                'emergency_contact_relationship': 'Immediate Family',
                'assigned_physician': doc_profile,
                'has_active_safety_alert': is_crit,
                'patient_preferences': '[SIMULATED DEMO DATA for Hackathon Testing]'
            }
        )

        # Create Assessment
        ass_date = timezone.now() - timedelta(days=(len(patients_data) - patients_data.index(pdata)))
        assessment = Assessment.objects.create(
            patient=profile,
            status='ANALYZED' if rec_status == 'PENDING_APPROVAL' else ('REVIEWED' if rec_status != 'APPROVED' else 'COMPLETED'),
            disclaimer_accepted=True,
            total_questions_answered=14,
            completion_rate=100.0,
            has_safety_flag=is_crit,
            created_at=ass_date
        )

        # Populate Responses & ScreeningResults
        phq_raw = sum(scores['DEPRESSION'])
        gad_raw = sum(scores['ANXIETY'])
        stress_raw = sum(scores['STRESS'])

        assessment.phq9_score = phq_raw
        assessment.gad7_score = gad_raw
        assessment.stress_score = stress_raw

        # Set severities based on streamlined 3-question scale
        if phq_raw >= 7:
            assessment.phq9_severity = "Elevated Depressive Indicators"
        elif phq_raw >= 5:
            assessment.phq9_severity = "Moderate Depressive Indicators"
        elif phq_raw >= 3:
            assessment.phq9_severity = "Mild Depressive Indicators"
        else:
            assessment.phq9_severity = "Minimal / No Depressive Indicators"

        if gad_raw >= 7:
            assessment.gad7_severity = "Elevated Anxiety Indicators"
        elif gad_raw >= 5:
            assessment.gad7_severity = "Moderate Anxiety Indicators"
        elif gad_raw >= 3:
            assessment.gad7_severity = "Mild Anxiety Indicators"
        else:
            assessment.gad7_severity = "Minimal / No Anxiety Indicators"

        assessment.save()

        # Save responses and category screening results
        for ccode, score_tuple in scores.items():
            cat = cat_map[ccode]
            q_list = question_map[ccode]
            cat_sum = 0
            for idx, q in enumerate(q_list):
                score_val = score_tuple[idx] if idx < len(score_tuple) else 0
                cat_sum += score_val
                lbl = {0: 'Not at all', 1: 'Several days', 2: 'More than half the days', 3: 'Nearly every day'}.get(score_val, str(score_val))
                if q.question_type == 'YES_NO':
                    lbl = 'Yes' if score_val == 1 else 'No'

                PatientResponse.objects.create(
                    assessment=assessment,
                    question=q,
                    response_value=str(score_val),
                    numeric_score=float(score_val),
                    response_label=lbl
                )

            max_possible = len(q_list) * 3.0
            score_pct = (cat_sum / max_possible * 100.0) if max_possible > 0 else 0.0
            sev = 'MINIMAL'
            elevated = False
            if score_pct >= 66.0 or (ccode == 'SAFETY' and is_crit):
                sev = 'HIGH' if ccode == 'SAFETY' else 'ELEVATED'
                elevated = True
            elif score_pct >= 40.0:
                sev = 'MODERATE'
                elevated = True
            elif score_pct >= 20.0:
                sev = 'MILD'

            ScreeningResult.objects.create(
                assessment=assessment,
                category=cat,
                raw_score=cat_sum,
                max_score=max_possible,
                score_percentage=round(score_pct, 1),
                severity_level=sev,
                is_elevated=elevated,
                indicator_summary=f"Reported score {cat_sum:.0f}/{max_possible:.0f} ({score_pct:.1f}%). Preliminary Indicator: {sev}."
            )

        # Handle Safety Alert if applicable
        if is_crit:
            SafetyAssessment.objects.create(
                assessment=assessment,
                patient=profile,
                intent_reported=True,
                plan_reported=False,
                inability_to_stay_safe=True,
                immediate_danger=True,
                urgency_level='CRITICAL',
                status='ACTIVE_EMERGENCY',
                safety_triggers_detected="Positive response to suicidal ideation and crisis safety screening items.",
                escalated_to=doc_profile,
                escalated_at=timezone.now(),
                action_taken="Emergency triage initiated. Crisis hotlines DOH 1553 and Hopeline dispatched."
            )

        # AI Recommendation
        pathway_title = "Preventive Routine & Healthy Habits" if pathway == 'PATHWAY_A' else "Targeted Coping Strategies & Clinical Consultation"
        summary_text = (
            f"Based on reported screening indicators (Anxiety: {assessment.gad7_severity}, Depression: {assessment.phq9_severity}), "
            f"GabAI structured a personalized {pathway_title} program. Supervised review by Dr. {doc_profile.user.get_full_name()}."
        )

        rec = AiRecommendation.objects.create(
            assessment=assessment,
            patient=profile,
            pathway=pathway,
            status=rec_status,
            title=f"Personalized Mental Health Plan: {pathway_title}",
            summary_content=summary_text,
            daily_schedule_plan=[
                {'time': '07:30', 'activity': 'Morning Box Breathing & Hydration', 'category': 'Mindfulness'},
                {'time': '12:30', 'activity': 'Mid-day 15-Minute Outdoor Walk', 'category': 'Movement'},
                {'time': '21:30', 'activity': '10-3-2-1 Sleep Hygiene Routine', 'category': 'Rest'}
            ],
            weekly_activities_plan=[
                {'day': 'Wednesday', 'title': 'Mid-week Reflective Journaling', 'category': 'Reflection'},
                {'day': 'Saturday', 'title': 'Social Connection Walk with Family/Friend', 'category': 'Social'}
            ],
            preventive_strategies=["Maintain consistent sleep and wake hours", "Take micro-breaks during work", "Stay physically hydrated"],
            coping_strategies=["4-7-8 Breathing Technique", "5-4-3-2-1 Grounding Method", "Progressive Muscle Relaxation"],
            is_visible_to_patient=(rec_status in ['APPROVED', 'MODIFIED_AND_APPROVED']),
            created_at=ass_date
        )

        if rec_status in ['APPROVED', 'MODIFIED_AND_APPROVED']:
            rec.approved_by = doc_profile
            rec.approved_at = timezone.now() - timedelta(days=1)
            rec.physician_notes = f"Clinical indicators reviewed and verified by Dr. {doc_profile.user.get_full_name()}. Patient authorized for wellness guidance."
            rec.save()

            PhysicianApproval.objects.create(
                recommendation=rec,
                physician=doc_profile,
                decision='APPROVED' if rec_status == 'APPROVED' else 'MODIFIED_AND_APPROVED',
                reason_or_notes="Authorized after reviewing screening results.",
                reviewed_at=timezone.now() - timedelta(days=1)
            )

        # Version
        RecommendationVersion.objects.create(
            recommendation=rec,
            version_number=1,
            modification_type='PHYSICIAN_MODIFICATION' if rec_status in ['APPROVED', 'MODIFIED_AND_APPROVED'] else 'AI_INITIAL',
            title=rec.title,
            summary_content=rec.summary_content,
            daily_schedule_plan=rec.daily_schedule_plan,
            weekly_activities_plan=rec.weekly_activities_plan,
            coping_strategies=rec.coping_strategies,
            preventive_strategies=rec.preventive_strategies,
            modified_by=doc_profile.user if rec_status in ['APPROVED', 'MODIFIED_AND_APPROVED'] else admin_user,
            change_summary="Initial AI guidance draft" if rec_status == 'PENDING_APPROVAL' else "Physician reviewed & released"
        )

        # Sample Appointments across statuses
        apt_status_choices = ['CONFIRMED', 'REQUESTED', 'COMPLETED', 'CONFIRMED']
        apt_status = apt_status_choices[patients_data.index(pdata) % len(apt_status_choices)]
        Appointment.objects.create(
            patient=profile,
            physician=doc_profile,
            appointment_type='INITIAL_EVALUATION' if pathway == 'PATHWAY_B' else 'WELLNESS_CHECK',
            consultation_mode='TELEHEALTH' if (patients_data.index(pdata) % 2 == 0) else 'IN_PERSON',
            appointment_date=date.today() + timedelta(days=((patients_data.index(pdata) % 7) - 2)),
            start_time=time(10 + (patients_data.index(pdata) % 5), 0),
            end_time=time(10 + (patients_data.index(pdata) % 5), 45),
            status=apt_status,
            reason_for_visit=f"Mental health assessment review and personalized guidance ({pathway_title}).",
            meeting_link=f"https://telehealth.gabai.ai/room/room-{uname.replace('patient.', '')}"
        )

    print(f"Successfully seeded {len(patients_data)} patient records with assessments, recommendations, and appointments.")

if __name__ == '__main__':
    seed()
