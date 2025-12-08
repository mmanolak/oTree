
from otree.api import (
    Currency,
    cu,
    currency_range,
    models,
    widgets,
    BaseConstants,
    BaseSubsession,
    BaseGroup,
    BasePlayer,
    ExtraModel,
    WaitPage,
    Page,
    read_csv,
)

import units
import shared_out

doc = '2-player joy-of-destruction game, 3 rounds, random rematching each round.'
class C(BaseConstants):
    NAME_IN_URL = 'joy_of_destruction'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 3
class Subsession(BaseSubsession):
    pass
class Group(BaseGroup):
    endowment = models.IntegerField(initial=10)
class Player(BasePlayer):
    destroy_amount = models.IntegerField()
def creating_session(subsession: Subsession):
    
    players = subsession.get_players()
    num_players = len(players)
    assert num_players % 2 == 0, 'Number of players must be even.'
    
    if subsession.round_number == 1:
        subsession.group_randomly()
    else:
        import random
        players_copy = players.copy()
        random.shuffle(players_copy)
    
        matrix = []
        while players_copy:
            p1 = players_copy.pop()
            partner = None
            for candidate in players_copy:
                if not any(prev_p.id_in_subsession == candidate.id_in_subsession for prev_p in p1.in_previous_rounds()):
                    partner = candidate
                    break
            if partner is None:
                partner = players_copy[0]
            players_copy.remove(partner)
            matrix.append([p1.id_in_subsession, partner.id_in_subsession])
    
        subsession.set_group_matrix(matrix)
    
class JOD_Instructions(Page):
    form_model = 'player'
class JOD_Decision(Page):
    form_model = 'player'
    form_fields = ['destroy_amount']
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        group = player.group
        
        other = player.get_others_in_group()[0]
        endowment = player.group.endowment
        
        # both choose destroy_amount; payoff is symmetric and depends on both
        if other.destroy_amount is None:
            # wait until other has submitted
            return
        
        a = player.destroy_amount
        b = other.destroy_amount
        
        player.payoff = endowment - a - b
        other.payoff = endowment - a - b
        
class JOD_WaitForOther(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        session = group.session
        
        # grouping is handled in creating_session
        pass
        
class JOD_Results(Page):
    form_model = 'player'
    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        
        other = player.get_others_in_group()[0]
        return dict(other=other)
        
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        participant = player.participant
        
        if player.round_number == C.NUM_ROUNDS:
            total = sum(p.payoff for p in player.in_all_rounds())
            player.participant.total_jod = total
        
page_sequence = [JOD_Instructions, JOD_Decision, JOD_WaitForOther, JOD_Results]