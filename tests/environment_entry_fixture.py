"""Explicit synthetic route declarations; never host authorization or evidence."""

def local_entry(target='mac-a'):
    return {'schema_version': 'guardian-environment-entry-input/0.1',
            'route': {'choice': 'local', 'state': 'selected'},
            'targets': [{'role': 'local', 'target_ref': target}],
            'network': {'possession': 'none', 'selection': 'direct',
                        'configuration': 'not_applicable', 'path': 'direct'},
            'local_entry': {'kind': 'none'},
            'final_egress': {'kind': 'direct', 'protocol': 'unknown'},
            'client': 'claude_code'}
