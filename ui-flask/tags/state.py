# tags/state.py
import time
from collections import defaultdict
import logging
log = logging.getLogger(__name__)

_TAGS = {}
_DIRTY = set()
_SUBSCRIPTIONS = set()


def update_tag(name, value):
    _TAGS[name] = (value, time.time())
    _DIRTY.add(name)


def get_tag_updates():
    updates = {}
    for t in list(_DIRTY):
        updates[t] = _TAGS[t][0]
        _DIRTY.remove(t)
    return updates


def subscribe_tags(tags):
    _SUBSCRIPTIONS.update(tags)


def unsubscribe_tags(tags):
    for t in tags:
        _SUBSCRIPTIONS.discard(t)


def get_subscriptions():
    return set(_SUBSCRIPTIONS)
