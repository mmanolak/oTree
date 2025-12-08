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
    'assigned_treatment', # Simplified this field name
]

# --- List of the 4 treatment apps for random assignment ---
TREATMENT_APPS = ['app_3_treatment1', 'app_4_treatment2a', 'app_5_treatment2b', 'app_6_treatment3']

SESSION_CONFIGS = [
    # --- 1. THE SINGLE FULL EXPERIMENT CONFIGURATION ---
    dict(
        name='Full_Experiment',
        display_name="Full Experiment (Random Treatment)",
        num_demo_participants=8,
        app_sequence=['app_0_dictator', 'app_1_ultimatum', 'app_2_jod', 'app_4_treatment2a'],
    ),

    # --- 2. DEBUG SESSIONS ---
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
        num_demo_participants=5,
        app_sequence=['app_3_treatment1'],
        slider_task_timeout=15,
    ),
    dict(
        name='debug_treatment_2a',
        display_name="DEBUG: Treatment 2a Only",
        num_demo_participants=5,
        app_sequence=['app_4_treatment2a'],
        slider_task_timeout=15,
    ),
    dict(
        name='debug_treatment_2b',
        display_name="DEBUG: Treatment 2b Only",
        num_demo_participants=5,
        app_sequence=['app_5_treatment2b'],
        slider_task_timeout=15,
    ),
    dict(
        name='debug_treatment_3',
        display_name="DEBUG: Treatment 3 Only",
        num_demo_participants=5,
        app_sequence=['app_6_treatment3'],
        slider_task_timeout=15,
    ),
    dict(
        name='debug_voting',
        display_name="DEBUG: Voting Assignment Only",
        num_demo_participants=5,
        app_sequence=['floating_rotation'],
        slider_task_timeout=15,
    ),
]

# --- oTree Customization for Random Treatment Assignment ---
import random
def app_after_this_page(player, upcoming_apps):
    # This function is now only called at the end of the 'dispatcher' app
    if player.subsession.app_name == 'dispatcher':
        
        # Randomly choose one of the REAL treatment apps
        assigned_treatment = random.choice(TREATMENT_APPS)
        
        # Store the assigned treatment on the participant
        player.participant.assigned_treatment = assigned_treatment
        
        # Tell oTree to send this player to that app next
        return assigned_treatment

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
    'dispatcher',
    'app_3_treatment1', 
    'app_4_treatment2a', 
    'app_5_treatment2b', 
    'app_6_treatment3',
    'floating_rotation',
]