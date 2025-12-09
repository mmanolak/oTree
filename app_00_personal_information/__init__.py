from otree.api import *

doc = "A simple, one-page app to collect the participant's name and set it as their label."

class C(BaseConstants):
    NAME_IN_URL = 'floating_rotation'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    # This field will store the name they enter.
    # We add a label to the form and specify that the field is required.
    player_name = models.StringField(
        label="Please enter your first name or a nickname:",
        blank=False # This makes the field required
    )

class NamePage(Page):
    form_model = 'player'
    form_fields = ['player_name']

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        # This is the key step. We take the name the player entered
        # and save it to the special 'participant.label' field.
        player.participant.label = player.player_name
        
        
page_sequence = [NamePage]