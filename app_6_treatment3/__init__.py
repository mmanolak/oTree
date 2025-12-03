from otree.api import *
import random

class C(BaseConstants):
    NAME_IN_URL = 'app_6_treatment3'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 20
    VOTERS_PER_GROUP = 3
    REP_SALARY = 250
    STAGE_2_COST = 50
    VOTER_SUCCESS_PAYOFF = 5
    REP_SUCCESS_PAYOFF = 50
    TERM_LENGTH = 3
    START_OF_INDEFINITE_HORIZON = 7
    CONTINUATION_PROB = 0.80

class Subsession(BaseSubsession):
    pass

def creating_session(subsession: Subsession):
    session = subsession.session
    if subsession.round_number == 1:
        players = subsession.get_players()
        random.shuffle(players)
        voter_players = players[:C.VOTERS_PER_GROUP]
        session.vars['voter_pids'] = [p.participant.id for p in voter_players]
        rep_pool_players = players[C.VOTERS_PER_GROUP:]
        session.vars['rep_pool_pids'] = [p.participant.id for p in rep_pool_players]
        session.vars['game_over'] = False
        session.vars['game_over_reason'] = ""
        session.vars['removed_reps_info'] = []
        session.vars['term_round'] = 0
        if session.vars['rep_pool_pids']:
            session.vars['current_rep_pid'] = session.vars['rep_pool_pids'].pop(0)
            session.vars['term_round'] = 1
        else:
            session.vars['game_over'] = True
            session.vars['game_over_reason'] = "Not enough players for a Representative."

    voter_pids = session.vars['voter_pids']
    current_rep_pid = session.vars.get('current_rep_pid')
    for p in subsession.get_players():
        pid = p.participant.id
        if pid in voter_pids: p.game_role = "Voter"
        elif pid == current_rep_pid: p.game_role = "Representative"
        else: p.game_role = "Inactive"
    
    active_group = [p for p in subsession.get_players() if p.game_role in ["Voter", "Representative"]]
    inactive_players = [p for p in subsession.get_players() if p.game_role == "Inactive"]
    group_matrix = []
    if active_group: group_matrix.append(active_group)
    for p in inactive_players: group_matrix.append([p])
    subsession.set_group_matrix(group_matrix)

class Group(BaseGroup):
    num_remove_votes = models.IntegerField(initial=0)
    collective_pot = models.FloatField(initial=0)

class Player(BasePlayer):
    is_representative = models.BooleanField()
    game_role = models.StringField()
    slider_score = models.IntegerField(initial=0)
    vote_to_remove = models.BooleanField(choices=[[True, 'Vote to Remove'], [False, 'Vote to Retain']], widget=widgets.RadioSelect)
    was_removed = models.BooleanField(initial=False)
    removal_mechanism = models.StringField()
    stage2_decision = models.IntegerField(widget=widgets.RadioSelect, choices=[[1, 'Sabotage'], [2, 'Help'], [0, 'Neutral']])

def get_voters(group: Group): return [p for p in group.get_players() if p.game_role == 'Voter']
def get_representative(group: Group):
    for p in group.get_players():
        if p.game_role == 'Representative': return p
    return None

# --- GAMEPLAY PAGES ---
class Introduction(Page):
    @staticmethod
    def is_displayed(player: Player): return player.round_number == 1

class PoolWaitPage(Page):
    @staticmethod
    def is_displayed(player: Player): return not player.session.vars['game_over'] and player.game_role == "Inactive"

class SliderTask(Page):
    form_model = 'player'
    form_fields = ['slider_score']
    @staticmethod
    def get_timeout_seconds(player: Player): return player.session.config.get('slider_timeout', 60)
    @staticmethod
    def is_displayed(player: Player): return not player.session.vars['game_over'] and player.game_role in ["Voter", "Representative"]

class ResultsWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        if not get_representative(group): return
        rep, voters = get_representative(group), get_voters(group)
        pot = (rep.slider_score * C.REP_SUCCESS_PAYOFF + sum(p.slider_score for p in voters) * C.VOTER_SUCCESS_PAYOFF)
        group.collective_pot = pot
        for p in voters: p.payoff = pot / C.VOTERS_PER_GROUP
        rep.payoff = C.REP_SALARY

class Vote(Page):
    form_model = 'player'
    form_fields = ['vote_to_remove']
    @staticmethod
    def is_displayed(player: Player): return not player.session.vars['game_over'] and player.game_role == 'Voter'

class VoteWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        if not get_representative(group): return
        session, rep = group.session, get_representative(group)
        votes = [p.vote_to_remove for p in get_voters(group) if p.vote_to_remove is not None]
        num_votes = sum(votes)
        group.num_remove_votes = num_votes
        
        is_removed = False
        mechanism = ""
        if num_votes >= 2:
            is_removed = True; mechanism = 'voted_out_early'
        elif session.vars['term_round'] >= C.TERM_LENGTH:
            is_removed = True; mechanism = 'term_limit'
        
        if is_removed:
            rep.was_removed = True
            rep.removal_mechanism = mechanism
            # "Survivors Only" Rule: Only record reps removed by term limit for Stage 2
            if mechanism == 'term_limit':
                session.vars['removed_reps_info'].append({'participant_id': rep.participant.id, 'mechanism': 'term_limit'})
            
            if session.vars['rep_pool_pids']:
                session.vars['current_rep_pid'] = session.vars['rep_pool_pids'].pop(0)
                session.vars['term_round'] = 1
            else:
                session.vars['game_over'] = True; session.vars['game_over_reason'] = "Pool empty."
        else:
            session.vars['term_round'] += 1

class RoundResults(Page):
    @staticmethod
    def is_displayed(player: Player): return not player.session.vars['game_over'] and player.game_role in ["Voter", "Representative"]
    @staticmethod
    def vars_for_template(player: Player):
        rep = get_representative(player.group)
        return {'my_score': player.slider_score, 'collective_pot': player.group.collective_pot, 'representative_score': rep.slider_score if rep else 0}

class EndOfRoundWaitPage(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        session = subsession.session
        if session.vars['game_over']: return
        if subsession.round_number >= C.START_OF_INDEFINITE_HORIZON and random.random() > C.CONTINUATION_PROB:
            session.vars['game_over'] = True; session.vars['game_over_reason'] = "The game ended randomly."
        if subsession.round_number >= C.NUM_ROUNDS:
            session.vars['game_over'] = True; session.vars['game_over_reason'] = "Max rounds reached."

# --- ENDGAME PAGES ---
class Stage2Decision(Page):
    form_model = 'player'
    form_fields = ['stage2_decision']
    @staticmethod
    def is_displayed(player: Player):
        if not player.session.vars['game_over']: return False
        my_removal_info = next((info for info in player.session.vars['removed_reps_info'] if info['participant_id'] == player.participant.id), None)
        return my_removal_info is not None # In T3, this list only contains term-limit survivors
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if player.stage2_decision in [1, 2]: player.payoff -= C.STAGE_2_COST

class FinalResults(Page):
    @staticmethod
    def is_displayed(player: Player): return player.session.vars['game_over']
    @staticmethod
    def vars_for_template(player: Player):
        return {'reason': player.session.vars.get('game_over_reason', 'The experiment has concluded.')}

page_sequence = [Introduction, PoolWaitPage, SliderTask, ResultsWaitPage, Vote, VoteWaitPage, RoundResults, EndOfRoundWaitPage, Stage2Decision, FinalResults]