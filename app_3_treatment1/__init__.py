from otree.api import *
import random

doc = 'Treatment 1 (No Vote): A fixed 3-round term limit for representatives with no voting.'

# App-level Constants
class C(BaseConstants):
    NAME_IN_URL = 'app_3_treatment1'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 10
    NUM_VOTERS = 3
    STAGE_2_COST = 50
    REP_SALARY = 150
    BASE_VOTER_SUCCESS_PAYOFF = 5
    BASE_REP_SUCCESS_PAYOFF = 50

class Subsession(BaseSubsession):
    rep_was_removed_this_round = models.BooleanField(initial=False)

def creating_session(subsession: Subsession):
    # Session Initialization
    # This function runs once in Round 1 to set up the permanent roles and pools for the entire session.
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
            session.vars['rep_term_start_round'] = 1
        else:
            session.vars['current_rep_pid'] = None
    
class Group(BaseGroup):
    num_remove_votes = models.IntegerField(initial=0)
    collective_pot = models.FloatField(initial=0)
    voter_multiplier = models.FloatField(initial=C.BASE_VOTER_SUCCESS_PAYOFF)
    rep_multiplier = models.FloatField(initial=C.BASE_REP_SUCCESS_PAYOFF)

class Player(BasePlayer):
    vote_choice = models.BooleanField(label='Do you want to replace the current representative?', choices=[[True, 'Replace'], [False, 'Keep']], widget=widgets.RadioSelect)
    is_voter = models.BooleanField(initial=False)
    is_active_rep = models.BooleanField(initial=False)
    stage2_decision = models.IntegerField(label="Make your legacy decision.", choices=[[1, 'Sabotage'],[0, 'Neutral'],[2, 'Help']])
    slider_score = models.IntegerField(initial=0)

class InitializeRoundWaitPage(WaitPage):
    # Per-Round Setup
    # This logic runs at the start of every round to assign roles and create groups.
    wait_for_all_groups = True
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        # 1. Assign player roles (Voter, Representative, Inactive) for this round.
        voter_pids = subsession.session.vars['voter_pids']
        current_rep_pid = subsession.session.vars.get('current_rep_pid')
        for p in subsession.get_players():
            pid = p.participant.id
            if pid in voter_pids: p.is_voter = True; p.is_active_rep = False
            elif pid == current_rep_pid: p.is_voter = False; p.is_active_rep = True
            else: p.is_voter = False; p.is_active_rep = False
        # 2. Create the group structure for this round (one active group, inactive players in solo groups).
        active_players = [p for p in subsession.get_players() if p.is_voter or p.is_active_rep]
        inactive_players = [p for p in subsession.get_players() if not (p.is_voter or p.is_active_rep)]
        group_matrix = []
        if active_players: group_matrix.append(active_players)
        for p in inactive_players: group_matrix.append([p])
        subsession.set_group_matrix(group_matrix)
        # 3. Carry over the productivity multipliers from the previous round's active group.
        active_group = next((g for g in subsession.get_groups() if len(g.get_players()) > 1), None)
        if active_group:
            if subsession.round_number > 1:
                a_voter = next((p for p in active_group.get_players() if p.is_voter), None)
                if a_voter:
                    prev_group = a_voter.in_round(subsession.round_number - 1).group
                    active_group.voter_multiplier = prev_group.voter_multiplier
                    active_group.rep_multiplier = prev_group.rep_multiplier

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

class SliderTask(Page):
    form_model = 'player'
    form_fields = ['slider_score']
    @staticmethod
    def get_timeout_seconds(player: Player):
        return player.session.config.get('slider_task_timeout', 60)
    @staticmethod
    def vars_for_template(player: Player):
        if player.is_active_rep: contribution_rate = player.group.rep_multiplier
        else: contribution_rate = player.group.voter_multiplier
        return {'contribution_rate': contribution_rate}
    @staticmethod
    def is_displayed(player: Player):
        return (player.is_voter or player.is_active_rep) and player.session.vars.get('current_rep_pid') is not None

class PayoffWaitPage(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def is_displayed(subsession: Subsession):
        return subsession.session.vars.get('current_rep_pid') is not None
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        active_group = next((g for g in subsession.get_groups() if len(g.get_players()) > 1), None)
        if active_group:
            rep = next((p for p in active_group.get_players() if p.is_active_rep), None)
            voters = [p for p in active_group.get_players() if p.is_voter]
            if rep and voters:
                pot = (rep.slider_score * active_group.rep_multiplier + sum(p.slider_score for p in voters) * active_group.voter_multiplier)
                active_group.collective_pot = pot
                for p in voters: p.payoff = pot / C.NUM_VOTERS
                rep.payoff = C.REP_SALARY

class IncomeResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return (player.is_voter or player.is_active_rep) and player.session.vars.get('current_rep_pid') is not None
    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        rep = next((p for p in group.get_players() if p.is_active_rep), None)
        voters = [p for p in group.get_players() if p.is_voter]
        if rep and voters:
            rep_contribution = rep.slider_score * group.rep_multiplier
            voters_total_contribution = sum(p.slider_score for p in voters) * group.voter_multiplier
            return {'rep_contribution': rep_contribution, 'voters_total_contribution': voters_total_contribution, 'collective_pot': group.collective_pot}
        return {}

class SyncAfterVote(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        # Treatment 1 Core Logic: Term Limit Check
        # In this treatment, there is no voting. This page's only purpose is to check
        # if the current representative has completed their 3-round term.
        active_group = next((g for g in subsession.get_groups() if len(g.get_players()) > 1), None)
        if active_group:
            rep = next((p for p in active_group.get_players() if p.is_active_rep), None)
            if rep:
                # Calculate how many consecutive rounds this player has been the representative.
                start_round = subsession.session.vars.get('rep_term_start_round', 0)
                rounds_served = subsession.round_number - start_round + 1
                # If the term is over, mark them for removal.
                if rounds_served >= 3:
                    subsession.rep_was_removed_this_round = True
                    rep_pid = rep.participant.id
                    if rep_pid not in subsession.session.vars['removed_pids']:
                         subsession.session.vars['removed_pids'].append(rep_pid)
    @staticmethod
    def is_displayed(subsession: Subsession):
        return subsession.session.vars.get('current_rep_pid') is not None
    
def after_all_players_arrive(subsession: Subsession):
    active_group = next((g for g in subsession.get_groups() if len(g.get_players()) > 1), None)
    if active_group:
        rep = next((p for p in active_group.get_players() if p.is_active_rep), None)
        if rep:
            rounds_served = 0
            for i in range(subsession.round_number, 0, -1):
                historical_player = rep.in_round(i)
                if historical_player.is_active_rep:
                    rounds_served += 1
                else:
                    break
            if rounds_served >= 3:
                subsession.rep_was_removed_this_round = True
                rep_pid = rep.participant.id
                if rep_pid not in subsession.session.vars['removed_pids']:
                     subsession.session.vars['removed_pids'].append(rep_pid)

class Stage2Decision(Page):
    form_model = 'player'
    form_fields = ['stage2_decision']
    @staticmethod
    def is_displayed(player: Player):
        # T1 Display Rule
        # Show this page ONLY to the representative, and ONLY in the final round of their term.
        # (Note: This logic will need to be updated for T1)
        return player.is_active_rep and player.subsession.rep_was_removed_this_round
    @staticmethod
    def vars_for_template(player: Player):
        return dict(C=C)
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        decision = player.stage2_decision
        group = player.group

        if decision in [1, 2]: 
            player.payoff -= C.STAGE_2_COST

        if decision == 1: 
            group.voter_multiplier = C.BASE_VOTER_SUCCESS_PAYOFF * 0.5
            group.rep_multiplier = C.BASE_REP_SUCCESS_PAYOFF * 0.5
        elif decision == 2: 
            group.voter_multiplier = C.BASE_VOTER_SUCCESS_PAYOFF * 1.5
            group.rep_multiplier = C.BASE_REP_SUCCESS_PAYOFF * 1.5
        else: 
            group.voter_multiplier = C.BASE_VOTER_SUCCESS_PAYOFF
            group.rep_multiplier = C.BASE_REP_SUCCESS_PAYOFF

class PostDecisionWaitPage(WaitPage):
    @staticmethod
    def is_displayed(player: Player):
        return player.subsession.rep_was_removed_this_round

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
                session.vars['rep_term_start_round'] = subsession.round_number + 1
            else: 
                session.vars['current_rep_pid'] = None

class TotalResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.session.vars.get('current_rep_pid') is None

    @staticmethod
    def vars_for_template(player: Player):
        session = player.session
        total_voter_points = session.vars.get('total_voter_points', 0)
        total_rep_points = session.vars.get('total_rep_points', 0)
        
        return {
            'total_voter_points': round(total_voter_points),
            'total_rep_points': round(total_rep_points),
            'your_total_points': round(player.participant.vars.get('total_payoff', 0)),
            'overall_total_points': round(total_voter_points + total_rep_points),
        }

class FinalWaitPage(WaitPage):
    wait_for_all_groups = True
    
    @staticmethod
    def is_displayed(player: Player):
        return player.session.vars.get('current_rep_pid') is None

    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        session = subsession.session
        voter_pids = session.vars['voter_pids']
        
        total_voter_points = 0
        total_rep_points = 0

        for p in subsession.get_players():
            personal_total = sum([p_in_round.payoff for p_in_round in p.in_all_rounds()])
            p.participant.vars['total_payoff'] = personal_total
            
            if p.participant.id in voter_pids:
                total_voter_points += personal_total
            else: 
                total_rep_points += personal_total
        
        session.vars['total_voter_points'] = total_voter_points
        session.vars['total_rep_points'] = total_rep_points


page_sequence = [
    InitializeRoundWaitPage,
    Status,
    SliderTask,
    PayoffWaitPage,
    IncomeResults,
    SyncAfterVote,
    Stage2Decision,
    PostDecisionWaitPage,
    EndOfRoundWaitPage,
    FinalWaitPage,
    TotalResults,
]