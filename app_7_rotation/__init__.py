from otree.api import *
import random

class C(BaseConstants):
    NAME_IN_URL = 'app_7_rotation'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 5
    VOTERS_PER_GROUP = 3
    REP_SALARY = 250
    VOTER_SUCCESS_PAYOFF = 5
    REP_SUCCESS_PAYOFF = 50

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
        
        if session.vars['rep_pool_pids']:
            session.vars['current_rep_pid'] = session.vars['rep_pool_pids'].pop(0)
        else:
            session.vars['current_rep_pid'] = None

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
    vote_to_remove = models.BooleanField(label="Do you vote to remove the Representative?", choices=[[True, 'Yes'], [False, 'No']], widget=widgets.RadioSelect)
    was_removed_this_round = models.BooleanField(initial=False)

# --- PAGES ---
class RoundStatus(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.session.vars.get('current_rep_pid') is not None
    @staticmethod
    def vars_for_template(player: Player):
        return {
            'current_rep_pid': player.session.vars.get('current_rep_pid'),
            'rep_pool_pids': player.session.vars.get('rep_pool_pids'),
            'removed_pids': player.session.vars.get('removed_pids'),
        }

class SliderTask(Page):
    form_model = 'player'
    form_fields = ['slider_score']
    timeout_seconds = 15
    @staticmethod
    def is_displayed(player: Player):
        return player.game_state in [1, 2]

class PoolWaitPage(Page):
    timeout_seconds = 15
    @staticmethod
    def is_displayed(player: Player):
        return player.game_state in [0, 3]

class SyncAfterTask(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        for group in subsession.get_groups():
            if len(group.get_players()) > 1:
                rep = next((p for p in group.get_players() if p.game_state == 2), None)
                voters = [p for p in group.get_players() if p.game_state == 1]
                if rep:
                    pot = (rep.slider_score * C.REP_SUCCESS_PAYOFF + sum(p.slider_score for p in voters) * C.VOTER_SUCCESS_PAYOFF)
                    group.collective_pot = pot
                    for p in voters: p.payoff = pot / C.VOTERS_PER_GROUP
                    rep.payoff = C.REP_SALARY

class Vote(Page):
    form_model = 'player'
    form_fields = ['vote_to_remove']
    @staticmethod
    def is_displayed(player: Player):
        return player.game_state == 1

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

class VoteResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.session.vars.get('current_rep_pid') is not None
    @staticmethod
    def vars_for_template(player: Player):
        active_group = next((g for g in player.subsession.get_groups() if len(g.get_players()) > 1), None)
        return {'active_group': active_group}

class EndOfRoundWaitPage(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        session = subsession.session
        removed_rep = next((p for p in subsession.get_players() if p.was_removed_this_round), None)
        
        if removed_rep:
            session.vars['removed_pids'].append(removed_rep.participant.id)
            if session.vars['rep_pool_pids']:
                session.vars['current_rep_pid'] = session.vars['rep_pool_pids'].pop(0)
            else:
                session.vars['current_rep_pid'] = None

class EndOfExperiment(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.session.vars.get('current_rep_pid') is None and player.round_number > 1

page_sequence = [
    RoundStatus,
    SliderTask, PoolWaitPage,
    SyncAfterTask,
    Vote, PoolWaitPage,
    SyncAfterVote,
    VoteResults,
    EndOfRoundWaitPage,
    EndOfExperiment,
]