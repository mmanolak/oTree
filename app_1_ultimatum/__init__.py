from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'app_1_ultimatum'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 3
    ULTIMATUM_ENDOWMENT = 100

class Subsession(BaseSubsession):
    pass

def creating_session(subsession: Subsession):
    subsession.group_randomly()
    for group in subsession.get_groups():
        p1, p2 = group.get_players()
        p1.game_role = 'Proposer'
        p2.game_role = 'Responder'

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    game_role = models.StringField()
    ultimatum_offer = models.IntegerField(min=0, max=C.ULTIMATUM_ENDOWMENT, label="How many tokens to offer?")
    ultimatum_accepted = models.BooleanField(widget=widgets.RadioSelect, choices=[[True, 'Accept'], [False, 'Reject']])

class Offer(Page):
    form_model = 'player'
    form_fields = ['ultimatum_offer']
    @staticmethod
    def is_displayed(player: Player):
        return player.game_role == 'Proposer'
    @staticmethod
    def vars_for_template(player: Player):
        return dict(game_role=player.game_role)

class OfferWaitPage(WaitPage):
    pass

class Respond(Page):
    form_model = 'player'
    form_fields = ['ultimatum_accepted']
    @staticmethod
    def is_displayed(player: Player):
        return player.game_role == 'Responder'
    @staticmethod
    def vars_for_template(player: Player):
        proposer = player.get_others_in_group()[0]
        return dict(offer=proposer.ultimatum_offer, game_role=player.game_role)

class ResultsWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        proposer = next(p for p in group.get_players() if p.game_role == 'Proposer')
        responder = next(p for p in group.get_players() if p.game_role == 'Responder')

        offer = proposer.ultimatum_offer
        accepted = responder.ultimatum_accepted
        if accepted:
            proposer.payoff = C.ULTIMATUM_ENDOWMENT - offer
            responder.payoff = offer
        else:
            proposer.payoff = 0
            responder.payoff = 0
            
        # CORRECTED LINES: Use participant.vars
        proposer.participant.vars[f'ultimatum_offer_r{proposer.round_number}'] = offer
        responder.participant.vars[f'ultimatum_accepted_r{responder.round_number}'] = accepted

class Results(Page):
    pass

page_sequence = [Offer, OfferWaitPage, Respond, ResultsWaitPage, Results]