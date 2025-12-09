from otree.api import *
import random

doc = 'Treatment 2b (Betrayal): Voters can remove the representative at any round end, but randomly backfires.'

class C(BaseConstants):
    # App-level Constants
    NAME_IN_URL = 'app_5_treatment2b'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 10
    NUM_VOTERS = 3
    STAGE_2_COST = 50
    REP_SALARY = 150
    BASE_VOTER_SUCCESS_PAYOFF = 5
    BASE_REP_SUCCESS_PAYOFF = 50
    INDEFINITE_HORIZON_START_ROUND = 6
    CONTINUATION_PROBABILITY = 0.90
    OPPOSITE_OUTCOME_PROB = 0.40 # 40% "chaos" probability

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
        else:
            session.vars['current_rep_pid'] = None
        session.vars['game_over'] = False
    
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
    wait_for_all_groups = True
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        # Per-Round Setup
        # This logic runs at the start of every round to assign roles and create groups.
        
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
        if player.session.vars.get('game_over', False):
            return False
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
        if player.session.vars.get('game_over', False):
            return False
        return (player.is_voter or player.is_active_rep) and player.session.vars.get('current_rep_pid') is not None

class PayoffWaitPage(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def is_displayed(subsession: Subsession):
        if subsession.session.vars.get('game_over', False):
            return False
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
        if player.session.vars.get('game_over', False):
            return False
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

class VotingPage(Page):
    form_model = 'player'
    form_fields = ['vote_choice']
    @staticmethod
    def is_displayed(player: Player):
        if player.session.vars.get('game_over', False):
            return False
        return player.is_voter and player.session.vars.get('current_rep_pid') is not None
    @staticmethod
    def vars_for_template(player: Player):
        return {'active_rep_id': player.session.vars.get('current_rep_pid')}

class SyncAfterVote(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def is_displayed(subsession: Subsession):
        if subsession.session.vars.get('game_over', False):
            return False
        return subsession.session.vars.get('current_rep_pid') is not None
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        active_group = next((g for g in subsession.get_groups() if len(g.get_players()) > 1), None)
        if active_group:
            rep = next((p for p in active_group.get_players() if p.is_active_rep), None)
            if rep:
                # --- NEW LOGIC FOR TREATMENT 2b (CHAOS) ---

                # 1. Count votes to determine the intended outcome
                voters = [p for p in active_group.get_players() if p.is_voter]
                replace_votes = sum(1 for v in voters if v.field_maybe_none('vote_choice') is True)
                active_group.num_remove_votes = replace_votes
                
                intended_to_be_removed = replace_votes > (C.NUM_VOTERS / 2)

                # 2. Roll the die to see if the "opposite" outcome occurs
                is_opposite_outcome = random.random() < C.OPPOSITE_OUTCOME_PROB 

                # 3. Determine the final outcome
                final_is_removed = False
                if is_opposite_outcome:
                    # The opposite of the intended outcome happens
                    final_is_removed = not intended_to_be_removed
                else:
                    # The intended outcome happens
                    final_is_removed = intended_to_be_removed
                
                # 4. If the final outcome is removal, update the state
                if final_is_removed:
                    subsession.rep_was_removed_this_round = True
                    rep_pid = rep.participant.id
                    if rep_pid not in subsession.session.vars['removed_pids']:
                         subsession.session.vars['removed_pids'].append(rep_pid)

class Stage2Decision(Page):
    form_model = 'player'
    form_fields = ['stage2_decision']
    @staticmethod
    def is_displayed(player: Player):
        if player.session.vars.get('game_over', False):
            return False
        # T2a Display Rule
        # Show this page to the current representative IF they were just voted out in this round.
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
            player.session.vars['legacy_effect'] = "Sabotage"
        elif decision == 2: 
            group.voter_multiplier = C.BASE_VOTER_SUCCESS_PAYOFF * 1.5
            group.rep_multiplier = C.BASE_REP_SUCCESS_PAYOFF * 1.5
            player.session.vars['legacy_effect'] = "Help"
        else: 
            group.voter_multiplier = C.BASE_VOTER_SUCCESS_PAYOFF
            group.rep_multiplier = C.BASE_REP_SUCCESS_PAYOFF
            player.session.vars['legacy_effect'] = "Neutral"

class PostDecisionWaitPage(WaitPage):
    @staticmethod
    def is_displayed(player: Player):
        if player.session.vars.get('game_over', False):
            return False
        return player.subsession.rep_was_removed_this_round

class VotingResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        if player.session.vars.get('game_over', False):
            return False
        return (player.is_voter or player.is_active_rep) and player.session.vars.get('current_rep_pid') is not None
    @staticmethod
    def vars_for_template(player: Player):
        session = player.session
        active_group = next((g for g in player.subsession.get_groups() if len(g.get_players()) > 1), None)
        if active_group:
            replace_votes = active_group.num_remove_votes
            vote_result = "Replace" if replace_votes > (C.NUM_VOTERS / 2) else "Keep"
        else:
            replace_votes = 0; vote_result = "N/A"
        next_rep_pid = None
        if vote_result == "Keep": next_rep_pid = session.vars.get('current_rep_pid')
        else:
            if session.vars['rep_pool_pids']: next_rep_pid = session.vars['rep_pool_pids'][0]
            else: next_rep_pid = "None (Pool is empty)"
        return {'replace_votes': replace_votes, 'keep_votes': C.NUM_VOTERS - replace_votes, 'vote_result': vote_result, 'next_rep_pid': next_rep_pid}

class EndOfRoundWaitPage(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def is_displayed(subsession: Subsession):
        if subsession.session.vars.get('game_over', False):
            return False
        return subsession.session.vars.get('current_rep_pid') is not None
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        session = subsession.session
        
        # 1. Check for random termination First
        if not session.vars['game_over'] and subsession.round_number >= C.INDEFINITE_HORIZON_START_ROUND:
            if random.random() > C.CONTINUATION_PROBABILITY:
                session.vars['game_over'] = True

        # 2. Only if the game is not over, promote the next representative
        if not session.vars['game_over']:
            if subsession.rep_was_removed_this_round:
                if session.vars['rep_pool_pids']: 
                    session.vars['current_rep_pid'] = session.vars['rep_pool_pids'].pop(0)
                    # Note: rep_term_start_round is not needed for T2a, but is for T3
                    session.vars['rep_term_start_round'] = subsession.round_number + 1
                else: 
                    session.vars['current_rep_pid'] = None


class TotalResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        pool_is_empty = player.session.vars.get('current_rep_pid') is None
        random_end_triggered = player.session.vars.get('game_over', False)
        is_max_round = player.round_number == C.NUM_ROUNDS

        return pool_is_empty or random_end_triggered or is_max_round

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
        pool_is_empty = player.session.vars.get('current_rep_pid') is None
        random_end_triggered = player.session.vars.get('game_over', False)
        is_max_round = player.round_number == C.NUM_ROUNDS

        return pool_is_empty or random_end_triggered or is_max_round

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
    VotingPage,
    SyncAfterVote,
    Stage2Decision,
    PostDecisionWaitPage,
    VotingResults,
    EndOfRoundWaitPage,
    FinalWaitPage,
    TotalResults,
]
