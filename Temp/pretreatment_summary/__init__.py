
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

doc = 'Summarize pre-treatment game payoffs, rank players, and assign treatment roles.'
class C(BaseConstants):
    NAME_IN_URL = 'pretreatment_summary'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
class Subsession(BaseSubsession):
    roles_assigned = models.BooleanField()
class Group(BaseGroup):
    pass
class Player(BasePlayer):
    rank_ultimatum = models.IntegerField()
    rank_dictator = models.IntegerField()
    rank_jod = models.IntegerField()
    rank_overall = models.IntegerField()
class Summary(Page):
    form_model = 'player'
page_sequence = [Summary]