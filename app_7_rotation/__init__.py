from otree.api import *

# Imports a shared module (not used in this file)
import shared_out
# Imports Python's random library
import random

# Docstring for the app
doc = 'A minimal, robust implementation of the representative rotation mechanic using a subsession bridge.'

# Defines constants for the app
class C(BaseConstants):
    # Sets the app's URL name
    NAME_IN_URL = 'app_7_rotation'
    # Disables automatic grouping
    PLAYERS_PER_GROUP = None
    # Sets the maximum number of rounds
    NUM_ROUNDS = 10
    # Sets the number of voters
    NUM_VOTERS = 3

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

# Defines the 'Status' page
class Status(Page):
    # Passes variables to the HTML template
    @staticmethod
    def vars_for_template(player: Player):
        # Passes the entire session.vars dictionary to the template
        return { 'session_vars': player.session.vars }

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

# Defines the 'ResultsPage'
class ResultsPage(Page):
    # Passes variables to the HTML template
    @staticmethod
    def vars_for_template(player: Player):
        # Passes the entire session.vars dictionary to the template
        return { 'session_vars': player.session.vars }

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
    EndOfRoundWaitPage,
    EndOfGame,
]