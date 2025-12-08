from otree.api import *
import random

# The PlayerWithRotation class has been REMOVED.

def setup_rotation(subsession: BaseSubsession):
    """This is the main engine function. It sets up and executes the rotation."""
    session = subsession.session
    
    # DEFINITIVE FIX: Use subsession.constants to get the C class
    C = subsession.constants

    # --- ONE-TIME SETUP (ROUND 1 ONLY) ---
    if subsession.round_number == 1:
        participants = session.get_participants()
        random.shuffle(participants)
        
        voter_participants = participants[:C.NUM_VOTERS]
        # ... rest of the function is the same
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


def T2a_EndOfRound(subsession: BaseSubsession):
    # ... (this function is exactly the same as before)
    session = subsession.session
    removed_rep = next((p for p in subsession.get_players() if p.was_removed_this_round), None)
    if removed_rep:
        session.vars['removed_pids'].append(removed_rep.participant.id)
        if session.vars['rep_pool_pids']:
            session.vars['current_rep_pid'] = session.vars['rep_pool_pids'].pop(0)
        else:
            session.vars['current_rep_pid'] = None