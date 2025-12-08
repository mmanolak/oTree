
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

doc = ''
class C(BaseConstants):
    NAME_IN_URL = 'floating_rotation'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 100
    NUM_VOTERS = 3
    CONTINUATION_PROB = 0.9
class Subsession(BaseSubsession):
    active_rep_id = models.IntegerField()
    vote_result = models.StringField()
    game_continues = models.BooleanField()
class Group(BaseGroup):
    pass
class Player(BasePlayer):
    vote_choice = models.StringField(choices=['Keep', 'Replace'], label='Do you want to keep or replace the current representative?', widget=widgets.RadioSelect)
    is_voter = models.BooleanField()
    is_active_rep = models.BooleanField()
    is_in_rep_pool = models.BooleanField()
    is_retired = models.BooleanField()
def creating_session(subsession: Subsession):
    
    import random
    if subsession.round_number == 1:
        # Get all participants
        all_participants = subsession.session.get_participants()
    
        # Randomly select 3 to be voters
        voters = random.sample(all_participants, C.NUM_VOTERS)
    
        # Assign voter status
        for p in all_participants:
            if p in voters:
                p.is_voter = True
                p.is_active_rep = False
                p.in_rep_pool = False
                p.in_retired_pool = False
                p.role_status = "voter"
            else:
                p.is_voter = False
                p.is_active_rep = False
                p.in_rep_pool = True
                p.in_retired_pool = False
                p.role_status = "rep_pool"
    
        # Select first representative from rep pool
        rep_pool = [p for p in all_participants if p.in_rep_pool]
        if rep_pool:
            first_rep = random.choice(rep_pool)
            first_rep.is_active_rep = True
            first_rep.in_rep_pool = False
            first_rep.role_status = "active_rep"
            subsession.active_rep_id = first_rep.id_in_subsession
    else:
        # Copy role status from previous round
        for player in subsession.get_players():
            player.is_voter = player.participant.is_voter
            player.is_active_rep = player.participant.is_active_rep
            player.is_in_rep_pool = player.participant.in_rep_pool
            player.is_retired = player.participant.in_retired_pool
    
        # Set active rep ID from previous round's data
        prev_subsession = subsession.in_round(subsession.round_number - 1)
        subsession.active_rep_id = prev_subsession.active_rep_id
    
class RoleAssignment(Page):
    form_model = 'player'
    @staticmethod
    def is_displayed(player: Player):
        
        return player.round_number == 1
        
    @staticmethod
    def vars_for_template(player: Player):
        participant = player.participant
        
        return dict(
            role_status=player.participant.role_status
        )
        
class WaitForRoleAssignment(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def is_displayed(player: Player):
        
        return player.round_number == 1
        
class VotingPage(Page):
    form_model = 'player'
    form_fields = ['vote_choice']
    @staticmethod
    def is_displayed(player: Player):
        participant = player.participant
        
        return player.participant.is_voter
        
    @staticmethod
    def vars_for_template(player: Player):
        session = player.session
        subsession = player.subsession
        participant = player.participant
        
        # Get the active representative
        active_rep = None
        for p in player.get_others_in_subsession():
            if p.participant.is_active_rep:
                active_rep = p
                break
        
        return dict(
            round_num=player.round_number,
            active_rep_id=active_rep.id_in_subsession if active_rep else None
        )
        
class WaitForVotes(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        session = subsession.session
        
        import random
        
        # Count votes
        voters = [p for p in subsession.get_players() if p.participant.is_voter]
        keep_votes = sum(1 for v in voters if v.vote_choice == "Keep")
        replace_votes = sum(1 for v in voters if v.vote_choice == "Replace")
        
        # Determine outcome (majority rule)
        if replace_votes > keep_votes:
            subsession.vote_result = "Replace"
        
            # Move current rep to retired pool
            for p in subsession.session.get_participants():
                if p.is_active_rep:
                    p.is_active_rep = False
                    p.in_retired_pool = True
                    p.role_status = "retired"
                    break
        
            # Select new rep from pool
            rep_pool = [p for p in subsession.session.get_participants() if p.in_rep_pool]
            if rep_pool:
                new_rep = random.choice(rep_pool)
                new_rep.is_active_rep = True
                new_rep.in_rep_pool = False
                new_rep.role_status = "active_rep"
                subsession.active_rep_id = new_rep.id_in_subsession
        else:
            subsession.vote_result = "Keep"
        
        # Random continuation (90% continue, 10% end)
        subsession.game_continues = random.random() < C.CONTINUATION_PROB
        
class ResultsPage(Page):
    form_model = 'player'
    @staticmethod
    def vars_for_template(player: Player):
        session = player.session
        subsession = player.subsession
        participant = player.participant
        
        # Get vote counts
        voters = [p for p in player.subsession.get_players() if p.participant.is_voter]
        keep_votes = sum(1 for v in voters if v.vote_choice == "Keep")
        replace_votes = sum(1 for v in voters if v.vote_choice == "Replace")
        
        # Get active rep
        active_rep_id = player.subsession.active_rep_id
        
        return dict(
            vote_result=player.subsession.vote_result,
            keep_votes=keep_votes,
            replace_votes=replace_votes,
            active_rep_id=active_rep_id,
            game_continues=player.subsession.game_continues,
            role_status=player.participant.role_status
        )
        
    @staticmethod
    def app_after_this_page(player: Player, upcoming_apps):
        session = player.session
        subsession = player.subsession
        
        if not player.subsession.game_continues:
            # Game ends - skip to next app
            return upcoming_apps[0] if upcoming_apps else None
        
page_sequence = [RoleAssignment, WaitForRoleAssignment, VotingPage, WaitForVotes, ResultsPage]