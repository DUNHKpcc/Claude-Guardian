"""Entry declaration boundary: unknown members and hostile values are refused with fixed codes.

Synthetic marker only. This is a bounded matrix over the closed entry schema, not arbitrary-secret
recognition: a target alias that is identifier-shaped is accepted by design (see environment_entry._alias).
"""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/claude-guardian/scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
import environment_entry as entry
from environment_entry_fixture import local_entry

MARKER = 'SYNTHSECRETQ7Z9K2'
INJECTIONS = (('password', MARKER), ('command', 'curl ' + MARKER),
              ('url', 'https://example.invalid/?t=' + MARKER))


def walk(value, path=()):
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk(item, path + (key,))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk(item, path + (index,))


def at(root, path):
    for key in path:
        root = root[key]
    return root


class EntryInputBoundaryTests(unittest.TestCase):
    def test_control_is_accepted(self):
        entry.assess_entry(local_entry('mac-a'))

    def test_unknown_members_are_refused_at_every_object_without_echo(self):
        base = local_entry('mac-a')
        paths = [path for path, value in walk(base) if isinstance(value, dict)]
        self.assertGreaterEqual(len(paths), 6)
        for path in paths:
            for key, value in INJECTIONS:
                request = copy.deepcopy(base)
                at(request, path)[key] = value
                with self.subTest(path=path, key=key), self.assertRaises(entry.InvalidProjection) as ctx:
                    entry.assess_entry(request)
                self.assertNotIn(MARKER, str(ctx.exception) + repr(ctx.exception.args))

    def test_hostile_value_in_every_closed_string_field_is_refused_without_echo(self):
        base = local_entry('mac-a')
        alias_paths = {('targets', 0, 'target_ref')}
        for path, value in walk(base):
            if not isinstance(value, str) or path in alias_paths:
                continue
            request = copy.deepcopy(base)
            at(request, path[:-1])[path[-1]] = MARKER
            with self.subTest(path=path), self.assertRaises(entry.InvalidProjection) as ctx:
                entry.assess_entry(request)
            self.assertNotIn(MARKER, str(ctx.exception) + repr(ctx.exception.args))

    def test_alias_shape_refuses_commands_urls_and_free_text(self):
        for alias in ('curl x', 'https://example.invalid/?t=1', 'a;rm', 'a b', '1abc', 'a' * 49, 'x.y',
                      '123e4567-e89b-12d3-a456-426614174000'):
            request = local_entry('mac-a')
            request['targets'][0]['target_ref'] = alias
            with self.subTest(alias=alias[:20]), self.assertRaises(entry.InvalidProjection) as ctx:
                entry.assess_entry(request)
            self.assertEqual(str(ctx.exception), 'E_ALIAS')

    def test_identifier_shaped_alias_is_a_known_limit_not_a_secret_screen(self):
        request = local_entry('mac-a')
        request['targets'][0]['target_ref'] = MARKER
        entry.assess_entry(request)  # accepted by design; sanitization of aliases remains the host's job


if __name__ == '__main__':
    unittest.main()
