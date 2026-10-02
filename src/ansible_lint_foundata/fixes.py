"""Small round-trip YAML transformations shared by the rules."""

from copy import copy
from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.tokens import CommentToken


def wrap_scalar_list(mapping: CommentedMap, key: str) -> None:
    """Wrap a scalar while moving its trailing comment to the new list item."""
    sequence = CommentedSeq([mapping[key]])
    comments = mapping.ca.items.get(key)
    if comments and comments[2] is not None:
        # Leaving this on the mapping puts scalar trailing whitespace before
        # the new sequence, making the formatter change it on a second pass.
        sequence.ca.items[0] = [comments[2], None, None, None]
        comments[2] = None
    mapping[key] = sequence


def _last_comment_slot(value: CommentedMap | CommentedSeq) -> tuple[list[Any], int]:
    """Locate the comment attached to the final serialized value."""
    key = next(reversed(value)) if isinstance(value, CommentedMap) else len(value) - 1
    child = value[key]
    if isinstance(child, (CommentedMap, CommentedSeq)) and child:
        position = value.lc.data.get(key) if value.lc.data else None
        # An alias's children belong to the earlier anchor definition. Only
        # comments attached to the alias use itself may move with this task.
        if not (
            position is not None
            and child.lc.line is not None
            and child.lc.line < position[0]
        ):
            return _last_comment_slot(child)
    return value.ca.items.setdefault(key, [None, None, None, None]), (
        2 if isinstance(value, CommentedMap) else 0
    )


def reorder_task(mapping: CommentedMap, keys: list[str]) -> None:
    """Move keys without moving following-task comments into this task."""
    comments, index = _last_comment_slot(mapping)
    token = comments[index]
    trailing = None
    if isinstance(token, CommentToken) and "\n" in token.value:
        inline, _, rest = token.value.partition("\n")
        if rest:
            trailing = copy(token)
            trailing.value = "\n" + rest
            if inline:
                token.value = inline + "\n"
            else:
                comments[index] = None
    for key in keys:
        mapping.move_to_end(key)
    if trailing is not None:
        comments, index = _last_comment_slot(mapping)
        existing = comments[index]
        if isinstance(existing, CommentToken):
            existing.value = existing.value.rstrip("\n") + trailing.value
        else:
            comments[index] = trailing
