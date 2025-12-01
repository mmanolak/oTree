SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.0, 
    participation_fee=0.0
)

PARTICIPANT_FIELDS = [
    'display_name',
    'dictator_send',
    'jod_destroy',
    'ultimatum_offer',
    'ultimatum_accepted',
]


SESSION_CONFIGS = [
    dict(
        name='T1_NoVote',
        display_name="Treatment 1 (No Vote Term Limit)",
        num_demo_participants=4,
        app_sequence=['app_0_dictator', 'app_1_ultimatum', 'app_2_jod', 'app_3_main_experiment'],
        treatment='T1'
    ),
    dict(
        name='T2a_VoteOut',
        display_name="Treatment 2a (Removal by Popular Vote)",
        num_demo_participants=4,
        app_sequence=['app_0_dictator', 'app_1_ultimatum', 'app_2_jod', 'app_3_main_experiment'],
        treatment='T2a'
    ),
    dict(
        name='T2b_DumbLuck',
        display_name="Treatment 2b (Probabilistic Removal)",
        num_demo_participants=4,
        app_sequence=['app_0_dictator', 'app_1_ultimatum', 'app_2_jod', 'app_3_main_experiment'],
        treatment='T2b'
    ),
    dict(
        name='T3_LameDuck',
        display_name="Treatment 3 (Removal by Term Limit)",
        num_demo_participants=4,
        app_sequence=['app_0_dictator', 'app_1_ultimatum', 'app_2_jod', 'app_3_main_experiment'],
        treatment='T3'
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