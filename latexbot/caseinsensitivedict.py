"""
A case-insensitive dictionary that keeps the original case of the keys.

From https://stackoverflow.com/a/30221547/5745575.
"""
import typing


class CaseInsensitiveKey:
    """
    A key for the case insensitive dict.
    """
    def __init__(self, key: str):
        self.key = key
    
    def __hash__(self):
        return hash(self.key.casefold())
    
    def __eq__(self, other: "CaseInsensitiveKey"):
        return self.key.casefold() == other.key.casefold()
    
    def __str__(self):
        return self.key
    
    def __repr__(self):
        return self.key


class CaseInsensitiveDict(dict):
    """
    A simple case-insensitive dictionary that keeps the original case of the key.
    """
    def __init__(self, d: typing.Dict[str, typing.Any] = None):
        super().__init__()
        if d is None:
            return
        for k, v in d.items():
            self.__setitem__(k, v)

    def __setitem__(self, key, value):
        return super().__setitem__(CaseInsensitiveKey(key), value)
    
    def __getitem__(self, key):
        return super().__getitem__(CaseInsensitiveKey(key))
    
    def __contains__(self, key):
        return super().__contains__(CaseInsensitiveKey(key))
    
    def __delitem__(self, key):
        return super().__delitem__(CaseInsensitiveKey(key))
    
    def pop(self, k, d=None):
        return super().pop(CaseInsensitiveKey(k), d)
    
    def get(self, key, default=None):
        return super().get(CaseInsensitiveKey(key), default)
    
    def to_dict(self):
        return {k: v for k, v in self.items()}
    
    def items(self):
        return ((k.key, v) for k, v in super().items())
