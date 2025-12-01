SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.0, 
    participation_fee=0.0
)

PARTICIPANT_FIELDS = [
    'dictator_send_r1', 'dictator_send_r2', 'dictator_send_r3',
    'ultimatum_offer_r1', 'ultimatum_offer_r2', 'ultimatum_offer_r3',
    'ultimatum_accepted_r1', 'ultimatum_accepted_r2', 'ultimatum_accepted_r3',
    'jod_destroy_r1', 'jod_destroy_r2', 'jod_destroy_r3',
    'is_representative',
    'game_role',
]

SESSION_CONFIGS = [
    dict(
        name='Full_Game_Lame_Duck_Experiment',
        display_name="Full Game - Lame Duck Experiment",
        num_demo_participants=8,
        app_sequence=['app_0_dictator', 'app_1_ultimatum', 'app_2_jod', 'app_3_main_experiment'],
        treatment='T3'
    ),
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
        name='debug_main_experiment_T1',
        display_name="DEBUG: Main Experiment Only (T1 Rules)",
        num_demo_participants=4,
        app_sequence=['app_3_main_experiment'],
        treatment='T1'
    ),
    dict(
        name='DEV_Full_Game',
        display_name="DEV MODE: Full Game (T3 Rules, Fast Timers)",
        num_demo_participants=8,
        app_sequence=['app_0_dictator', 'app_1_ultimatum', 'app_2_jod', 'app_3_main_experiment'],
        treatment='T3',
        use_browser_bots=True 
    ),
]

LANGUAGE_CODE = 'en'
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True
DEMO_PAGE_INTRO_HTML = ''
SESSION_FIELDS = []
ROOMS = []

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'

SECRET_KEY = 'a-secret-key-for-testing'

INSTALLED_APPS = [
    'otree',
    'app_0_dictator',
    'app_1_ultimatum',
    'app_2_jod',
    'app_3_main_experiment',
]
