SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.0, 
    participation_fee=0.0,
    slider_timeout=60
)

PARTICIPANT_FIELDS = [
    'dictator_send_r1', 'dictator_send_r2', 'dictator_send_r3',
    'ultimatum_offer_r1', 'ultimatum_offer_r2', 'ultimatum_offer_r3',
    'ultimatum_accepted_r1', 'ultimatum_accepted_r2', 'ultimatum_accepted_r3',
    'jod_destroy_r1', 'jod_destroy_r2', 'jod_destroy_r3',
    'assigned_treatment',
]

SESSION_CONFIGS = [
    # 1) The Treatments
    dict(
        name='Full_Experiment',
        display_name="All Treatments, All Games",
        num_demo_participants=8,
        app_sequence=['app_00_personal_information','app_0_dictator', 'app_1_ultimatum', 'app_2_jod', 'app_3_treatment1', 'app_4_treatment2a', 'app_5_treatment2b', 'app_6_treatment3'],
    ),
    
    dict(
        name='treatment_1',
        display_name="Treatment 1 - Ultimate Representative",
        num_demo_participants=8,
        app_sequence=['app_00_personal_information','app_0_dictator', 'app_1_ultimatum', 'app_2_jod','app_3_treatment1'],
    ),
    
    dict(
        name='treatment_2a',
        display_name="Treatment 2a - Vengeful Representative",
        num_demo_participants=8,
        app_sequence=['app_00_personal_information','app_0_dictator', 'app_1_ultimatum', 'app_2_jod','app_4_treatment2a'],
    ),
    
    dict(
        name='treatment_2b',
        display_name="Treatment 2b - Representative Chaos",
        num_demo_participants=8,
        app_sequence=['app_00_personal_information','app_0_dictator', 'app_1_ultimatum', 'app_2_jod','app_5_treatment2b'],
    ),
    
    dict(
        name='treatment_3',
        display_name="Treatment 3 - Term Limits",
        num_demo_participants=8,
        app_sequence=['app_00_personal_information','app_0_dictator', 'app_1_ultimatum', 'app_2_jod','app_6_treatment3'],
    ),
    
    # 2. Debugging Area - Cause Life hates
    dict(
        name='debug_dictator',
        display_name="DEBUG: Dictator Game Only",
        num_demo_participants=2,
        app_sequence=['app_0_dictator'],
    ),
    dict(
        name='debug_ultimatum',
        display_name="DEBUG: Ultimatum Game Only",
        num_demo_participants=2,
        app_sequence=['app_1_ultimatum'],
    ),
    dict(
        name='debug_jod',
        display_name="DEBUG: Joy of Destruction Only",
        num_demo_participants=2,
        app_sequence=['app_2_jod'],
    ),
    dict(
        name='debug_treatment_1',
        display_name="DEBUG: Treatment 1 Only",
        num_demo_participants=6,
        app_sequence=['app_3_treatment1'],
        slider_task_timeout=15,
    ),
    dict(
        name='debug_treatment_2a',
        display_name="DEBUG: Treatment 2a Only",
        num_demo_participants=6,
        app_sequence=['app_4_treatment2a'],
        slider_task_timeout=15,
    ),
    dict(
        name='debug_treatment_2b',
        display_name="DEBUG: Treatment 2b Only",
        num_demo_participants=6,
        app_sequence=['app_5_treatment2b'],
        slider_task_timeout=15,
    ),
    dict(
        name='debug_treatment_3',
        display_name="DEBUG: Treatment 3 Only",
        num_demo_participants=6,
        app_sequence=['app_6_treatment3'],
        slider_task_timeout=15,
    ),
]

# Standard oTree Settings
LANGUAGE_CODE = 'en'
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'
SECRET_KEY = 'a-secret-key-for-testing'

ROOMS = [
    dict(
        name='econ_lab',
        display_name='Economics Lab Session',
        participant_label_file='_rooms/econ_lab.txt',
        use_secure_urls=True
    ),
]

INSTALLED_APPS = [
    'otree',
    'app_00_personal_information',
    'app_0_dictator', 
    'app_1_ultimatum', 
    'app_2_jod',
    'dispatcher',
    'app_3_treatment1', 
    'app_4_treatment2a', 
    'app_5_treatment2b', 
    'app_6_treatment3',
]