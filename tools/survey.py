"""Survey retail levels: which ones load on the ported engine, and what they look like.

    python tools/survey.py [--limit N] [--retry]

Every retail campaign zone and every level template marked "Complete" is
compiled as an empty SS2 mission (level geometry only, overview camera) into
its own run root, build/survey, then launched one at a time. For each level
the result (loaded / timeout / crashed, load time) goes to
build/survey/results.json and an overview screenshot to build/survey/shots/.
The run is resumable: levels already in results.json are skipped unless
--retry is given.

The survey uses its own exe name (SS2Survey.exe) and no debug-output
listener, so it can run while tools/run.py is used for other tests.
"""
import argparse
import json
import os
import shutil
import subprocess
import time

import build
import config
import content
import run as game_run
from ssdb import Database

EXE = 'SS2Survey.exe'
LOAD_TIMEOUT = 600
SETTLE = 8          # seconds between the mission UI appearing and the screenshot


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


def prepare(paths, survey_dir, levels):
    """Stage the survey run root and compile one empty mission per level. Returns {variant: map id}."""
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
        folder = os.path.join(missions, 's%04d' % slot)
        os.makedirs(folder)
        with open(os.path.join(folder, 'mission.toml'), 'w', encoding='utf-8') as f:
            f.write('slot = %d\nname = "survey_%d"\nshell = %d\n\n[[camera]]\nname = "overview"\n'
                    'anchor = [%.1f, %.1f, 0.0]\nyaw = -0.8\npitch = -1.3\ndistance = 62.0\n'
                    % (slot, variant, variant, template['Width'] / 2, template['Height'] / 2))
        with open(os.path.join(folder, 'script.lua'), 'w', encoding='utf-8') as f:
            f.write('CameraSet( GetCamera( SS2_CAMERA_overview ) )\n')

    db_path = os.path.join(survey_dir, 'game.db')
    build.patched_retail_db(paths, db_path)
    db = Database.load(db_path)
    b = content.Build(db, survey_dir)
    compiled = content.compile_all(b, os.path.join(survey_dir, 'game'))
    db.save(db_path)
    b.write_resources()
    return {variant: mission['variant'] for (variant, _, _), mission in zip(levels, compiled)}


def mission_ui_visible(hwnd):
    """True once the mission interface is drawn: the bottom panel is no longer black."""
    w, h, bgra = game_run.grab(hwnd)
    if not w:
        return False
    total = count = 0
    for y in range(int(h * 0.92), int(h * 0.98), 4):
        row = bgra[y * w * 4:(y + 1) * w * 4]
        for channel in (0, 1, 2):
            samples = row[channel::16]
            total += sum(samples)
            count += len(samples)
    return total / count > 12


def exit_info(proc, seconds):
    return {'status': 'crashed', 'exit_code': '0x%X' % (proc.returncode & 0xFFFFFFFF), 'seconds': seconds}


def survey_one(survey_dir, map_id, png_path):
    game = [os.path.join(survey_dir, EXE), '-1024'] + game_run.write_boot_cfg(survey_dir, 'map %d' % map_id)
    proc = game_run.launch_quiet(game, survey_dir)
    start = time.time()
    in_back = False
    try:
        while time.time() - start < LOAD_TIMEOUT:
            time.sleep(2)
            if proc.poll() is not None:
                return exit_info(proc, round(time.time() - start))
            hwnd = game_run.find_window(EXE)
            if not hwnd:
                continue
            if not in_back:
                game_run.send_to_back(hwnd)
                in_back = True
            if mission_ui_visible(hwnd):
                loaded = round(time.time() - start)
                time.sleep(SETTLE)
                if proc.poll() is not None:
                    return exit_info(proc, loaded)
                game_run.capture(hwnd, png_path)
                return {'status': 'loaded', 'seconds': loaded}
        return {'status': 'timeout'}
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(10)


def write_report(results, path):
    """docs/locations.md: every surveyed level, smallest first."""
    rows = sorted(results.items(), key=lambda kv: (kv[1]['width'] * kv[1]['height'], int(kv[0])))
    loaded = sum(1 for _, r in rows if r['status'] == 'loaded')
    lines = [
        '# Retail levels usable as mission locations', '',
        'Generated by `python tools/survey.py --report` from the last survey run. Each level was',
        'compiled as an empty SS2 mission (geometry only) and launched on the ported engine.',
        '"Shell" is the variant ID to put in `mission.toml`. Load time is seconds from launch to',
        'the mission interface on the survey machine. Overview screenshots are in',
        '`build/survey/shots/<shell>.png` after a survey run.', '',
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
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--limit', type=int, default=0, help='stop after this many levels')
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
        write_report(results, os.path.join(config.REPO, 'docs', 'locations.md'))
        return

    levels = candidates(Database.load(os.path.join(paths['run'], 'game.db.retail')))
    print('%d levels; preparing run root...' % len(levels), flush=True)
    map_ids = prepare(paths, survey_dir, levels)

    done = 0
    for variant, label, template in levels:
        key = str(variant)
        if key in results and (results[key]['status'] == 'loaded' or not args.retry):
            continue
        result = survey_one(survey_dir, map_ids[variant], os.path.join(shots, '%d.png' % variant))
        result.update(name=template['UserName'], kind=label, width=template['Width'], height=template['Height'])
        results[key] = result
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=1, sort_keys=True)
        print('%5d %-34s %3dx%-3d %s %ss' % (variant, template['UserName'][:34], template['Width'],
                                             template['Height'], result['status'], result.get('seconds', '-')),
              flush=True)
        done += 1
        if args.limit and done >= args.limit:
            break


if __name__ == '__main__':
    main()
