from otree.api import *
import random

# Docstring for the app
doc = 'Treatment 2a: Simple Vote-Out, adapted from the working floating_rotation.'

# Defines constants for the app
class C(BaseConstants):
    # Sets the app's URL name
    NAME_IN_URL = 'app_4_treatment2a'
    # Disables automatic grouping
    PLAYERS_PER_GROUP = None
    # Sets the maximum number of rounds
    NUM_ROUNDS = 10
    # Sets the number of voters
    NUM_VOTERS = 3
    # Sets the cost for Stage 2 actions
    STAGE_2_COST = 50

# Defines subsession-level properties
class Subsession(BaseSubsession):
    # Bridge field to pass the removed rep's ID between wait pages
    pid_of_removed_rep = models.IntegerField(initial=None)

# Function that runs at the beginning of each round
def creating_session(subsession: Subsession):
    # Gets the session-wide variables
    session = subsession.session
    # Checks if it is the first round
    if subsession.round_number == 1:
        # Gets all participants in the session
        participants = session.get_participants()
        # Randomizes the order of participants
        random.shuffle(participants)
        # Selects the first N participants to be voters
        voter_participants = participants[:C.NUM_VOTERS]
        # Selects the remaining participants for the representative pool
        rep_pool_participants = participants[C.NUM_VOTERS:]
        # Stores the permanent IDs of voters
        session.vars['voter_pids'] = [p.id for p in voter_participants]
        # Stores the permanent IDs of the pool
        session.vars['rep_pool_pids'] = [p.id for p in rep_pool_participants]
        # Initializes a list to store IDs of removed reps
        session.vars['removed_pids'] = []
        # Checks if there are representatives in the pool
        if session.vars['rep_pool_pids']:
            # Promotes the first person from the pool to be the representative
            session.vars['current_rep_pid'] = session.vars['rep_pool_pids'].pop(0)
        else:
            # Sets the current rep to None if the pool is empty
            session.vars['current_rep_pid'] = None
    
    # Gets the permanent lists of player IDs
    voter_pids = session.vars['voter_pids']
    current_rep_pid = session.vars.get('current_rep_pid')
    removed_pids = session.vars['removed_pids']
    
    # Loops through each player for the current round
    for p in subsession.get_players():
        # Gets the player's permanent ID
        pid = p.participant.id
        # Assigns the 'voter' role
        if pid in voter_pids:
            p.is_voter = True
            p.is_active_rep = False
        # Assigns the 'representative' role
        elif pid == current_rep_pid:
            p.is_voter = False
            p.is_active_rep = True
        # Assigns inactive status
        else:
            p.is_voter = False
            p.is_active_rep = False

    # Creates a list of active players for this round
    active_players = [p for p in subsession.get_players() if p.is_voter or p.is_active_rep]
    # Creates a list of inactive players
    inactive_players = [p for p in subsession.get_players() if not (p.is_voter or p.is_active_rep)]
    # Initializes the grouping structure
    group_matrix = []
    # Puts all active players into one group
    if active_players: group_matrix.append(active_players)
    # Puts each inactive player into their own group of one
    for p in inactive_players: group_matrix.append([p])
    # Sets the group structure for the round
    subsession.set_group_matrix(group_matrix)

# Defines group-level properties
class Group(BaseGroup):
    # Stores the number of votes to remove the rep
    num_remove_votes = models.IntegerField(initial=0)

# Defines player-level properties
class Player(BasePlayer):
    # Stores the voter's decision
    vote_choice = models.BooleanField(label='Do you want to replace the current representative?', choices=[[True, 'Replace'], [False, 'Keep']], widget=widgets.RadioSelect)
    # Stores if the player is a voter this round
    is_voter = models.BooleanField(initial=False)
    # Stores if the player is the representative this round
    is_active_rep = models.BooleanField(initial=False)
    # Temporary flag to identify the rep removed in the current round
    was_removed_this_round = models.BooleanField(initial=False)
    # Stores the removed representative's legacy decision
    stage2_decision = models.IntegerField(widget=widgets.RadioSelect, choices=[[1, 'Sabotage'], [2, 'Help'], [0, 'Neutral']])

# --- PAGES ---
# Defines the 'Status' page
class Status(Page):
    # Determines if the page is shown to a player
    @staticmethod
    def is_displayed(player: Player):
        # Shows page only if there is an active representative
        return player.session.vars.get('current_rep_pid') is not None
    
    # Passes variables to the HTML template
    @staticmethod
    def vars_for_template(player: Player):
        # Passes the session-wide state variables to the template
        return {
            'voter_pids': player.session.vars.get('voter_pids'),
            'current_rep_pid': player.session.vars.get('current_rep_pid'),
            'rep_pool_pids': player.session.vars.get('rep_pool_pids'),
            'removed_pids': player.session.vars.get('removed_pids'),
        }

# Defines the 'VotingPage'
class VotingPage(Page):
    # Binds the page to the Player model
    form_model = 'player'
    # Specifies which player field is a form field on this page
    form_fields = ['vote_choice']
    # Determines if the page is shown to a player
    @staticmethod
    def is_displayed(player: Player):
        # Shows page only if the player is a voter
        return player.is_voter
    # Passes variables to the HTML template
    @staticmethod
    def vars_for_template(player: Player):
        # Passes the current representative's ID to the template
        return {'active_rep_id': player.session.vars.get('current_rep_pid')}

# Defines the 'SyncAfterVote' wait page
class SyncAfterVote(WaitPage):
    # Waits for all players in the session
    wait_for_all_groups = True
    # Function that runs after all players arrive
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        # Finds the active group (more than 1 player)
        active_group = next((g for g in subsession.get_groups() if len(g.get_players()) > 1), None)
        # Checks if an active group exists
        if active_group:
            # Finds the representative in the active group
            rep = next((p for p in active_group.get_players() if p.is_active_rep), None)
            # Checks if a representative was found
            if rep:
                # Gets the voters from the active group
                voters = [p for p in active_group.get_players() if p.is_voter]
                # Counts the number of 'Replace' votes
                replace_votes = sum(1 for v in voters if v.field_maybe_none('vote_choice') is True)
                # Stores the vote count on the group
                active_group.num_remove_votes = replace_votes
                # Checks if the replacement threshold was met
                if replace_votes > (C.NUM_VOTERS / 2):
                    # Writes the removed rep's ID to the subsession bridge field
                    subsession.pid_of_removed_rep = rep.participant.id
                    # Sets a temporary flag on the player for the Stage2Decision page
                    rep.was_removed_this_round = True

# Defines the 'ResultsPage'
class ResultsPage(Page):
    # Determines if the page is shown to a player
    @staticmethod
    def is_displayed(player: Player):
        # Shows page only if there is an active representative
        return player.session.vars.get('current_rep_pid') is not None
    # Passes variables to the HTML template
    @staticmethod
    def vars_for_template(player: Player):
        # Gets the session-wide variables
        session = player.session
        # Finds the active group
        active_group = next((g for g in player.subsession.get_groups() if len(g.get_players()) > 1), None)
        # Checks if an active group exists
        if active_group:
            # Gets the number of replace votes
            replace_votes = active_group.num_remove_votes
            # Determines the vote outcome string
            vote_result = "Replace" if replace_votes > (C.NUM_VOTERS / 2) else "Keep"
        else:
            # Sets default values if no active group
            replace_votes = 0; vote_result = "N/A"
        # Variable to store the next representative's ID
        next_rep_pid = None
        # Checks if the representative was kept
        if vote_result == "Keep":
            # Next rep is the same as the current one
            next_rep_pid = session.vars.get('current_rep_pid')
        else:
            # Checks if the pool is not empty
            if session.vars['rep_pool_pids']:
                # Shows the ID of the next person in the pool
                next_rep_pid = session.vars['rep_pool_pids'][0]
            else:
                # Indicates the pool is empty
                next_rep_pid = "None (Pool is empty)"
        # Returns all necessary variables to the template
        return {
            'replace_votes': replace_votes,
            'keep_votes': C.NUM_VOTERS - replace_votes,
            'vote_result': vote_result,
            'next_rep_pid': next_rep_pid,
        }

# Defines the 'Stage2Decision' page
class Stage2Decision(Page):
    # Binds the page to the Player model
    form_model = 'player'
    # Specifies which player field is a form field on this page
    form_fields = ['stage2_decision']
    # Determines if the page is shown to a player
    @staticmethod
    def is_displayed(player: Player):
        # Shows page only to the player who was just removed
        return player.field_maybe_none('was_removed_this_round') is True

    # Function that runs before the player leaves the page
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        # Saves the decision to a permanent participant variable
        player.participant.stage2_decision_made = player.stage2_decision
        # Applies the cost for Sabotage or Help actions
        if player.stage2_decision in [1, 2]:
            player.payoff -= C.STAGE_2_COST

# Defines the 'EndOfRoundWaitPage'
class EndOfRoundWaitPage(WaitPage):
    # Waits for all players in the session
    wait_for_all_groups = True
    # Function that runs after all players arrive
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        # Gets the session-wide variables
        session = subsession.session
        
        # Safely reads the removed rep's ID from the subsession bridge
        removed_pid = subsession.field_maybe_none('pid_of_removed_rep')
        
        # Checks if a representative was removed
        if removed_pid:
            # Adds the removed rep's ID to the permanent removed list
            session.vars['removed_pids'].append(removed_pid)
            # Checks if the representative pool is not empty
            if session.vars['rep_pool_pids']:
                # Promotes the next person from the pool
                session.vars['current_rep_pid'] = session.vars['rep_pool_pids'].pop(0)
            else:
                # Sets the current rep to None if the pool is empty
                session.vars['current_rep_pid'] = None

# Defines the 'EndOfGame' page
class EndOfGame(Page):
    # Determines if the page is shown to a player
    @staticmethod
    def is_displayed(player: Player):
        # Shows page only if there is no active representative
        return player.session.vars.get('current_rep_pid') is None

# Defines the order of pages in the app
page_sequence = [
    Status,
    VotingPage,
    SyncAfterVote,
    ResultsPage,
    Stage2Decision,
    EndOfRoundWaitPage,
    EndOfGame,
]