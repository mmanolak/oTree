
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

doc = 'Treatment 3: Term Limit (policy choice only after surviving term).'
class C(BaseConstants):
    NAME_IN_URL = 'term_limit'
    PLAYERS_PER_GROUP = 4
    NUM_ROUNDS = 20
class Subsession(BaseSubsession):
    pass
class Group(BaseGroup):
    pass
class Player(BasePlayer):
    pass
class Task(Page):
    form_model = 'player'
class AfterTaskWait(WaitPage):
    pass
class Vote(Page):
    form_model = 'player'
class AfterVoteWait(WaitPage):
    pass
class RoundResults(Page):
    form_model = 'player'
page_sequence = [Task, AfterTaskWait, Vote, AfterVoteWait, RoundResults]