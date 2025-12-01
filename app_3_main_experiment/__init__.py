from otree.api import *
import random

class C(BaseConstants):
    NAME_IN_URL = 'app_3_main_experiment'
    PLAYERS_PER_GROUP = 4
    NUM_ROUNDS = 3
    VOTERS_PER_GROUP = 3
    REP_SALARY = 250  # As requested, changed from 150
    STAGE_2_COST = 50
    # New constants for slider task payoffs
    VOTER_SUCCESS_PAYOFF = 5
    REP_SUCCESS_PAYOFF = 50

class Subsession(BaseSubsession):
    # Field to carry over productivity state between rounds
    productivity_pr = models.FloatField(initial=50)
    productivity_pv = models.FloatField(initial=5)

def creating_session(subsession: Subsession):
    # In Round 1, assign roles that will be fixed for the entire experiment
    if subsession.round_number == 1:
        subsession.group_randomly()
        for group in subsession.get_groups():
            players = group.get_players()
            # Randomly select one player to be the Representative
            rep = random.choice(players)
            rep.participant.is_representative = True
            rep.participant.game_role = 'Representative'
            # All other players are Voters
            for p in players:
                if p.id_in_group != rep.id_in_group:
                    p.participant.is_representative = False
                    p.participant.game_role = 'Voter'
    else:
        subsession.group_like_round(1)
        # Carry over the productivity state from the previous round
        prev_subsession = subsession.in_round(subsession.round_number - 1)
        subsession.productivity_pr = prev_subsession.productivity_pr
        subsession.productivity_pv = prev_subsession.productivity_pv

    # In every round, copy the fixed role from the participant to the player
    for player in subsession.get_players():
        player.is_representative = player.participant.is_representative
        player.game_role = player.participant.game_role

class Group(BaseGroup):
    num_remove_votes = models.IntegerField(initial=0)
    collective_pot = models.FloatField(initial=0)

class Player(BasePlayer):
    is_representative = models.BooleanField()
    game_role = models.StringField() # For displaying the label
    slider_score = models.IntegerField(initial=0)
    vote_to_remove = models.BooleanField(choices=[[True, 'Vote to Remove'], [False, 'Vote to Retain']], label="What is your vote?", widget=widgets.RadioSelect)
    was_removed = models.BooleanField(initial=False)
    removal_mechanism = models.StringField()
    stage2_decision = models.StringField(choices=['Sabotage', 'Help', 'Neutral'])

# --- HELPER FUNCTIONS ---
def get_voters(group: Group):
    return [p for p in group.get_players() if not p.is_representative]

def get_representative(group: Group):
    return next(p for p in group.get_players() if p.is_representative)

# --- PAGES ---
class Introduction(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

class SliderTask(Page):
    form_model = 'player'
    form_fields = ['slider_score']
    timeout_seconds = 60
    
    @staticmethod
    def is_displayed(player: Player):
        if player.is_representative:
            # A removed representative should not see this page in subsequent rounds
            if player.round_number > 1:
                return not player.in_round(player.round_number - 1).was_removed
        return True

class ResultsWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        rep = get_representative(group)
        voters = get_voters(group)
        
        # Calculate pot contributions based on slider scores
        pot = (
            rep.slider_score * C.REP_SUCCESS_PAYOFF + 
            sum(p.slider_score for p in voters) * C.VOTER_SUCCESS_PAYOFF
        )
        group.collective_pot = pot
        
        # Voters get an equal share of the pot
        for p in voters:
            p.payoff = pot / C.VOTERS_PER_GROUP
        
        # Representative gets their fixed salary
        rep.payoff = C.REP_SALARY

class Vote(Page):
    form_model = 'player'
    form_fields = ['vote_to_remove']
    
    @staticmethod
    def is_displayed(player: Player):
        is_voting_treatment = player.session.config['treatment'] != 'T1'
        # Also, don't show if the Rep was already removed in a previous round
        rep_was_removed = False
        if player.round_number > 1:
            rep = get_representative(player.group)
            rep_was_removed = rep.in_round(player.round_number - 1).was_removed
        
        return not player.is_representative and is_voting_treatment and not rep_was_removed

class VoteWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        treatment = group.session.config['treatment']
        rep = get_representative(group)
        
        # Only run voting logic if the rep hasn't already been removed
        if not any(p.was_removed for p in rep.in_previous_rounds()):
            if treatment != 'T1':
                votes = [p.vote_to_remove for p in get_voters(group) if p.vote_to_remove is not None]
                group.num_remove_votes = sum(votes)
            
            if treatment == 'T1' and group.round_number == C.NUM_ROUNDS:
                rep.was_removed = True
                rep.removal_mechanism = 'no_vote_term_limit'
            elif treatment == 'T2a' and group.num_remove_votes >= 2:
                rep.was_removed = True
                rep.removal_mechanism = 'voted_out'
            elif treatment == 'T2b':
                voted_out = group.num_remove_votes >= 2
                if voted_out and random.random() < 0.90:
                    rep.was_removed = True
                    rep.removal_mechanism = 'voted_out_probabilistic'
                elif not voted_out and random.random() < 0.10:
                    rep.was_removed = True
                    rep.removal_mechanism = 'unlucky_winner'
            elif treatment == 'T3':
                if group.round_number < C.NUM_ROUNDS and group.num_remove_votes >= 2:
                    rep.was_removed = True
                    rep.removal_mechanism = 'voted_out_early'
                elif group.round_number == C.NUM_ROUNDS:
                    rep.was_removed = True
                    rep.removal_mechanism = 'term_limit'

class RoundResults(Page):
    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        rep = get_representative(group)
        voters = get_voters(group)
        
        return {
            'representative_score': rep.slider_score,
            'my_score': player.slider_score,
            'collective_pot': group.collective_pot,
        }

class Stage2Decision(Page):
    form_model = 'player'
    form_fields = ['stage2_decision']
    
    @staticmethod
    def is_displayed(player: Player):
        if player.round_number != C.NUM_ROUNDS: return False
        if not player.is_representative: return False
        return any(p.was_removed for p in player.in_all_rounds())

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        decision = player.stage2_decision
        subsession = player.subsession
        
        if decision == 'Sabotage':
            player.payoff -= C.STAGE_2_COST
            # Halve the productivity parameters for the next subsession/group
            subsession.productivity_pr *= 0.5
            subsession.productivity_pv *= 0.5
        elif decision == 'Help':
            player.payoff -= C.STAGE_2_COST
            # Increase productivity parameters by 50%
            subsession.productivity_pr *= 1.5
            subsession.productivity_pv *= 1.5

class FinalResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

page_sequence = [
    Introduction,
    SliderTask,
    ResultsWaitPage,
    Vote,
    VoteWaitPage,
    RoundResults,
    Stage2Decision,
    FinalResults,
]