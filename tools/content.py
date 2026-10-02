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

# Player slots as the engine numbers them: 0 is the human player.
POSES = ('Stand', 'Crouch', 'Crawl')


class Build:
    """One content build: the database being edited plus loose-resource output."""

    def __init__(self, db, run_dir):
        self.db = db
        self.run_dir = run_dir
        self._packs = {}
        self.resources = {}     # (pack name, file id) -> bytes

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

    # units
    groups = db['UnitGroups']
    group_ids = {}
    units = db['Units']
    pers = db['RPGPers']
    if spec.get('keep_units', False):
        for row in list(units.find(VariantID=shell)):
            new_id = ids.new('Units')
            units.clone(row['ID'], new_id, VariantID=variant_id)
            build.copy_resource('Units', row['ID'], new_id)
    for unit in spec.get('unit', []):
        if unit['pers'] not in pers:
            raise ValueError('%s: unit %r uses unknown RPGPers %d' % (mission_dir, unit.get('name'), unit['pers']))
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
        units.upsert(ids.new('Units'), VariantID=variant_id, MonsterID=unit['pers'],
                     PosX=x, PosY=y, Floor=unit.get('floor', 0), Rotation=unit.get('rotation', 0.0),
                     Player=unit.get('player', 1), Diplomacy=-1, Group=group,
                     Name=unit.get('name', ''), Pose=pose, Logic=unit.get('logic', 'Sentry'),
                     RoamingRadius=unit.get('roaming_radius', 0))

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

    # script, with the IDs it needs prepended as globals (scripts fetch groups and cameras by ID)
    with open(os.path.join(mission_dir, spec.get('script', 'script.lua')), encoding='utf-8') as f:
        code = f.read().replace('\r\n', '\n')
    header = ''.join('SS2_GROUP_%s = %d\n' % item for item in sorted(group_ids.items()))
    header += ''.join('SS2_CAMERA_%s = %d\n' % item for item in sorted(camera_ids.items()))
    db['Scripts'].upsert(ids.single, UserName=tag, CodeText=header + code)
    return {'name': spec['name'], 'slot': slot, 'variant': variant_id}


def compile_all(build, game_dir):
    """Compile every mission under game/missions, in slot order."""
    root = os.path.join(game_dir, 'missions')
    dirs = [os.path.join(root, d) for d in sorted(os.listdir(root))
            if os.path.exists(os.path.join(root, d, 'mission.toml'))]
    return [compile_mission(build, d) for d in dirs]
