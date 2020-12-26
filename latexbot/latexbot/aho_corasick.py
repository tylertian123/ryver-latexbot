"""
Aho-Corasick implementation for keyword matching.
"""

import typing
from collections import deque

class Node:
    """
    A node in the automaton's trie.
    """

    __slots__ = ("next", "leaf_value", "parent", "char", "fail")

    def __init__(self, parent: "Node", char: str):
        self.next = dict()
        self.leaf_value = None
        self.parent = parent
        self.char = char
        self.fail = None

    def __repr__(self):
        return f"Node(leaf={self.leaf_value}, char={self.char})"


class Automaton:
    """
    An Aho-Corasick algorithm DFA.
    """

    __slots__ = ("trie_root", "leaves")

    def __init__(self):
        self.trie_root = Node(None, None)
        self.trie_root.fail = self.trie_root
        self.leaves = []

    def trie_find(self, s: str) -> typing.Optional[Node]:
        """
        Find the leaf node representing a string in the trie.

        If it does not exist, return None.
        """
        node = self.trie_root
        for c in s:
            if c in node.next:
                node = node.next[c]
            else:
                return None
        return node

    def add_str(self, s: str, value: typing.Any = None) -> None:
        """
        Add a string to the trie with an optional value.
        """
        node = self.trie_root
        for c in s:
            if c not in node.next:
                node.next[c] = Node(node, c)
            node = node.next[c]
        node.leaf_value = value if value is not None else s

    def del_str(self, s: str) -> None:
        """
        Delete a string from the trie.
        """
        node = self.trie_find(s)
        if node is None:
            raise ValueError
        # Delete from the leaf back up the tree until we reach the root
        # or until a fork
        while node is not self.trie_root:
            node.parent.next.pop(node.char)
            node = node.parent
            if node.next:
                break

    def get_failure_link(self, node: Node) -> Node:
        """
        Get the failure link (build it if necessary) for the given node.
        """
        if node.fail is None:
            if node is self.trie_root or node.parent is self.trie_root:
                node.fail = self.trie_root
                return self.trie_root
            else:
                parent_link = node
                while True:
                    parent_link = self.get_failure_link(parent_link.parent)
                    if node.char in parent_link.next:
                        node.fail = parent_link.next[node.char]
                        return node.fail
                    elif parent_link is self.trie_root:
                        node.fail = self.trie_root
                        return node.fail
        return node.fail

    def build_automaton(self) -> None:
        """
        Build/rebuild the automaton from the trie.
        """
        d = deque()
        d.append(self.trie_root)
        while d:
            node = d.pop()
            # Clear failure link to reset
            node.fail = None
            self.get_failure_link(node)
            for n in node.next.values():
                d.append(n)

    def find_all(self, s: str) -> typing.Iterable[typing.Tuple[int, typing.Any]]:
        """
        Iterate over all matches for a given string.

        Gives (index, value). Note the index returned is of the rightmost character in the match.
        """
        node = self.trie_root
        for i, c in enumerate(s):
            while c not in node.next:
                if node is self.trie_root:
                    break
                node = node.fail
            else:
                node = node.next[c]
                if node.leaf_value is not None:
                    yield (i, node.leaf_value)
