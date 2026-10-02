"""Compile SS2 content sources (game/) into game.db rows and loose resources.

A mission is a directory under game/missions/ holding mission.toml and a Lua
script. It takes its level geometry from a retail map variant (the "shell"):
the shell's placement rows are copied under new IDs and its terrain/building
resources are copied to loose files, then the mission's own units, waypoints
and script are added. Retail rows are never modified, so the original
campaigns keep working next to SS2 content.

ID plan (retail maxima: variants 8021, scripts 126, final elements 121282):
    mission N       variant / template / script / diplomacy  50000 + N
                    every other row                           1000000 + N*10000 + n
Variant IDs stay below 65536 because some resource keys pack a part number
into the high 16 bits.
"""
import os
import struct
import tomllib

import lualint
from ssdb import emit
from sspack import Package

SINGLE_BASE = 50000
BULK_BASE = 1000000
BULK_BLOCK = 10000

# tables whose rows place things in a variant, and the column naming the variant
PLACEMENT_TABLES = {
    'Rects': 'VariantID', 'FinalElements': 'VariantID', 'Walls': 'VariantID',
    'Floors': 'VariantID', 'SolidObjects': 'VariantID', 'Containers': 'VariantID',
    'Rooms': 'VariantID', 'IntermediateFloors': 'VariantID',
    'IntermediateSolids': 'VariantID', 'Explosions': 'VariantID',
    'TerrainSpots': 'PlacementID',
}
VARIANT_PACKS = ('Terrain', 'Buildings')    # resources keyed by variant ID

# tables giving a character its starting equipment, keyed by RPGPersID
EQUIPMENT_TABLES = (
    'RPGWeapon4Pers', 'RPGClip4Pers', 'RPGGrenade4Pers', 'RPGFirstAid4Pers', 'RPGMeleeWeapon4Pers',
    'RPGMineDetector4Pers', 'RPGMines4Pers', 'RPGTool4Pers',
)

POSES = ('Stand', 'Crouch', 'Crawl')

# named times of day -> the retail AmbientLights row used for them
LIGHTS = {'day': 106, 'night': 108, 'dusk': 65}

# What the retail fonts can draw: ASCII, Cyrillic and a few typographic marks.
# Accented Latin letters are missing and render as a placeholder box.
DIALOGUE_CHARS = (set(map(chr, range(0x20, 0x7F))) | set(map(chr, range(0x410, 0x450))) | set('ЁёІіЇїЄє')
                  | set('‘’“”–—…«»№™'))


class Build:
    """One content build: the database being edited plus loose-resource output."""

    def __init__(self, db, run_dir):
        self.db = db
        self.run_dir = run_dir
        self._packs = {}
        self.resources = {}     # (pack name, file id) -> bytes
        self.common_script = ''
        self.test = False       # compile each mission's test.lua into its script
        self.skip_dialogue = False      # dialogues are logged, not shown (unattended runs)

    def pack(self, name):
        if name not in self._packs:
            self._packs[name] = Package(os.path.join(self.run_dir, 'res', name + '.res'))
        return self._packs[name]

    def copy_resource(self, pack_name, src_id, dst_id):
        pack = self.pack(pack_name)
        if src_id in pack:
            self.resources[(pack_name, dst_id)] = pack.read(src_id)

    def write_resources(self):
        """Write loose files as <run>/<Pack>/<id>, replacing earlier SS2 output."""
        for pack_name in {name for name, _ in self.resources} | set(VARIANT_PACKS) | {'Waypoints', 'Units'}:
            folder = os.path.join(self.run_dir, pack_name)
            if os.path.isdir(folder):
                for name in os.listdir(folder):
                    os.remove(os.path.join(folder, name))
        for (pack_name, file_id), data in self.resources.items():
            folder = os.path.join(self.run_dir, pack_name)
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, str(file_id)), 'wb') as f:
                f.write(data)


class _Ids:
    def __init__(self, slot):
        self.single = SINGLE_BASE + slot
        self._base = BULK_BASE + slot * BULK_BLOCK
        self._next = {}

    def new(self, table):
        n = self._next.get(table, 0)
        if n >= BULK_BLOCK:
            raise ValueError('mission needs more than %d rows in %s' % (BULK_BLOCK, table))
        self._next[table] = n + 1
        return self._base + n


def waypoint_resource(x, y, z=0.0, floor=0, rotation=0):
    """Bytes of a Waypoints/<id> resource: position in tiles within the variant."""
    body = (emit(2, struct.pack('<fff', x, y, z)) + emit(3, struct.pack('<i', floor))
            + emit(4, struct.pack('<i', rotation)) + emit(5, b''))
    return emit(1, body) + emit(0, b'') + emit(2, b'')


def route_resource(waypoint_name_ids):
    """Bytes of a Units/<id> resource: one patrol route as a list of waypoint name IDs."""
    points = struct.pack('<%di' % len(waypoint_name_ids), *waypoint_name_ids)
    route = emit(2, emit(1, struct.pack('<i', len(waypoint_name_ids))) + emit(2, points))
    return emit(1, emit(2, emit(1, route))) + emit(0, b'') + emit(2, b'')


def compile_mission(build, mission_dir):
    with open(os.path.join(mission_dir, 'mission.toml'), 'rb') as f:
        spec = tomllib.load(f)
    db = build.db
    slot = spec['slot']
    if not 1 <= slot <= 9999:
        raise ValueError('%s: slot must be 1..9999' % mission_dir)
    ids = _Ids(slot)
    variant_id = ids.single
    tag = 'SS2\\%s' % spec['name']
    shell = spec['shell']
    variants = db['TemplVariants']
    shell_row = variants.get(shell)
    if shell_row is None:
        raise ValueError('%s: shell variant %d does not exist' % (mission_dir, shell))
    if variant_id in variants:
        raise ValueError('%s: slot %d is already used' % (mission_dir, slot))

    # own template (so retail template roulette never picks this variant) and the variant itself
    db['Templates'].clone(shell_row['TemplateID'], ids.single, UserName=tag)
    variants.clone(shell, variant_id, TemplateID=ids.single, ScriptID=ids.single, RndWeight=1.0,
                   **spec.get('variant', {}))

    # level geometry: the shell's placement rows and variant-keyed resources
    for table_name, column in PLACEMENT_TABLES.items():
        table = db[table_name]
        for row in list(table.find(**{column: shell})):
            table.clone(row['ID'], ids.new(table_name), **{column: variant_id})
    for pack_name in VARIANT_PACKS:
        build.copy_resource(pack_name, shell, variant_id)

    # time of day: most retail levels use a light set that picks day or night at random.
    # A mission that names one gets its own set holding only that light.
    if 'light' in spec:
        light = LIGHTS.get(spec['light'], spec['light'])
        lights = db['AmbientLights']
        if not isinstance(light, int) or light not in lights:
            raise ValueError('%s: light must be one of %s or an AmbientLights ID' % (
                mission_dir, ', '.join(sorted(LIGHTS))))
        db['AmbientLightTemplates'].upsert(ids.single, UserName=tag)
        lights.clone(light, ids.new('AmbientLights'), TemplateID=ids.single, RndWeight=1.0)
        variants.upsert(variant_id, DefaultLight=ids.single)

    # relations between player slots at mission start. Each of the 16 slots holds two bits
    # per other slot: 0 enemy, 1 neutral, 2 ally. Pairs not listed are enemies.
    if 'diplomacy' in spec:
        masks = [0] * 16
        for state, key in ((1, 'neutral'), (2, 'ally')):
            for a, b in spec['diplomacy'].get(key, []):
                masks[a] |= state << (2 * b)
                masks[b] |= state << (2 * a)
        db['Diplomacies'].upsert(ids.single, UserName=tag,
                                 **{'Diplomacy%d' % (i + 1): mask for i, mask in enumerate(masks)})
        variants.upsert(variant_id, DiplomacyID=ids.single)

    # extra level pieces: nested templates (buildings, trees) and single objects
    templates, rects = db['Templates'], db['Rects']
    for piece in spec.get('template', []):
        nested = templates.get(piece['id'])
        if nested is None:
            raise ValueError('%s: [[template]] id %d does not exist' % (mission_dir, piece['id']))
        x, y = piece['pos']
        rects.upsert(ids.new('Rects'), VariantID=variant_id, TemplateLink=piece['id'],
                     CenterX=x, CenterY=y, Width=nested['Width'], Height=nested['Height'],
                     Floor=piece.get('floor', 0), Rotation=piece.get('rotation', 0.0),
                     DeltaZ=piece.get('dz', 0.0), Params='')
    placable, elements = db['PlacableObjects'], db['FinalElements']
    for obj in spec.get('object', []):
        if obj['id'] not in placable:
            raise ValueError('%s: [[object]] id %d does not exist' % (mission_dir, obj['id']))
        x, y = obj['pos']
        elements.upsert(ids.new('FinalElements'), VariantID=variant_id, ModelID=obj['id'],
                        PosX=x, PosY=y, Floor=obj.get('floor', 0), Rotation=obj.get('rotation', 0.0),
                        DeltaZ=obj.get('dz', 0.0), ScaleX=1.0, ScaleY=1.0, ScaleZ=1.0,
                        Lightmap=1, LightShadow=1, APRadius=10, LightParam='Night',
                        Name=obj.get('name', ''))

    # waypoints: optionally the shell's own, then the mission's
    names = db['WaypointNames']
    name_ids = {}
    for row in names.rows():
        name_ids.setdefault(row['UserName'], row['ID'])
    waypoints = db['Waypoints']
    if spec.get('keep_waypoints', True):
        for row in list(waypoints.find(VariantID=shell)):
            new_id = ids.new('Waypoints')
            waypoints.clone(row['ID'], new_id, VariantID=variant_id)
            build.copy_resource('Waypoints', row['ID'], new_id)
    for wp in spec.get('waypoint', []):
        name = wp['name']
        if name not in name_ids:
            name_ids[name] = ids.new('WaypointNames')
            names.upsert(name_ids[name], UserName=name)
        new_id = ids.new('Waypoints')
        waypoints.upsert(new_id, UserName='%s\\%s' % (tag, name), VariantID=variant_id,
                         NameID=name_ids[name])
        x, y = wp['pos']
        build.resources[('Waypoints', new_id)] = waypoint_resource(
            x, y, wp.get('z', 0.0), wp.get('floor', 0), wp.get('rotation', 0))

    # characters: a retail character cloned under a new name, with its starting equipment
    pers = db['RPGPers']
    character_ids = {}
    for character in spec.get('character', []):
        base = character['base']
        if base not in pers:
            raise ValueError('%s: character %r: unknown base RPGPers %d' % (mission_dir, character['name'], base))
        new_id = ids.new('RPGPers')
        character_ids[character['name']] = new_id
        name_string = ids.new('Strings')
        db['Strings'].upsert(name_string, UserName='%s\\%s' % (tag, character['name']),
                             String=character['display_name'])
        pers.clone(base, new_id, UserName='%s\\%s' % (tag, character['name']),
                   DisplayName=name_string, LongNameID=name_string)
        for table_name in EQUIPMENT_TABLES:
            table = db[table_name]
            for row in list(table.find(RPGPersID=base)):
                table.clone(row['ID'], ids.new(table_name), RPGPersID=new_id)

    def pers_id(value, what):
        """An RPGPers ID given as a number, or as the name of one of this mission's characters."""
        if isinstance(value, str):
            if value not in character_ids:
                raise ValueError('%s: %s: no [[character]] named %r' % (mission_dir, what, value))
            return character_ids[value]
        if value not in pers:
            raise ValueError('%s: %s: unknown RPGPers %d' % (mission_dir, what, value))
        return value

    # units
    groups = db['UnitGroups']
    group_ids = {}
    units = db['Units']
    if spec.get('keep_units', False):
        for row in list(units.find(VariantID=shell)):
            new_id = ids.new('Units')
            units.clone(row['ID'], new_id, VariantID=variant_id)
            build.copy_resource('Units', row['ID'], new_id)
    for unit in spec.get('unit', []):
        who = pers_id(unit['pers'], 'unit %r' % unit.get('name'))
        pose = unit.get('pose', 'Stand')
        if pose not in POSES:
            raise ValueError('%s: pose must be one of %s' % (mission_dir, ', '.join(POSES)))
        group = 0
        if 'group' in unit:
            if unit['group'] not in group_ids:
                group_ids[unit['group']] = ids.new('UnitGroups')
                groups.upsert(group_ids[unit['group']], UserName=unit['group'], Formation='')
            group = group_ids[unit['group']]
        x, y = unit['pos']
        unit_id = ids.new('Units')
        units.upsert(unit_id, VariantID=variant_id, MonsterID=who,
                     PosX=x, PosY=y, Floor=unit.get('floor', 0), Rotation=unit.get('rotation', 0.0),
                     Player=unit.get('player', 1), Diplomacy=-1, Group=group,
                     RelativeLevel=unit.get('level', 0),
                     Name=unit.get('name', ''), Pose=pose, Logic=unit.get('logic', 'Sentry'),
                     RoamingRadius=unit.get('roaming_radius', 0))
        if 'route' in unit:
            missing = [name for name in unit['route'] if name not in name_ids]
            if missing:
                raise ValueError('%s: unit %r route uses unknown waypoints %s' % (
                    mission_dir, unit.get('name'), ', '.join(missing)))
            build.resources[('Units', unit_id)] = route_resource([name_ids[name] for name in unit['route']])

    # cameras: anchor is the point looked at (tiles, z up), angles in radians
    cameras = db['Cameras']
    camera_ids = {}
    for cam in spec.get('camera', []):
        camera_ids[cam['name']] = ids.new('Cameras')
        x, y, z = cam['anchor']
        cameras.upsert(camera_ids[cam['name']], UserName='%s\\%s' % (tag, cam['name']),
                       AnchorX=x, AnchorY=y, AnchorZ=z, Yaw=cam.get('yaw', -0.8),
                       Pitch=cam.get('pitch', -0.7), Roll=0.0,
                       Distance=cam.get('distance', 20.0), FOV=cam.get('fov', 35.0))

    # dialogues: text-only lines shown on the engine's letterbox dialogue screen
    dialogue_codes = {}
    for dialogue in spec.get('dialogue', []):
        code = 'SS2_%s_%s' % (spec['name'], dialogue['name'])
        dialogue_codes[dialogue['name']] = code
        dialog_id = ids.new('Dialogs')
        db['Dialogs'].upsert(dialog_id, Code=code, UserName=code)
        for n, line in enumerate(dialogue['line'], 1):
            text = line['text']
            who = pers_id(line['who'], 'dialogue %r line %d' % (dialogue['name'], n))
            if '\n' in text or not all(c in DIALOGUE_CHARS for c in text):
                raise ValueError('%s: dialogue %r line %d: use <br> for line breaks and only '
                                 'characters the retail fonts have' % (mission_dir, dialogue['name'], n))
            label = '%s\\%s.%d' % (tag, dialogue['name'], n)
            string_id = ids.new('Strings')
            db['Strings'].upsert(string_id, UserName=label, String=text)
            ack_id = ids.new('AckInfos')
            db['AckInfos'].upsert(ack_id, UserName=label, WhoID=who, StringID=string_id)
            db['DialogSeqs'].upsert(ids.new('DialogSeqs'), DialogID=dialog_id, AckInfoID=ack_id)

    # The script the engine gets: generated constants (scripts fetch groups and cameras by ID),
    # the shared helpers, the mission script and, in a test build, the mission's test.lua, which
    # plays the mission through by script and logs TEST PASS or TEST FAIL.
    script_name = spec.get('script', 'script.lua')
    test_path = os.path.join(mission_dir, 'test.lua')
    has_test = build.test and os.path.exists(test_path)
    header = ''.join('SS2_GROUP_%s = %d\n' % item for item in sorted(group_ids.items()))
    header += ''.join('SS2_CAMERA_%s = %d\n' % item for item in sorted(camera_ids.items()))
    header += ''.join('SS2_DIALOG_%s = "%s"\n' % item for item in sorted(dialogue_codes.items()))
    header += ''.join('SS2_PERS_%s = %d\n' % item for item in sorted(character_ids.items()))
    header += 'SS2_TEST = %s\n' % ('1' if has_test else 'nil')
    header += 'SS2_SKIP_DIALOGUE = %s\n' % ('1' if has_test or build.skip_dialogue else 'nil')
    parts = [('generated constants', header), ('game/scripts/common.lua', build.common_script)]
    for name in (script_name, 'test.lua') if has_test else (script_name,):
        with open(os.path.join(mission_dir, name), encoding='utf-8') as f:
            parts.append((name, f.read().replace('\r\n', '\n').rstrip('\n') + '\n'))
    source = ''.join(text for _, text in parts)

    problems = lualint.lint(source)
    if problems:
        lines = []
        for line, message in problems:
            first = 1
            for name, text in parts:        # which file the combined line number falls in
                count = text.count('\n')
                if line < first + count:
                    lines.append('  %s line %d: %s' % (name, line - first + 1, message))
                    break
                first += count
        raise ValueError('%s: script problems\n%s' % (mission_dir, '\n'.join(lines)))

    db['Scripts'].upsert(ids.single, UserName=tag, CodeText=source)
    return {'name': spec['name'], 'slot': slot, 'variant': variant_id, 'has_test': has_test,
            'party': spec.get('party', [])}


def compile_all(build, game_dir):
    """Compile every mission under game/missions, in folder-name order.

    game/scripts/common.lua, if present, is put in front of every mission script.
    """
    common = os.path.join(game_dir, 'scripts', 'common.lua')
    if os.path.exists(common):
        with open(common, encoding='utf-8') as f:
            build.common_script = f.read().replace('\r\n', '\n') + '\n'
    root = os.path.join(game_dir, 'missions')
    dirs = [os.path.join(root, d) for d in sorted(os.listdir(root))
            if os.path.exists(os.path.join(root, d, 'mission.toml'))]
    return [compile_mission(build, d) for d in dirs]
