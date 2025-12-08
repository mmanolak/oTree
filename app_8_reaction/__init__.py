from otree.api import *
import random

doc = 'Treatment 2a: Representatives who are voted out make an immediate final decision.'

class C(BaseConstants):
    NAME_IN_URL = 'app_8_reaction'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 10
    NUM_VOTERS = 3
    STAGE_2_COST = 50

class Subsession(BaseSubsession):
    rep_was_removed_this_round = models.BooleanField(initial=False)

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
    stage2_decision = models.IntegerField(
        label="Make your legacy decision.",
        choices=[
            [1, 'Sabotage'],
            [0, 'Neutral'],
            [2, 'Help'],
        ]
    )


# --- PAGES ---
class Status(Page):
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
        return player.is_voter and player.session.vars.get('current_rep_pid') is not None
    @staticmethod
    def vars_for_template(player: Player):
        return {'active_rep_id': player.session.vars.get('current_rep_pid')}

class SyncAfterVote(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def is_displayed(subsession: Subsession):
        return subsession.session.vars.get('current_rep_pid') is not None
        
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        active_group = next((g for g in subsession.get_groups() if len(g.get_players()) > 1), None)
        if active_group:
            rep = next((p for p in active_group.get_players() if p.is_active_rep), None)
            if rep:
                voters = [p for p in active_group.get_players() if p.is_voter]
                replace_votes = sum(1 for v in voters if v.field_maybe_none('vote_choice') is True)
                active_group.num_remove_votes = replace_votes
                if replace_votes > (C.NUM_VOTERS / 2):
                    subsession.rep_was_removed_this_round = True
                    rep_pid = rep.participant.id
                    if rep_pid not in subsession.session.vars['removed_pids']:
                         subsession.session.vars['removed_pids'].append(rep_pid)

class Stage2Decision(Page):
    form_model = 'player'
    form_fields = ['stage2_decision']

    @staticmethod
    def is_displayed(player: Player):
        return player.is_active_rep and player.subsession.rep_was_removed_this_round

    @staticmethod
    def vars_for_template(player: Player):
        return dict(C=C)

class PostDecisionWaitPage(WaitPage):
    # This is the new, required wait page
    @staticmethod
    def is_displayed(player: Player):
        # Show this page to everyone IF a removal happened this round
        return player.subsession.rep_was_removed_this_round

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

        # CORRECTED RETURN STATEMENT
        return {
            'replace_votes': replace_votes,
            'keep_votes': C.NUM_VOTERS - replace_votes,
            'vote_result': vote_result,
            'next_rep_pid': next_rep_pid,
        }

class EndOfRoundWaitPage(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def is_displayed(subsession: Subsession):
        return subsession.session.vars.get('current_rep_pid') is not None

    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        if subsession.rep_was_removed_this_round:
            session = subsession.session
            if session.vars['rep_pool_pids']:
                session.vars['current_rep_pid'] = session.vars['rep_pool_pids'].pop(0)
            else:
                session.vars['current_rep_pid'] = None

class EndOfGame(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.session.vars.get('current_rep_pid') is None

# CORRECTED PAGE SEQUENCE
page_sequence = [
    Status,
    VotingPage,
    SyncAfterVote,
    Stage2Decision,
    PostDecisionWaitPage,
    ResultsPage,
    EndOfRoundWaitPage,
    EndOfGame,
]