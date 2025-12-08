from otree.api import *

# Defines constants for the app
class C(BaseConstants):
    # Sets the app's URL name
    NAME_IN_URL = 'app_1_ultimatum'
    # Sets the number of players in each group
    PLAYERS_PER_GROUP = 2
    # Sets the number of rounds for this app
    NUM_ROUNDS = 3
    # Sets the initial amount for the Proposer
    ULTIMATUM_ENDOWMENT = 100

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
        # Assigns the 'Proposer' role to the first player
        p1.game_role = 'Proposer'
        # Assigns the 'Responder' role to the second player
        p2.game_role = 'Responder'

# Defines group-level properties
class Group(BaseGroup):
    pass

# Defines player-level properties
class Player(BasePlayer):
    # Stores the player's role for the round
    game_role = models.StringField()
    # Stores the amount the Proposer offers
    ultimatum_offer = models.IntegerField(min=0, max=C.ULTIMATUM_ENDOWMENT, label="How many tokens to offer?")
    # Stores the Responder's accept/reject decision
    ultimatum_accepted = models.BooleanField(widget=widgets.RadioSelect, choices=[[True, 'Accept'], [False, 'Reject']])

# Defines the 'Offer' page
class Offer(Page):
    # Binds the page to the Player model
    form_model = 'player'
    # Specifies which player field is a form field on this page
    form_fields = ['ultimatum_offer']
    # Determines if the page is shown to a player
    @staticmethod
    def is_displayed(player: Player):
        # Shows page only if the player's role is 'Proposer'
        return player.game_role == 'Proposer'
    # Passes variables to the HTML template
    @staticmethod
    def vars_for_template(player: Player):
        # Passes the player's role to the template
        return dict(game_role=player.game_role)

# Defines a wait page for synchronization
class OfferWaitPage(WaitPage):
    pass

# Defines the 'Respond' page
class Respond(Page):
    # Binds the page to the Player model
    form_model = 'player'
    # Specifies which player field is a form field on this page
    form_fields = ['ultimatum_accepted']
    # Determines if the page is shown to a player
    @staticmethod
    def is_displayed(player: Player):
        # Shows page only if the player's role is 'Responder'
        return player.game_role == 'Responder'
    # Passes variables to the HTML template
    @staticmethod
    def vars_for_template(player: Player):
        # Gets the other player in the group (the Proposer)
        proposer = player.get_others_in_group()[0]
        # Passes the Proposer's offer and the player's role to the template
        return dict(offer=proposer.ultimatum_offer, game_role=player.game_role)

# Defines the 'ResultsWaitPage'
class ResultsWaitPage(WaitPage):
    # Function that runs after all players in a group arrive
    @staticmethod
    def after_all_players_arrive(group: Group):
        # Finds the player with the 'Proposer' role
        proposer = next(p for p in group.get_players() if p.game_role == 'Proposer')
        # Finds the player with the 'Responder' role
        responder = next(p for p in group.get_players() if p.game_role == 'Responder')

        # Gets the Proposer's offer amount
        offer = proposer.ultimatum_offer
        # Gets the Responder's decision
        accepted = responder.ultimatum_accepted
        # Checks if the offer was accepted
        if accepted:
            # Calculates payoffs if accepted
            proposer.payoff = C.ULTIMATUM_ENDOWMENT - offer
            responder.payoff = offer
        else:
            # Calculates payoffs if rejected
            proposer.payoff = 0
            responder.payoff = 0
            
        # Saves the Proposer's offer to a permanent participant variable
        proposer.participant.vars[f'ultimatum_offer_r{proposer.round_number}'] = offer
        # Saves the Responder's decision to a permanent participant variable
        responder.participant.vars[f'ultimatum_accepted_r{responder.round_number}'] = accepted

# Defines the 'Results' page
class Results(Page):
    pass

# Defines the order of pages in the app
page_sequence = [Offer, OfferWaitPage, Respond, ResultsWaitPage, Results]