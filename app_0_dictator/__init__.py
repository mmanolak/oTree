from otree.api import *

# Defines constants for the app
class C(BaseConstants):
    # Sets the app's URL name
    NAME_IN_URL = 'app_0_dictator'
    # Sets the number of players in each group
    PLAYERS_PER_GROUP = 2
    # Sets the number of rounds for this app
    NUM_ROUNDS = 3
    # Sets the initial amount for the Dictator
    DICTATOR_ENDOWMENT = 100

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
        # Assigns the 'Dictator' role to the first player
        p1.game_role = 'Dictator'
        # Assigns the 'Recipient' role to the second player
        p2.game_role = 'Recipient'

# Defines group-level properties
class Group(BaseGroup):
    pass

# Defines player-level properties
class Player(BasePlayer):
    # Stores the player's role for the round
    game_role = models.StringField()
    # Stores the amount the Dictator sends
    dictator_send = models.IntegerField(min=0, max=C.DICTATOR_ENDOWMENT, label=f"How many tokens (0-{C.DICTATOR_ENDOWMENT}) do you want to send?")

# Defines the 'Decision' page
class Decision(Page):
    # Binds the page to the Player model
    form_model = 'player'
    # Specifies which player field is a form field on this page
    form_fields = ['dictator_send']
    # Determines if the page is shown to a player
    @staticmethod
    def is_displayed(player: Player):
        # Shows page only if the player's role is 'Dictator'
        return player.game_role == 'Dictator'
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
        # Finds the player with the 'Dictator' role
        dictator = next(p for p in group.get_players() if p.game_role == 'Dictator')
        # Finds the player with the 'Recipient' role
        recipient = next(p for p in group.get_players() if p.game_role == 'Recipient')
        
        # Gets the amount sent by the Dictator
        sent = dictator.dictator_send
        # Calculates the Dictator's payoff
        dictator.payoff = C.DICTATOR_ENDOWMENT - sent
        # Calculates the Recipient's payoff
        recipient.payoff = sent
        
        # Saves the amount sent to a permanent participant variable
        dictator.participant.vars[f'dictator_send_r{dictator.round_number}'] = sent

# Defines the 'Results' page
class Results(Page):
    pass

# Defines the order of pages in the app
page_sequence = [Decision, ResultsWaitPage, Results]