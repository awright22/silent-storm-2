"""Round-trip checks for ssdb against a real game.db.

    python tools/test_ssdb.py <path-to-game.db>

Never writes to the input file. Exit code 0 = all checks passed.
"""
import os
import sys
import tempfile

from ssdb import Database


def main():
    path = sys.argv[1]
    with open(path, 'rb') as f:
        original = f.read()
    db = Database.load(path)
    rows = sum(len(t) for t in db.tables.values())
    print('%d tables, %d rows, %d bytes' % (len(db.tables), rows, len(original)))

    # 1. untouched save is byte-identical
    assert db.to_bytes() == original, 'untouched save differs'
    print('PASS  untouched save is byte-identical')

    # 2. every table re-encodes to its original bytes (exercises the full encoder)
    for table in db.tables.values():
        assert table._encode() == table._body, 're-encode differs: %s' % table.name
    print('PASS  all %d tables re-encode byte-identically' % len(db.tables))

    # 3. edit, save, reload: the edit is there and nothing else moved
    scripts = db['Scripts']
    before = len(scripts)
    template_id = scripts.ids()[0]
    new_id = scripts.max_id() + 1
    marker = '-- ssdb round-trip ✓ тест\n' + 'x' * 500
    scripts.clone(template_id, new_id, CodeText=marker)
    strings = db['Strings']
    some_id = strings.ids()[0]
    old_row = strings.get(some_id)
    text_col = [c for c, t in strings.columns if t == 3][0]
    strings.upsert(some_id, **{text_col: 'edited'})

    fd, tmp = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    try:
        db.save(tmp)
        db2 = Database.load(tmp)
    finally:
        os.remove(tmp)
    assert len(db2['Scripts']) == before + 1
    assert db2['Scripts'].get(new_id)['CodeText'] == marker
    assert db2['Strings'].get(some_id)[text_col] == 'edited'
    expect = dict(old_row)
    expect[text_col] = 'edited'
    assert db2['Strings'].get(some_id) == expect
    untouched = Database.load(path)
    for tid, table in db2.tables.items():
        if table.name not in ('Scripts', 'Strings'):
            assert table._body == untouched.tables[tid]._body, 'unrelated table changed: %s' % table.name
    print('PASS  edit survives save and reload; other tables unchanged')

    with open(path, 'rb') as f:
        assert f.read() == original, 'input file was modified'
    print('PASS  input file untouched')


if __name__ == '__main__':
    main()
