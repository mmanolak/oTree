
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

doc = '2-player ultimatum game, 3 rounds, random rematching each round.'
class C(BaseConstants):
    NAME_IN_URL = 'ultimatum'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 3
class Subsession(BaseSubsession):
    pass
class Group(BaseGroup):
    endowment = models.IntegerField(initial=10)
class Player(BasePlayer):
    offer = models.IntegerField()
    accept = models.BooleanField()
    is_proposer = models.BooleanField()
    temp_name = models.StringField(label='Please enter your first name.')
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
    
class EnterName(Page):
    form_model = 'player'
    form_fields = ['temp_name']
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        participant = player.participant
        
        # store the entered name on the participant object so it persists across apps
        player.participant.display_name = player.temp_name
        
class UG_Instructions(Page):
    form_model = 'player'
    @staticmethod
    def is_displayed(player: Player):
        
        # skip instructions in later rounds; show only in round 1
        return player.round_number == 1
        
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        group = player.group
        
        # assign roles randomly each round: 1 proposer, 1 responder
        import random
        players = player.group.get_players()
        proposer = random.choice(players)
        for p in players:
            p.is_proposer = (p == proposer)
        
class UG_Decision(Page):
    form_model = 'player'
    form_fields = ['offer', 'accept']
    @staticmethod
    def get_form_fields(player: Player):
        
        if player.is_proposer:
            return ["offer"]
        else:
            return ["accept"]
        
    @staticmethod
    def is_displayed(player: Player):
        
        if player.is_proposer:
            # proposer chooses offer only
            return True
        # responder chooses accept only
        return True
        
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        group = player.group
        
        other = player.get_others_in_group()[0]
        endowment = player.group.endowment
        
        if player.is_proposer:
            # wait for responder's decision
            return
        
        # this block runs for responder after they submit 'accept'
        proposer = other
        responder = player
        
        if responder.accept:
            proposer.payoff = endowment - proposer.offer
            responder.payoff = proposer.offer
        else:
            proposer.payoff = 0
            responder.payoff = 0
        
class UG_WaitForOther(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        session = group.session
        
        # grouping is handled in creating_session
        pass
        
class UG_Results(Page):
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
            player.participant.total_ultimatum = total
        
page_sequence = [EnterName, UG_Instructions, UG_Decision, UG_WaitForOther, UG_Results]