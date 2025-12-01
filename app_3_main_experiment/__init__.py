from otree.api import *
import random

doc = """
This is the main experiment app. It features an indefinite horizon, a fixed set of 3 Voters,
and a dynamic pool of Representatives who are replaced when voted out.
"""

class C(BaseConstants):
    NAME_IN_URL = 'app_3_main_experiment'
    PLAYERS_PER_GROUP = None # Groups are dynamic
    NUM_ROUNDS = 20 # Set a high max number of rounds
    VOTERS_PER_GROUP = 3
    REP_SALARY = 250
    STAGE_2_COST = 50
    VOTER_SUCCESS_PAYOFF = 5
    REP_SUCCESS_PAYOFF = 50
    TERM_LENGTH = 3
    START_OF_INDEFINITE_HORIZON = 6
    CONTINUATION_PROB = 0.80
    CHAOS_PROB = 0.40

class Subsession(BaseSubsession):
    pass

def creating_session(subsession: Subsession):
    session = subsession.session
    
    # --- SETUP IN ROUND 1 ONLY ---
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
            first_rep_pid = session.vars['rep_pool_pids'].pop(0)
            session.vars['current_rep_pid'] = first_rep_pid
            session.vars['term_round'] = 1
        else:
            session.vars['game_over'] = True
            session.vars['game_over_reason'] = "Not enough players for a Representative."

    # --- ROLE ASSIGNMENT & GROUPING (EVERY ROUND) ---
    voter_pids = session.vars['voter_pids']
    current_rep_pid = session.vars.get('current_rep_pid')

    # 1. Assign roles to every player first
    for p in subsession.get_players():
        pid = p.participant.id
        if pid in voter_pids:
            p.game_role = "Voter"
        elif pid == current_rep_pid:
            p.game_role = "Representative"
        else:
            p.game_role = "Inactive"
    
    # 2. Manually build the group matrix based on roles
    active_group = []
    inactive_players = []
    for p in subsession.get_players():
        if p.game_role in ["Voter", "Representative"]:
            active_group.append(p)
        else:
            inactive_players.append(p)
            
    # The group matrix is a list of lists of players
    group_matrix = []
    if active_group:
        group_matrix.append(active_group)
    
    # Put each inactive player into their own group of 1
    for p in inactive_players:
        group_matrix.append([p])
        
    # 3. Use the compatible set_group_matrix function
    subsession.set_group_matrix(group_matrix)


class Group(BaseGroup):
    num_remove_votes = models.IntegerField(initial=0)
    collective_pot = models.FloatField(initial=0)

class Player(BasePlayer):
    is_representative = models.BooleanField() # This will be set based on role
    game_role = models.StringField()
    slider_score = models.IntegerField(initial=0)
    vote_to_remove = models.BooleanField(choices=[[True, 'Vote to Remove'], [False, 'Vote to Retain']], widget=widgets.RadioSelect)
    was_removed = models.BooleanField(initial=False)
    removal_mechanism = models.StringField()
    stage2_decision = models.IntegerField(widget=widgets.RadioSelect, choices=[[1, 'Sabotage'], [2, 'Help'], [0, 'Neutral']])

# --- HELPER FUNCTIONS ---
def get_voters(group: Group):
    return group.get_players_by_role('Voter')

def get_representative(group: Group):
    reps = group.get_players_by_role('Representative')
    return reps[0] if reps else None

# --- PAGES ---
class Introduction(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

class PoolWaitPage(Page):
    """This page is for players in the representative pool."""
    @staticmethod
    def is_displayed(player: Player):
        return not player.session.vars['game_over'] and player.game_role == "Inactive"

class SliderTask(Page):
    form_model = 'player'
    form_fields = ['slider_score']
    timeout_seconds = 60
    @staticmethod
    def is_displayed(player: Player):
        return not player.session.vars['game_over'] and player.game_role in ["Voter", "Representative"]

class ResultsWaitPage(WaitPage):
    group_by_role = True
    @staticmethod
    def after_all_players_arrive(group: Group):
        if group.get_players_by_role('Inactive'): return # Skip inactive groups
        rep = get_representative(group)
        voters = get_voters(group)
        pot = (rep.slider_score * C.REP_SUCCESS_PAYOFF + sum(p.slider_score for p in voters) * C.VOTER_SUCCESS_PAYOFF)
        group.collective_pot = pot
        for p in voters: p.payoff = pot / C.VOTERS_PER_GROUP
        rep.payoff = C.REP_SALARY

class Vote(Page):
    form_model = 'player'
    form_fields = ['vote_to_remove']
    @staticmethod
    def is_displayed(player: Player):
        if player.session.vars['game_over'] or player.game_role != 'Voter': return False
        return player.session.config['treatment'] != 'T1'

class VoteWaitPage(WaitPage):
    group_by_role = True
    @staticmethod
    def after_all_players_arrive(group: Group):
        if group.get_players_by_role('Inactive'): return
        session = group.session
        treatment = session.config['treatment']
        rep = get_representative(group)
        
        is_removed = False; mechanism = ""
        num_votes = 0
        if treatment != 'T1':
            votes = [p.vote_to_remove for p in get_voters(group) if p.vote_to_remove is not None]
            num_votes = sum(votes)
            group.num_remove_votes = num_votes

        # --- TREATMENT LOGIC ---
        if treatment == 'T1' and session.vars['term_round'] >= C.TERM_LENGTH:
            is_removed = True; mechanism = 'no_vote_term_limit'
        elif treatment == 'T2a' and num_votes >= 2:
            is_removed = True; mechanism = 'voted_out'
        elif treatment == 'T2b':
            won_vote = num_votes < 2
            if won_vote and random.random() < C.CHAOS_PROB:
                is_removed = True; mechanism = 'unlucky_winner'
            elif not won_vote and random.random() > C.CHAOS_PROB: # 60% chance of removal
                is_removed = True; mechanism = 'voted_out_probabilistic'
        elif treatment == 'T3':
            if num_votes >= 2:
                is_removed = True; mechanism = 'voted_out_early'
            elif session.vars['term_round'] >= C.TERM_LENGTH:
                is_removed = True; mechanism = 'term_limit'

        # --- UPDATE STATE BASED ON OUTCOME ---
        if is_removed:
            rep.was_removed = True
            rep.removal_mechanism = mechanism
            session.vars['removed_reps_info'].append({
                'participant_id': rep.participant.id, 'mechanism': mechanism, 'round_removed': group.round_number,
            })
            
            if session.vars['rep_pool_pids']:
                new_rep_pid = session.vars['rep_pool_pids'].pop(0)
                session.vars['current_rep_pid'] = new_rep_pid
                session.vars['term_round'] = 1 # Reset term counter for new rep
            else:
                session.vars['game_over'] = True; session.vars['game_over_reason'] = "The representative pool is empty."
        else:
            session.vars['term_round'] += 1 # Increment term counter for surviving rep

class EndOfRoundWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        session = subsession.session
        if session.vars['game_over']: return
        if subsession.round_number >= C.START_OF_INDEFINITE_HORIZON and random.random() > C.CONTINUATION_PROB:
            session.vars['game_over'] = True; session.vars['game_over_reason'] = "The game ended randomly."
        if subsession.round_number >= C.NUM_ROUNDS:
            session.vars['game_over'] = True; session.vars['game_over_reason'] = "The maximum number of rounds was reached."

class RoundResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return not player.session.vars['game_over'] and player.game_role in ["Voter", "Representative"]
    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        rep = get_representative(group)
        return {
            'representative_score': rep.slider_score if rep else 0,
            'my_score': player.slider_score,
            'collective_pot': group.collective_pot,
        }

class Stage2Decision(Page):
    form_model = 'player'
    form_fields = ['stage2_decision']
    
    @staticmethod
    def is_displayed(player: Player):
        if player.round_number != C.NUM_ROUNDS: return False
        treatment = player.session.config['treatment']
        my_removal_info = next((info for info in player.session.vars['removed_reps_info'] if info['participant_id'] == player.participant.id), None)
        if not my_removal_info: return False
        
        mechanism = my_removal_info['mechanism']
        # --- STAGE 2 DISPLAY LOGIC BASED ON CONFIRMED RULES ---
        if treatment == 'T1': return mechanism == 'no_vote_term_limit'
        if treatment == 'T2a': return mechanism == 'voted_out'
        if treatment == 'T2b': return mechanism in ['unlucky_winner', 'voted_out_probabilistic']
        if treatment == 'T3': return mechanism == 'term_limit' # "Survivors Only" rule
        return False

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if player.stage2_decision in [1, 2]: player.payoff -= C.STAGE_2_COST

class FinalResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS
    @staticmethod
    def vars_for_template(player: Player):
        return {'reason': player.session.vars['game_over_reason']}

page_sequence = [
    Introduction, PoolWaitPage, SliderTask, ResultsWaitPage, Vote, VoteWaitPage,
    RoundResults, EndOfRoundWaitPage, Stage2Decision, FinalResults,
]