# tags/historian_null.py

class NullHistorian:
    def handle_tag_updates(self, updates: dict):
        pass

    def query_history(self, *args, **kwargs):
        return []