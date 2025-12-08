from otree.api import *

import shared_out
import random

doc = 'A minimal, robust implementation of the representative rotation mechanic using a subsession bridge.'

class C(BaseConstants):
    NAME_IN_URL = 'floating_rotation'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 10
    NUM_VOTERS = 3

class Subsession(BaseSubsession):
    # STEP 1: Add the "bridge" field to the Subsession model
    pid_of_removed_rep = models.IntegerField(initial=None)

def creating_session(subsession: Subsession):
    session = subsession.session
    if subsession.round_number == 1:
        participants = session.get_participants()
        random.shuffle(participants)
        
        voter_participants = participants[:C.NUM_VOTERS]
        rep_pool_participants = participants[C.NUM_VOTERS:]

        session.vars['voter_pids'] = [p.id for p in voter_participants]
        session.vars['rep_pool_pids'] = [p.id for p in rep_pool_participants]
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
        if pid in voter_pids:
            p.is_voter = True
            p.is_active_rep = False
        elif pid == current_rep_pid:
            p.is_voter = False
            p.is_active_rep = True
        else:
            p.is_voter = False
            p.is_active_rep = False

    active_players = [p for p in subsession.get_players() if p.is_voter or p.is_active_rep]
    inactive_players = [p for p in subsession.get_players() if not (p.is_voter or p.is_active_rep)]
    group_matrix = []
    if active_players: group_matrix.append(active_players)
    for p in inactive_players: group_matrix.append([p])
    subsession.set_group_matrix(group_matrix)

class Group(BaseGroup):
    num_remove_votes = models.IntegerField(initial=0)

class Player(BasePlayer):
    vote_choice = models.BooleanField(label='Do you want to replace the current representative?', choices=[[True, 'Replace'], [False, 'Keep']], widget=widgets.RadioSelect)
    is_voter = models.BooleanField(initial=False)
    is_active_rep = models.BooleanField(initial=False)

# --- PAGES ---
class Status(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.session.vars.get('current_rep_pid') is not None
    @staticmethod
    def vars_for_template(player: Player):
        return {
            'voter_pids': player.session.vars['voter_pids'],
            'current_rep_pid': player.session.vars.get('current_rep_pid'),
            'rep_pool_pids': player.session.vars['rep_pool_pids'],
            'removed_pids': player.session.vars['removed_pids'],
        }

class VotingPage(Page):
    form_model = 'player'
    form_fields = ['vote_choice']
    @staticmethod
    def is_displayed(player: Player):
        return player.is_voter
    @staticmethod
    def vars_for_template(player: Player):
        return {'active_rep_id': player.session.vars.get('current_rep_pid')}

class SyncAfterVote(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        # STEP 2: Write the removed rep's ID to the "bridge" field
        active_group = next((g for g in subsession.get_groups() if len(g.get_players()) > 1), None)
        if active_group:
            rep = next((p for p in active_group.get_players() if p.is_active_rep), None)
            if rep:
                voters = [p for p in active_group.get_players() if p.is_voter]
                replace_votes = sum(1 for v in voters if v.field_maybe_none('vote_choice') is True)
                active_group.num_remove_votes = replace_votes
                if replace_votes > (C.NUM_VOTERS / 2):
                    subsession.pid_of_removed_rep = rep.participant.id

class ResultsPage(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.session.vars.get('current_rep_pid') is not None
    @staticmethod
    def vars_for_template(player: Player):
        session = player.session
        active_group = next((g for g in player.subsession.get_groups() if len(g.get_players()) > 1), None)
        
        if active_group:
            replace_votes = active_group.num_remove_votes
            vote_result = "Replace" if replace_votes > (C.NUM_VOTERS / 2) else "Keep"
        else:
            replace_votes = 0
            vote_result = "N/A"

        next_rep_pid = None
        if vote_result == "Keep":
            next_rep_pid = session.vars.get('current_rep_pid')
        else:
            if session.vars['rep_pool_pids']:
                next_rep_pid = session.vars['rep_pool_pids'][0]
            else:
                next_rep_pid = "None (Pool is empty)"

        return {
            'replace_votes': replace_votes,
            'keep_votes': C.NUM_VOTERS - replace_votes,
            'vote_result': vote_result,
            'next_rep_pid': next_rep_pid,
        }

class EndOfRoundWaitPage(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        # STEP 3: Read the ID from the "bridge" field and update the permanent state
        session = subsession.session
        
        # DEFINITIVE FIX: Use field_maybe_none() to safely read the bridge field
        removed_pid = subsession.field_maybe_none('pid_of_removed_rep')
        
        if removed_pid:
            session.vars['removed_pids'].append(removed_pid)
            if session.vars['rep_pool_pids']:
                session.vars['current_rep_pid'] = session.vars['rep_pool_pids'].pop(0)
            else:
                session.vars['current_rep_pid'] = None

class EndOfGame(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.session.vars.get('current_rep_pid') is None

page_sequence = [
    Status,
    VotingPage,
    SyncAfterVote,
    ResultsPage,
    EndOfRoundWaitPage,
    EndOfGame,
]