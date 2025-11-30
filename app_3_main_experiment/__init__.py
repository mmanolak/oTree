from otree.api import *
import random


class C(BaseConstants):
    NAME_IN_URL = 'app_1_main_experiment'
    PLAYERS_PER_GROUP = 4
    NUM_ROUNDS = 3
    VOTERS_PER_GROUP = 3
    REPRESENTATIVES_PER_GROUP = 1
    REP_SALARY = 150
    STAGE_2_COST = 50

class Subsession(BaseSubsession):
    pass

def creating_session(subsession: Subsession):
    if subsession.round_number == 1:
        subsession.group_randomly()
        for group in subsession.get_groups():
            players = group.get_players()
            rep = players[0]
            rep.is_representative = True
            for i in range(1, len(players)):
                players[i].is_representative = False
    else:
        subsession.group_like_round(1)

class Group(BaseGroup):
    num_remove_votes = models.IntegerField()
    collective_pot = models.FloatField()
    productivity_state_pr = models.FloatField(initial=50)
    productivity_state_pv = models.FloatField(initial=5)

class Player(BasePlayer):
    is_representative = models.BooleanField(initial=False)
    slider_score = models.IntegerField(initial=0)
    vote_to_remove = models.BooleanField(choices=[[True, 'Vote to Remove'], [False, 'Vote to Retain']], label="What is your vote?", widget=widgets.RadioSelect)
    was_removed = models.BooleanField(initial=False)
    removal_mechanism = models.StringField()
    stage2_decision = models.StringField(choices=['Sabotage', 'Help', 'Neutral'])

def get_voters(group: Group):
    return [p for p in group.get_players() if not p.is_representative]

def get_representative(group: Group):
    return group.get_player_by(is_representative=True)

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
        if player.is_representative and player.round_number > 1:
            return not player.in_round(player.round_number - 1).was_removed
        return True
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if player.id_in_group == C.PLAYERS_PER_GROUP:
            group = player.group
            representative_score = get_representative(group).slider_score
            voter_scores = [p.slider_score for p in get_voters(group)]
            pot = (group.productivity_state_pr * representative_score + group.productivity_state_pv * sum(voter_scores))
            group.collective_pot = pot
            for p in get_voters(group):
                p.payoff = pot / C.VOTERS_PER_GROUP

class Vote(Page):
    form_model = 'player'
    form_fields = ['vote_to_remove']
    @staticmethod
    def is_displayed(player: Player):
        is_voting_treatment = player.session.config['treatment'] != 'T1'
        return not player.is_representative and is_voting_treatment

class VoteWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        treatment = group.session.config['treatment']
        rep = get_representative(group)
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
            if group.num_remove_votes >= 2:
                if random.random() < 0.90:
                    rep.was_removed = True
                    rep.removal_mechanism = 'voted_out_probabilistic'
            else:
                if random.random() < 0.10:
                    rep.was_removed = True
                    rep.removal_mechanism = 'unlucky_winner'
        elif treatment == 'T3':
            if group.round_number < C.NUM_ROUNDS and group.num_remove_votes >= 2:
                rep.was_removed = True
                rep.removal_mechanism = 'voted_out'
            elif group.round_number == C.NUM_ROUNDS:
                rep.was_removed = True
                rep.removal_mechanism = 'term_limit'
        was_removed_last_round = False
        if group.round_number > 1:
            was_removed_last_round = rep.in_round(group.round_number - 1).was_removed
        if not was_removed_last_round:
            rep.payoff = C.REP_SALARY

class RoundResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        if player.is_representative and player.round_number > 1:
            return not player.in_round(player.round_number - 1).was_removed
        return True

class Stage2Decision(Page):
    form_model = 'player'
    form_fields = ['stage2_decision']
    @staticmethod
    def is_displayed(player: Player):
        if player.round_number != C.NUM_ROUNDS:
            return False
    
        if not player.is_representative:
            return False
    
        was_removed_at_any_point = any(p.was_removed for p in player.in_all_rounds())
    
        return was_removed_at_any_point
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        group = player.group
        decision = player.stage2_decision
        if decision == 'Sabotage':
            group.productivity_state_pr *= 0.5
            group.productivity_state_pv *= 0.5
            player.payoff -= C.STAGE_2_COST
        elif decision == 'Help':
            if group.round_number > 1 and group.in_round(group.round_number - 1).productivity_state_pr < 50:
                group.productivity_state_pr = 50
                group.productivity_state_pv = 5
            else:
                group.productivity_state_pr *= 1.5
                group.productivity_state_pv *= 1.5
            player.payoff -= C.STAGE_2_COST

class FinalResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

page_sequence = [
    Introduction,
    SliderTask,
    Vote,
    VoteWaitPage,
    RoundResults,
    Stage2Decision,
    FinalResults,
]