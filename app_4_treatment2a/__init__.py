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
        # Initialize permanent roles from participant fields if they exist
        # This allows the debug sessions to work without running the personality games
        if 'is_voter' not in subsession.get_players()[0].participant.vars:
            players = subsession.get_players()
            random.shuffle(players)
            
            voter_players = players[:C.VOTERS_PER_GROUP]
            for p in voter_players: p.participant.is_voter = True

            rep_pool_players = players[C.VOTERS_PER_GROUP:]
            for p in rep_pool_players: p.participant.is_voter = False
        
        # Now, build the PID lists from the permanent participant fields
        all_players = subsession.get_players()
        session.vars['voter_pids'] = [p.participant.id for p in all_players if p.participant.is_voter]
        session.vars['rep_pool_pids'] = [p.participant.id for p in all_players if not p.participant.is_voter]
        
        session.vars['removed_pids'] = []
        session.vars['game_over'] = False
        session.vars['game_over_reason'] = ""
        session.vars['term_round'] = 0

        if session.vars['rep_pool_pids']:
            session.vars['current_rep_pid'] = session.vars['rep_pool_pids'].pop(0)
            session.vars['term_round'] = 1
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
    vote_to_remove = models.BooleanField(choices=[[True, 'Vote to Remove'], [False, 'Vote to Retain']], widget=widgets.RadioSelect)
    was_removed_this_round = models.BooleanField(initial=False)
    stage2_decision = models.IntegerField(widget=widgets.RadioSelect, choices=[[1, 'Sabotage'], [2, 'Help'], [0, 'Neutral']])

def get_voters(group: Group): return [p for p in group.get_players() if p.game_state == 1]
def get_representative(group: Group):
    for p in group.get_players():
        if p.game_state == 2: return p
    return None

class Introduction(Page):
    @staticmethod
    def is_displayed(player: Player): return player.round_number == 1

class ActivePlayerPage(Page):
    @staticmethod
    def is_displayed(player: Player):
        return not player.session.vars['game_over'] and player.game_state in [1, 2]

class InactivePlayerPage(Page):
    @staticmethod
    def is_displayed(player: Player):
        return not player.session.vars['game_over'] and player.game_state in [0, 3]

class SliderTask(ActivePlayerPage):
    form_model = 'player'
    form_fields = ['slider_score']
    @staticmethod
    def get_timeout_seconds(player: Player): return player.session.config.get('slider_timeout', 60)

class Vote(ActivePlayerPage):
    form_model = 'player'
    form_fields = ['vote_to_remove']
    @staticmethod
    def is_displayed(player: Player):
        return player.game_state == 1 and not player.session.vars['game_over']

class SyncAfterVote(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        if get_representative(group):
            rep = get_representative(group)
            votes = [p.vote_to_remove for p in get_voters(group) if p.vote_to_remove]
            group.num_remove_votes = len(votes)
            if len(votes) >= 2:
                rep.was_removed_this_round = True

class Stage2Decision(Page):
    form_model = 'player'
    form_fields = ['stage2_decision']
    @staticmethod
    def is_displayed(player: Player):
        if not player.session.vars['game_over']: return False
        # Show to any player who was in the rep pool (i.e., not a permanent voter)
        return not player.participant.is_voter

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
        if player.game_state in [0, 3]: return {}
        else:
            rep = get_representative(player.group)
            return {
                'my_score': player.slider_score,
                'collective_pot': player.group.collective_pot,
                'representative_score': rep.slider_score if rep else 0,
            }

class EndOfRoundWaitPage(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        session = subsession.session
        if session.vars['game_over']: return
        
        current_rep_pid = session.vars.get('current_rep_pid')
        rep_was_removed = False
        for p in subsession.get_players():
            if p.participant.id == current_rep_pid and p.was_removed_this_round:
                rep_was_removed = True
                break
        
        if rep_was_removed:
            session.vars['removed_pids'].append(current_rep_pid)
            if session.vars['rep_pool_pids']:
                session.vars['current_rep_pid'] = session.vars['rep_pool_pids'].pop(0)
                session.vars['term_round'] = 1
            else:
                session.vars['game_over'] = True; session.vars['game_over_reason'] = "The representative pool is empty."
        else:
            session.vars['term_round'] += 1
        
        if subsession.round_number >= C.START_OF_INDEFINITE_HORIZON and random.random() > C.CONTINUATION_PROB:
            session.vars['game_over'] = True; session.vars['game_over_reason'] = "The game ended randomly."
        if subsession.round_number >= C.NUM_ROUNDS:
            session.vars['game_over'] = True; session.vars['game_over_reason'] = "Max rounds reached."

class FinalResults(Page):
    @staticmethod
    def is_displayed(player: Player): return player.session.vars['game_over']
    @staticmethod
    def vars_for_template(player: Player):
        return {'reason': player.session.vars.get('game_over_reason', 'The experiment has concluded.')}

page_sequence = [
    Introduction,
    SliderTask, InactivePlayerPage,
    SyncAfterVote,
    Vote,
    SyncAfterVote,
    RoundResults, 
    EndOfRoundWaitPage, 
    Stage2Decision,
    FinalResults,
]
