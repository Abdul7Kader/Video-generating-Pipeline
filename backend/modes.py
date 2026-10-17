"""Immutable production modes with separate animation and measured-still render paths."""

MODES = (
    {'id':'animated','label':'Animierte Strichmännchen','available':True,'design_frozen':True},
    {'id':'frame','label':'Frame','available':True,'preparation_available':True,'design_frozen':False,'acceptance':'series_and_long_video_pending'},
)


def require_mode(mode='animated'):
    if mode not in {'animated','frame'}:
        raise ValueError('Unbekannter Herstellungsmodus')
