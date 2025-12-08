from otree.api import *

# Defines constants for the app
class C(BaseConstants):
    # Sets the app's URL name
    NAME_IN_URL = 'app_2_jod'
    # Sets the number of players in each group
    PLAYERS_PER_GROUP = 2
    # Sets the number of rounds for this app
    NUM_ROUNDS = 3
    # Sets the initial amount for each player
    JOD_ENDOWMENT = 100
    # Sets the cost for the Destroyer to act
    JOD_COST = 10
    # Sets the amount of harm done to the Target
    JOD_HARM = 50

# Defines subsession-level properties
class Subsession(BaseSubsession):
    pass

# Function that runs at the beginning of each round
def creating_session(subsession: Subsession):
    # Randomly assigns players to new groups
    subsession.group_randomly()
    # Loops through each newly created group
    for group in subsession.get_groups():
        # Gets the two players in the group
        p1, p2 = group.get_players()
        # Assigns the 'Destroyer' role to the first player
        p1.game_role = 'Destroyer'
        # Assigns the 'Target' role to the second player
        p2.game_role = 'Target'

# Defines group-level properties
class Group(BaseGroup):
    pass

# Defines player-level properties
class Player(BasePlayer):
    # Stores the player's role for the round
    game_role = models.StringField()
    # Stores the Destroyer's destroy/do nothing decision
    jod_destroy = models.BooleanField(label="Choose an action:", widget=widgets.RadioSelect, choices=[[False, "Do nothing"], [True, f"Pay {C.JOD_COST} to reduce their earnings by {C.JOD_HARM}"]])

# Defines the 'Decision' page
class Decision(Page):
    # Binds the page to the Player model
    form_model = 'player'
    # Specifies which player field is a form field on this page
    form_fields = ['jod_destroy']
    # Determines if the page is shown to a player
    @staticmethod
    def is_displayed(player: Player):
        # Shows page only if the player's role is 'Destroyer'
        return player.game_role == 'Destroyer'
    # Passes variables to the HTML template
    @staticmethod
    def vars_for_template(player: Player):
        # Passes the player's role to the template
        return dict(game_role=player.game_role)

# Defines the 'ResultsWaitPage'
class ResultsWaitPage(WaitPage):
    # Function that runs after all players in a group arrive
    @staticmethod
    def after_all_players_arrive(group: Group):
        # Finds the player with the 'Destroyer' role
        destroyer = next(p for p in group.get_players() if p.game_role == 'Destroyer')
        # Finds the player with the 'Target' role
        target = next(p for p in group.get_players() if p.game_role == 'Target')

        # Gets the Destroyer's decision
        destroyed = destroyer.jod_destroy
        # Checks if the Destroyer chose to destroy
        if destroyed:
            # Calculates payoffs if destroyed
            destroyer.payoff = C.JOD_ENDOWMENT - C.JOD_COST
            target.payoff = C.JOD_ENDOWMENT - C.JOD_HARM
        else:
            # Calculates payoffs if not destroyed
            destroyer.payoff = C.JOD_ENDOWMENT
            target.payoff = C.JOD_ENDOWMENT
            
        # Saves the Destroyer's decision to a permanent participant variable
        destroyer.participant.vars[f'jod_destroy_r{destroyer.round_number}'] = destroyed

# Defines the 'Results' page
class Results(Page):
    pass

# Defines the order of pages in the app
page_sequence = [Decision, ResultsWaitPage, Results]