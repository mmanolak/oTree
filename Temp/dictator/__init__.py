
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

doc = '2-player dictator game, 3 rounds, random rematching each round.'
class C(BaseConstants):
    NAME_IN_URL = 'dictator'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 3
class Subsession(BaseSubsession):
    pass
class Group(BaseGroup):
    endowment = models.IntegerField(initial=10)
class Player(BasePlayer):
    give_amount = models.IntegerField()
    is_dictator = models.BooleanField()
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
    
class DG_Instructions(Page):
    form_model = 'player'
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        group = player.group
        
        # assign dictator randomly each round
        import random
        players = player.group.get_players()
        dictator = random.choice(players)
        for p in players:
            p.is_dictator = (p == dictator)
        
class DG_Decision(Page):
    form_model = 'player'
    form_fields = ['give_amount']
    @staticmethod
    def is_displayed(player: Player):
        
        # only dictator makes a decision
        return player.is_dictator
        
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        group = player.group
        
        other = player.get_others_in_group()[0]
        endowment = player.group.endowment
        
        dictator = player
        recipient = other
        
        dictator.payoff = endowment - dictator.give_amount
        recipient.payoff = dictator.give_amount
        
class DG_WaitForOther(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        session = group.session
        
        # grouping is handled in creating_session
        pass
        
class DG_Results(Page):
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
            player.participant.total_dictator = total
        
page_sequence = [DG_Instructions, DG_Decision, DG_WaitForOther, DG_Results]