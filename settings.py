SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.0, 
    participation_fee=0.0
)

PARTICIPANT_FIELDS = [
    'dictator_send_r1', 'dictator_send_r2', 'dictator_send_r3',
    'ultimatum_offer_r1', 'ultimatum_offer_r2', 'ultimatum_offer_r3',
    'ultimatum_accepted_r1', 'ultimatum_accepted_r2', 'ultimatum_accepted_r3',
    'jod_destroy_r1', 'jod_destroy_r2', 'jod_destroy_r3',
]

SESSION_CONFIGS = [
    # --- 1. FULL EXPERIMENT CONFIGURATIONS ---
    # (Use these for running the complete experiment from start to finish)
    dict(
        name='Treatment_1',
        display_name="Full Game - All Treatments - All Preliminary Games",
        num_demo_participants=8,
        app_sequence=['app_0_dictator', 'app_1_ultimatum', 'app_2_jod', 'app_3_treatment1', 'app_4_treatment2a', 'app_5_treatment2b', 'app_6_treatment3'],
    ),

    # --- 2. DEBUG SESSIONS FOR PERSONALITY GAMES ---
    # (Use these to test the first 3 apps individually)
    dict(
        name='debug_dictator',
        display_name="DEBUG: App 0 - Dictator Game Only",
        num_demo_participants=2,
        app_sequence=['app_0_dictator'],
    ),
    dict(
        name='debug_ultimatum',
        display_name="DEBUG: App 1 - Ultimatum Game Only",
        num_demo_participants=2,
        app_sequence=['app_1_ultimatum'],
    ),
    dict(
        name='debug_jod',
        display_name="DEBUG: App 2 - Joy of Destruction Only",
        num_demo_participants=2,
        app_sequence=['app_2_jod'],
    ),

    # --- 3. DEBUG SESSIONS FOR MAIN EXPERIMENT TREATMENTS (NEW) ---
    # (Use these to jump directly to a specific treatment with fast timers)
    dict(
        name='debug_treatment_1',
        display_name="DEBUG: Treatment 1 Only (No Vote, 1s Slider)",
        num_demo_participants=5,
        app_sequence=['app_3_treatment1'],
        slider_timeout=1,
    ),
    dict(
        name='debug_treatment_2a',
        display_name="DEBUG: Treatment 2a Only (Vote-Out, 1s Slider)",
        num_demo_participants=5,
        app_sequence=['app_4_treatment2a'],
        slider_timeout=1,
    ),
    dict(
        name='debug_treatment_2b',
        display_name="DEBUG: Treatment 2b Only (Chaos, 1s Slider)",
        num_demo_participants=5,
        app_sequence=['app_5_treatment2b'],
        slider_timeout=1,
    ),
    dict(
        name='debug_treatment_3',
        display_name="DEBUG: Treatment 3 Only (Lame-Duck, 1s Slider)",
        num_demo_participants=5,
        app_sequence=['app_6_treatment3'],
        slider_timeout=1,
    ),
]

# --- Standard oTree Settings ---
LANGUAGE_CODE = 'en'
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'
SECRET_KEY = 'a-secret-key-for-testing'

INSTALLED_APPS = [
    'otree',
    'app_0_dictator', 
    'app_1_ultimatum', 
    'app_2_jod',
    'app_3_treatment1', 
    'app_4_treatment2a', 
    'app_5_treatment2b', 
    'app_6_treatment3',
]