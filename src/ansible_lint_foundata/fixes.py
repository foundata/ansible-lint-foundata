# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Small round-trip YAML transformations shared by the rules."""

from ruamel.yaml.comments import CommentedMap, CommentedSeq


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
