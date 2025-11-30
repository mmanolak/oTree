from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'app_0_dictator'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 3
    DICTATOR_ENDOWMENT = 100

class Subsession(BaseSubsession):
    pass

def creating_session(subsession: Subsession):
    subsession.group_randomly()
    for group in subsession.get_groups():
        p1, p2 = group.get_players()
        p1.game_role = 'Dictator'
        p2.game_role = 'Recipient'

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    game_role = models.StringField()
    dictator_send = models.IntegerField(min=0, max=C.DICTATOR_ENDOWMENT, label=f"How many tokens (0-{C.DICTATOR_ENDOWMENT}) do you want to send?")

class Decision(Page):
    form_model = 'player'
    form_fields = ['dictator_send']
    @staticmethod
    def is_displayed(player: Player):
        return player.game_role == 'Dictator'
    @staticmethod
    def vars_for_template(player: Player):
        return dict(game_role=player.game_role)

class ResultsWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        dictator = next(p for p in group.get_players() if p.game_role == 'Dictator')
        recipient = next(p for p in group.get_players() if p.game_role == 'Recipient')
        
        sent = dictator.dictator_send
        dictator.payoff = C.DICTATOR_ENDOWMENT - sent
        recipient.payoff = sent
        
        # CORRECTED LINE: Use participant.vars
        dictator.participant.vars[f'dictator_send_r{dictator.round_number}'] = sent

class Results(Page):
    pass

page_sequence = [Decision, ResultsWaitPage, Results]