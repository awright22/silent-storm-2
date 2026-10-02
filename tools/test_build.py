"""Check a built game.db against the retail copy it was built from.

    python tools/test_build.py

Run after tools/build.py. Verifies the rule the whole content layer rests on:
SS2 only adds rows.

  1. Every retail row is still present and unchanged.
  2. Every added row is either in an SS2 ID range or one of the engine port's
     UI patch rows (UIControls only).

Exit code 0 = both hold.
"""
import os
import sys

import config
import content
from ssdb import Database


def main():
    run = config.load()['run']
    retail = Database.load(os.path.join(run, 'game.db.retail'))
    built = Database.load(os.path.join(run, 'game.db'))
    problems = []
    added = {}

    for tid, old in retail.tables.items():
        new = built.tables.get(tid)
        if new is None:
            problems.append('table %s is missing' % old.name)
            continue
        if new.encode() == old.encode():
            continue                    # byte-identical table, nothing to compare
        if new.columns != old.columns:
            problems.append('table %s: columns changed' % old.name)
            continue
        for rid in old.ids():
            if new.get(rid) != old.get(rid):
                problems.append('%s row %d was %s' % (old.name, rid, 'removed' if rid not in new else 'modified'))
                if len(problems) > 20:
                    break
        retail_ids = set(old.ids())
        extra = [rid for rid in new.ids() if rid not in retail_ids]
        if extra:
            added[old.name] = extra
    for tid in built.tables:
        if tid not in retail.tables:
            problems.append('table 0x%08X was added' % tid)

    for name, ids in sorted(added.items()):
        ss2 = [rid for rid in ids if rid >= content.SINGLE_BASE]
        other = [rid for rid in ids if rid < content.SINGLE_BASE]
        print('%-22s +%d SS2 rows%s' % (name, len(ss2), ', +%d engine patch rows' % len(other) if other else ''))
        if other and name != 'UIControls':
            problems.append('%s: %d added rows outside the SS2 ID ranges, e.g. %d' % (name, len(other), other[0]))

    if problems:
        print('\nFAIL')
        for problem in problems:
            print('  ' + problem)
        sys.exit(1)
    print('\nPASS  %d retail tables intact; rows added in %d tables' % (len(retail.tables), len(added)))


if __name__ == '__main__':
    main()
