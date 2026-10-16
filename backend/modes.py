"""Immutable production mode; the animated renderer stays unchanged while Frame is built."""
from .failures import PipelineFailure

MODES = (
    {'id':'animated','label':'Animierte Strichmännchen','available':True,'design_frozen':True},
    {'id':'frame','label':'Frame','available':False,'preparation_available':True,'design_frozen':False},
)


def require_mode(mode='animated'):
    if mode == 'frame':
        raise PipelineFailure('image','not_ready')
    if mode != 'animated':
        raise ValueError('Unbekannter Herstellungsmodus')
