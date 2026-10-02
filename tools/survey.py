"""Survey retail levels: which ones load on the ported engine, and what they look like.

    python tools/survey.py [--limit N] [--only ID ...] [--retry] [--report]

Every retail campaign zone and every level template marked "Complete" is
compiled as an SS2 mission that adds nothing to it (level geometry only,
daylight, one camera) into its own run root, build/survey, then launched one
at a time. For each level:

  build/survey/results.json            loaded / timeout / crashed, load time
  build/survey/shots/<id>_roofs.png    the whole level from above, roofs on
  build/survey/shots/<id>_ground.png   the same view cut at the ground floor,
                                       so rooms can be seen
  build/survey/shots/<id>.log          the engine's log for that run

The camera looks almost straight down at the level's centre from far enough to
hold all four corners in the 3D view, with the level's long side across the
screen. The engine normally caps script cameras at a distance too short for
that, so the survey raises the cap with the mission_camera_limits console
command.

The run is resumable: levels that already have both screenshots are skipped.
--retry reruns levels that did not load. --only limits the run to the given
shell IDs. --report writes docs/locations.md from the saved results without
running anything. Every screenshot gets a claim file for its reviewer
(docs/screenshot-review.md).

The survey uses its own run root and exe name (SS2Survey.exe), so it can run
while tools/run.py is used for other tests.
"""
import argparse
import json
import os
import shutil
import subprocess

import build
import config
import content
import reviews
import run as game_run
from ssdb import Database

EXE = 'SS2Survey.exe'
LOAD_TIMEOUT = 600
ROOFS_AT, GROUND_AT = 10, 17    # seconds after mission start; units take several seconds to appear
CAMERA_LIMITS = 'mission_camera_limits 35 10 2000 -1.5 -0.3'
PITCH = -1.35
# Camera distance in tiles needed per tile of level: across the screen, and up the screen.
# Measured on the 48x32 farm at distance 110: 15.1 px per tile across, 14.3 up, in a 1024x564 view.
FIT_ACROSS, FIT_UP = 1.95, 3.3


def candidates(db):
    """[(variant id, label, template row)] for campaign zones and 'Complete' templates, smallest first."""
    templates, variants = db['Templates'], db['TemplVariants']
    found = {}
    for zone in db['ScenarioZones'].rows():
        for column in ('TemplateID1', 'TemplateID2', 'TemplateID3'):
            template = templates.get(zone[column]) if zone[column] > 0 else None
            if template:
                for variant in variants.find(TemplateID=template['ID']):
                    found[variant['ID']] = ('zone ' + zone['UserName'], template)
    for template in templates.rows():
        if 'omplete' in template['UserName']:
            for variant in variants.find(TemplateID=template['ID']):
                found.setdefault(variant['ID'], ('level', template))
    rows = [(vid, label, template) for vid, (label, template) in found.items()]
    return sorted(rows, key=lambda r: (r[2]['Width'] * r[2]['Height'], r[0]))


def overview_camera(width, height):
    """(yaw, distance in tiles) that frames a width x height level, long side across the screen.

    At yaw 0 the level's +x runs to the right of the screen and +y up it; at
    yaw pi/2, +x runs down the screen and +y to the right (both measured from
    reviewed calibration screenshots).
    """
    yaw = 0.0 if width >= height else 1.5708
    across, up = max(width, height), min(width, height)
    return yaw, max(FIT_ACROSS * across, FIT_UP * up)


def prepare(paths, survey_dir, levels):
    """Stage the survey run root and compile one mission per level. Returns {variant: map id}."""
    run_dir = paths['run']
    os.makedirs(survey_dir, exist_ok=True)
    res_link = os.path.join(survey_dir, 'res')
    if not os.path.exists(res_link):
        subprocess.run(['cmd', '/c', 'mklink', '/J', os.path.normpath(res_link),
                        os.path.normpath(os.path.join(run_dir, 'res'))], check=True, capture_output=True)
    for name in ('cfg', 'scripts'):
        shutil.copytree(os.path.join(run_dir, name), os.path.join(survey_dir, name), dirs_exist_ok=True)
    shutil.copy2(os.path.join(run_dir, 'start.cfg'), survey_dir)
    shutil.copy2(os.path.join(run_dir, 'SS2.exe'), os.path.join(survey_dir, EXE))
    shutil.copy2(os.path.join(run_dir, 'Game.pdb'), survey_dir)

    missions = os.path.join(survey_dir, 'game', 'missions')
    shutil.rmtree(missions, ignore_errors=True)
    for slot, (variant, label, template) in enumerate(levels, 1):
        yaw, distance = overview_camera(template['Width'], template['Height'])
        folder = os.path.join(missions, 's%04d' % slot)
        os.makedirs(folder)
        with open(os.path.join(folder, 'mission.toml'), 'w', encoding='utf-8') as f:
            f.write('slot = %d\nname = "survey_%d"\nshell = %d\nlight = "day"\n\n[[camera]]\nname = "overview"\n'
                    'anchor = [%.1f, %.1f]\nyaw = %s\npitch = %s\ndistance = %.1f\n'
                    % (slot, variant, variant, template['Width'] / 2, template['Height'] / 2, yaw, PITCH, distance))
        with open(os.path.join(folder, 'script.lua'), 'w', encoding='utf-8') as f:
            # roofs on for the first shot, then cut the view at the ground floor for the second
            f.write('CameraSet( GetCamera( SS2_CAMERA_overview ) )\nFloor( 4 )\nSleep( %d )\nFloor( 0 )\n'
                    % ((ROOFS_AT + 2) * 20))

    db_path = os.path.join(survey_dir, 'game.db')
    build.patched_retail_db(paths, db_path)
    db = Database.load(db_path)
    b = content.Build(db, survey_dir)
    compiled = content.compile_all(b, os.path.join(survey_dir, 'game'))
    db.save(db_path)
    b.write_resources()
    return {variant: mission['variant'] for (variant, _, _), mission in zip(levels, compiled)}


def shot_paths(shots, variant):
    return os.path.join(shots, '%s_roofs.png' % variant), os.path.join(shots, '%s_ground.png' % variant)


def survey_one(survey_dir, map_id, variant):
    """Load one level and take its two overview shots. Returns the result record."""
    shots = os.path.join(survey_dir, 'shots')
    result = game_run.run_game(survey_dir, EXE, 'map %d' % map_id, os.path.join(shots, '%d.log' % variant),
                               shots=[ROOFS_AT, GROUND_AT], shot_base=os.path.join(shots, str(variant)),
                               load_timeout=LOAD_TIMEOUT, before=(CAMERA_LIMITS,))
    for at, final in zip((ROOFS_AT, GROUND_AT), shot_paths(shots, variant)):
        png = os.path.join(shots, '%d_%02d.png' % (variant, at))
        if os.path.exists(png):
            os.replace(png, final)
    if result.crashed:
        return {'status': 'crashed'}
    if result.started is None:
        if result.exit_code is not None:
            return {'status': 'crashed', 'exit_code': '0x%X' % result.exit_code}
        return {'status': 'timeout'}
    return {'status': 'loaded', 'seconds': round(result.started)}


def write_claims(results, shots):
    """Give every survey screenshot the claim its reviewer checks it against."""
    common = ('All four corners of the level are inside the 3D view and its edges run parallel to the screen '
              'edges. Daylight. No mouse cursor. Any figures are the default three-person party or soldiers the '
              'level itself contains. (Survey label: "%s", %dx%d tiles.)')
    for variant, r in results.items():
        label = common % (r['name'], r['width'], r['height'])
        roofs, ground = shot_paths(shots, variant)
        if os.path.exists(roofs):
            reviews.write_claim(roofs, 'One whole game level seen from almost straight above. Buildings, if '
                                       'any, have their roofs on. ' + label)
        if os.path.exists(ground):
            reviews.write_claim(ground, 'One whole game level seen from almost straight above, with the view '
                                        'cut at ground-floor height: buildings, if any, are open from above so '
                                        'their ground-floor rooms can be seen. ' + label)


def write_report(results, path):
    """docs/locations.md: every surveyed level, smallest first."""
    rows = sorted(results.items(), key=lambda kv: (kv[1]['width'] * kv[1]['height'], int(kv[0])))
    loaded = sum(1 for _, r in rows if r['status'] == 'loaded')
    lines = [
        '# Retail levels usable as mission locations', '',
        'Generated by `python tools/survey.py --report` from the last survey run. Each level was',
        'compiled as an SS2 mission that adds nothing to it and launched on the ported engine.',
        '"Shell" is the variant ID to put in `mission.toml`. Load time is seconds from launch to',
        'mission start on the survey machine. After a survey run the overview screenshots are',
        '`build/survey/shots/<shell>_roofs.png` and `<shell>_ground.png`.', '',
        'A level can contain soldiers of its own (through its nested templates), which a mission',
        'built on it inherits.', '',
        '%d of %d surveyed levels load.' % (loaded, len(rows)), '',
        '| Shell | Name | Size (tiles) | Source | Result | Load (s) |',
        '|---|---|---|---|---|---|',
    ]
    for variant, r in rows:
        lines.append('| %s | %s | %dx%d | %s | %s | %s |' % (
            variant, r['name'].replace('|', '/'), r['width'], r['height'], r['kind'], r['status'],
            r.get('seconds', '')))
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--limit', type=int, default=0, help='stop after this many levels')
    parser.add_argument('--only', type=int, nargs='+', default=[], metavar='ID', help='survey only these shells')
    parser.add_argument('--retry', action='store_true', help='rerun levels that did not load last time')
    parser.add_argument('--report', action='store_true', help='only write docs/locations.md from saved results')
    args = parser.parse_args()

    paths = config.load()
    survey_dir = os.path.join(config.REPO, 'build', 'survey')
    shots = os.path.join(survey_dir, 'shots')
    os.makedirs(shots, exist_ok=True)
    results_path = os.path.join(survey_dir, 'results.json')
    results = {}
    if os.path.exists(results_path):
        with open(results_path, encoding='utf-8') as f:
            results = json.load(f)
    if args.report:
        write_claims(results, shots)
        write_report(results, os.path.join(config.REPO, 'docs', 'locations.md'))
        return

    levels = candidates(Database.load(os.path.join(paths['run'], 'game.db.retail')))
    print('%d levels; preparing run root...' % len(levels), flush=True)
    map_ids = prepare(paths, survey_dir, levels)

    done = 0
    for variant, label, template in levels:
        key = str(variant)
        if args.only and variant not in args.only:
            continue
        previous = results.get(key)
        if previous and not args.only:
            if previous['status'] != 'loaded' and not args.retry:
                continue
            if previous['status'] == 'loaded' and all(os.path.exists(p) for p in shot_paths(shots, variant)):
                continue
        result = survey_one(survey_dir, map_ids[variant], variant)
        result.update(name=template['UserName'], kind=label, width=template['Width'], height=template['Height'])
        results[key] = result
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=1, sort_keys=True)
        write_claims({key: result}, shots)
        print('%5d %-34s %3dx%-3d %s %ss' % (variant, template['UserName'][:34], template['Width'],
                                             template['Height'], result['status'], result.get('seconds', '-')),
              flush=True)
        done += 1
        if args.limit and done >= args.limit:
            break


if __name__ == '__main__':
    main()
