from otree.api import *
import random

class C(BaseConstants):
    NAME_IN_URL = 'app_4_treatment2a'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 20
    VOTERS_PER_GROUP = 3
    REP_SALARY = 250
    STAGE_2_COST = 50
    VOTER_SUCCESS_PAYOFF = 5
    REP_SUCCESS_PAYOFF = 50
    START_OF_INDEFINITE_HORIZON = 7
    CONTINUATION_PROB = 0.80

class Subsession(BaseSubsession):
    pass

def creating_session(subsession: Subsession):
    session = subsession.session
    if subsession.round_number == 1:
        try:
            _ = subsession.get_players()[0].participant.is_voter
        except KeyError:
            players = subsession.get_players()
            random.shuffle(players)
            voter_players = players[:C.VOTERS_PER_GROUP]
            for p in voter_players: p.participant.is_voter = True
            rep_pool_players = players[C.VOTERS_PER_GROUP:]
            for p in rep_pool_players: p.participant.is_voter = False
        
        all_players = subsession.get_players()
        session.vars['voter_pids'] = [p.participant.id for p in all_players if p.participant.is_voter]
        session.vars['rep_pool_pids'] = [p.participant.id for p in all_players if not p.participant.is_voter]
        session.vars['removed_pids'] = []
        session.vars['game_over'] = False
        session.vars['game_over_reason'] = ""
        
        if session.vars['rep_pool_pids']:
            session.vars['current_rep_pid'] = session.vars['rep_pool_pids'].pop(0)
        else:
            session.vars['game_over'] = True
            session.vars['game_over_reason'] = "Not enough players for a Representative."

    voter_pids = session.vars['voter_pids']
    current_rep_pid = session.vars.get('current_rep_pid')
    removed_pids = session.vars['removed_pids']

    for p in subsession.get_players():
        pid = p.participant.id
        if pid in voter_pids: p.game_state = 1
        elif pid == current_rep_pid: p.game_state = 2
        elif pid in removed_pids: p.game_state = 3
        else: p.game_state = 0
    
    active_players = [p for p in subsession.get_players() if p.game_state in [1, 2]]
    inactive_players = [p for p in subsession.get_players() if p.game_state in [0, 3]]
    group_matrix = []
    if active_players: group_matrix.append(active_players)
    for p in inactive_players: group_matrix.append([p])
    subsession.set_group_matrix(group_matrix)

class Group(BaseGroup):
    num_remove_votes = models.IntegerField(initial=0)
    collective_pot = models.FloatField(initial=0)

class Player(BasePlayer):
    game_state = models.IntegerField()
    slider_score = models.IntegerField(initial=0)
    vote_to_remove = models.BooleanField(choices=[[True, 'Yes'], [False, 'No']], widget=widgets.RadioSelect)
    was_removed_this_round = models.BooleanField(initial=False)
    stage2_decision = models.IntegerField(widget=widgets.RadioSelect, choices=[[1, 'Sabotage'], [2, 'Help'], [0, 'Neutral']])

# --- PAGES ---
class Introduction(Page):
    @staticmethod
    def is_displayed(player: Player): return player.round_number == 1

class SliderTask(Page):
    form_model = 'player'
    form_fields = ['slider_score']
    @staticmethod
    def get_timeout_seconds(player: Player): return player.session.config.get('slider_timeout', 60)
    @staticmethod
    def is_displayed(player: Player): return not player.session.vars['game_over'] and player.game_state in [1, 2]

class PoolWaitPage(Page):
    @staticmethod
    def is_displayed(player: Player): return not player.session.vars['game_over'] and player.game_state in [0, 3]

class SyncAfterTask(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        rep = next((p for p in group.get_players() if p.game_state == 2), None)
        if rep:
            voters = [p for p in group.get_players() if p.game_state == 1]
            pot = (rep.slider_score * C.REP_SUCCESS_PAYOFF + sum(p.slider_score for p in voters) * C.VOTER_SUCCESS_PAYOFF)
            group.collective_pot = pot
            for p in voters: p.payoff = pot / C.VOTERS_PER_GROUP
            rep.payoff = C.REP_SALARY

class Vote(Page):
    form_model = 'player'
    form_fields = ['vote_to_remove']
    @staticmethod
    def is_displayed(player: Player): return not player.session.vars['game_over'] and player.game_state == 1
    @staticmethod
    def vars_for_template(player: Player):
        # Find the representative in the player's group
        rep = next((p for p in player.group.get_players() if p.game_state == 2), None)
        return {
            'representative_pid': rep.participant.id if rep else 'N/A'
        }

class SyncAfterVote(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        rep = next((p for p in group.get_players() if p.game_state == 2), None)
        if rep:
            voters = [p for p in group.get_players() if p.game_state == 1]
            num_votes = sum(1 for p in voters if p.field_maybe_none('vote_to_remove') is True)
            group.num_remove_votes = num_votes
            if num_votes >= 2:
                rep.was_removed_this_round = True

class Stage2Decision(Page):
    form_model = 'player'
    form_fields = ['stage2_decision']
    @staticmethod
    def is_displayed(player: Player):
        return player.was_removed_this_round

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.participant.stage2_decision_made = player.stage2_decision
        if player.stage2_decision in [1, 2]:
            player.payoff -= C.STAGE_2_COST

class RoundResults(Page):
    @staticmethod
    def is_displayed(player: Player): return not player.session.vars['game_over']
    @staticmethod
    def vars_for_template(player: Player):
        if player.game_state in [0, 3]:
            # Inactive players don't need any variables
            return {}
        else:
            # Active players (Voters and Reps) need the full summary
            rep = next((p for p in player.group.get_players() if p.game_state == 2), None)
            return {
                'my_score': player.slider_score, # <-- ADDED THIS LINE
                'representative_score': rep.slider_score if rep else 0,
                'collective_pot': player.group.collective_pot,
                'num_remove_votes': player.group.num_remove_votes, # <-- ADDED THIS FOR CLARITY
            }

class EndOfRoundWaitPage(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        session = subsession.session
        if session.vars['game_over']: return
        
        removed_rep = next((p for p in subsession.get_players() if p.was_removed_this_round), None)
        
        if removed_rep:
            session.vars['removed_pids'].append(removed_rep.participant.id)
            if session.vars['rep_pool_pids']:
                session.vars['current_rep_pid'] = session.vars['rep_pool_pids'].pop(0)
            else:
                session.vars['current_rep_pid'] = None
                session.vars['game_over'] = True
                session.vars['game_over_reason'] = "The representative pool is empty."
        
        if not session.vars['game_over']:
            if subsession.round_number >= C.START_OF_INDEFINITE_HORIZON and random.random() > C.CONTINUATION_PROB:
                session.vars['game_over'] = True
                session.vars['game_over_reason'] = "The game ended randomly."
            if subsession.round_number >= C.NUM_ROUNDS:
                session.vars['game_over'] = True
                session.vars['game_over_reason'] = "Max rounds reached."

class FinalResults(Page):
    @staticmethod
    def is_displayed(player: Player): return player.session.vars['game_over']
    @staticmethod
    def vars_for_template(player: Player):
        return {'reason': player.session.vars.get('game_over_reason', 'The experiment has concluded.')}

page_sequence = [
    Introduction,
    SliderTask, PoolWaitPage,
    SyncAfterTask,
    Vote, PoolWaitPage,
    SyncAfterVote,
    Stage2Decision,
    RoundResults, 
    EndOfRoundWaitPage, 
    FinalResults,
]