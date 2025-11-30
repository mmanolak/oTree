from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'app_2_jod'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 3
    JOD_ENDOWMENT = 100
    JOD_COST = 10
    JOD_HARM = 50

class Subsession(BaseSubsession):
    pass

def creating_session(subsession: Subsession):
    subsession.group_randomly()
    for group in subsession.get_groups():
        p1, p2 = group.get_players()
        p1.game_role = 'Destroyer'
        p2.game_role = 'Target'

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    game_role = models.StringField()
    jod_destroy = models.BooleanField(label="Choose an action:", widget=widgets.RadioSelect, choices=[[False, "Do nothing"], [True, f"Pay {C.JOD_COST} to reduce their earnings by {C.JOD_HARM}"]])

class Decision(Page):
    form_model = 'player'
    form_fields = ['jod_destroy']
    @staticmethod
    def is_displayed(player: Player):
        return player.game_role == 'Destroyer'
    @staticmethod
    def vars_for_template(player: Player):
        return dict(game_role=player.game_role)

class ResultsWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        destroyer = next(p for p in group.get_players() if p.game_role == 'Destroyer')
        target = next(p for p in group.get_players() if p.game_role == 'Target')

        destroyed = destroyer.jod_destroy
        if destroyed:
            destroyer.payoff = C.JOD_ENDOWMENT - C.JOD_COST
            target.payoff = C.JOD_ENDOWMENT - C.JOD_HARM
        else:
            destroyer.payoff = C.JOD_ENDOWMENT
            target.payoff = C.JOD_ENDOWMENT
            
        # CORRECTED LINE: Use participant.vars
        destroyer.participant.vars[f'jod_destroy_r{destroyer.round_number}'] = destroyed


class Results(Page):
    pass

page_sequence = [Decision, ResultsWaitPage, Results]