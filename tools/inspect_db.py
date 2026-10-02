"""Look things up in the staged retail database while authoring missions.

    python tools/inspect_db.py variant <id>        level: size, nested templates, units, waypoints
    python tools/inspect_db.py pers [text]         characters whose name contains text
    python tools/inspect_db.py table <name> [col=value ...]   rows of any table
    python tools/inspect_db.py script <id>         print a script's source

Reads build/run/game.db.retail by default; add --built to read the built
game.db (retail plus SS2 content).
"""
import os
import struct
import sys

import config
from ssdb import Database, iter_chunks
from sspack import Package


def waypoint_position(run_dir, waypoint_id, packs={}):
    """(x, y, z, floor) of a waypoint, from the pack or an SS2 loose file; None if missing."""
    if 'Waypoints' not in packs:
        packs['Waypoints'] = Package(os.path.join(run_dir, 'res', 'Waypoints.res'))
    loose = os.path.join(run_dir, 'Waypoints', str(waypoint_id))
    if waypoint_id in packs['Waypoints']:
        data = packs['Waypoints'].read(waypoint_id)
    elif os.path.exists(loose):
        with open(loose, 'rb') as f:
            data = f.read()
    else:
        return None
    x = y = z = 0.0
    floor = 0
    for cid, _, po, ln in iter_chunks(data, 0, len(data)):
        if cid != 1:
            continue
        for fid, _, fp, fl in iter_chunks(data, po, po + ln):
            if fid == 2:
                x, y, z = struct.unpack_from('<fff', data, fp)
            elif fid == 3:
                floor = struct.unpack_from('<i', data, fp)[0]
    return x, y, z, floor


def show_variant(db, run_dir, variant_id):
    variant = db['TemplVariants'].get(variant_id)
    if variant is None:
        sys.exit('no variant %d' % variant_id)
    template = db['Templates'].get(variant['TemplateID'])
    print('variant %d  template %d %r  %dx%d tiles' % (
        variant_id, template['ID'], template['UserName'], template['Width'], template['Height']))
    print('  ' + '  '.join('%s=%r' % (k, variant[k]) for k in (
        'ScriptID', 'DiplomacyID', 'DefaultLight', 'Weather', 'NoAttack', 'AmbientMusic', 'CombatMusic')))

    print('nested templates:')
    for rect in db['Rects'].find(VariantID=variant_id):
        nested = db['Templates'].get(rect['TemplateLink'])
        print('  %-34r at (%.1f, %.1f) floor %d  %gx%g  rot %g' % (
            nested['UserName'] if nested else rect['TemplateLink'], rect['CenterX'], rect['CenterY'],
            rect['Floor'], rect['Width'], rect['Height'], rect['Rotation']))

    placable = db['PlacableObjects']
    print('objects:')
    for element in db['FinalElements'].find(VariantID=variant_id):
        model = placable.get(element['ModelID'])
        print('  %-34r at (%.1f, %.1f) floor %d  rot %g%s' % (
            model['UserName'] if model else element['ModelID'], element['PosX'], element['PosY'],
            element['Floor'], element['Rotation'], '  name %r' % element['Name'] if element['Name'] else ''))

    pers, strings, groups = db['RPGPers'], db['Strings'], db['UnitGroups']
    print('units:')
    for unit in db['Units'].find(VariantID=variant_id):
        who = pers.get(unit['MonsterID'])
        shown = strings.get(who['DisplayName']) if who else None
        group = groups.get(unit['Group'])
        print('  %-12r pers %-4d %-28s (%d, %d) floor %d  player %d  %s%s' % (
            unit['Name'], unit['MonsterID'],
            '%s / %s' % (who['UserName'], shown['String'] if shown else '-') if who else '?',
            unit['PosX'], unit['PosY'], unit['Floor'], unit['Player'], unit['Logic'],
            '  group %d %r' % (group['ID'], group['UserName']) if group else ''))

    names = db['WaypointNames']
    print('waypoints:')
    for waypoint in db['Waypoints'].find(VariantID=variant_id):
        name = names.get(waypoint['NameID'])
        pos = waypoint_position(run_dir, waypoint['ID'])
        where = '(%.1f, %.1f, %.1f) floor %d' % pos if pos else 'no position resource'
        print('  %-18r %s' % (name['UserName'] if name else waypoint['NameID'], where))


def show_pers(db, text):
    strings, classes = db['Strings'], db['RPGClasses']
    for row in db['RPGPers'].rows():
        shown = strings.get(row['DisplayName'])
        label = '%s / %s' % (row['UserName'], shown['String'] if shown else '-')
        if text.lower() not in label.lower():
            continue
        cls = classes.get(row['ClassID'])
        print('%5d  %-44s class %-10s side %-8s weapon %-4d%s' % (
            row['ID'], label, cls['UserName'] if cls else row['ClassID'], row['Side'] or '-',
            row['WeaponID'], '  hireable' if row['CanHired'] else ''))


def show_table(db, name, filters):
    table = db[name]
    where = {}
    types = dict(table.columns)
    for item in filters:
        column, value = item.split('=', 1)
        where[column] = value if types[column] == 3 else (float(value) if types[column] == 2 else int(value))
    print('\t'.join(c for c, _ in table.columns))
    for row in table.find(**where):
        print('\t'.join(repr(v) if isinstance(v, str) else '%g' % v for v in row.values()))


def main():
    sys.stdout.reconfigure(errors='replace')    # retail names include Cyrillic the console may lack
    args = [a for a in sys.argv[1:] if a != '--built']
    if not args:
        sys.exit(__doc__)
    run_dir = config.load()['run']
    db = Database.load(os.path.join(run_dir, 'game.db' if '--built' in sys.argv else 'game.db.retail'))
    command = args[0]
    if command == 'variant':
        show_variant(db, run_dir, int(args[1]))
    elif command == 'pers':
        show_pers(db, args[1] if len(args) > 1 else '')
    elif command == 'table':
        show_table(db, args[1], args[2:])
    elif command == 'script':
        print(db['Scripts'].get(int(args[1]))['CodeText'])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
