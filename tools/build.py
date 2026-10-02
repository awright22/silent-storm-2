"""Build Silent Storm 2: stage the run root, then compile game/ into it.

    python tools/build.py [--test] [--skip-dialogue] [--extra DIR ...]

--test compiles each mission's test.lua into its script (a scripted
playthrough; see tools/test_missions.py). Do not play a test build.
--skip-dialogue makes dialogues log a line instead of opening, so an
unattended run gets past them.
--extra adds another content folder (laid out like game/) to this build only,
for scratch missions that should not live in the repository.

Starts from the pristine retail game.db copy every time, applies the engine
port's UI patches (retail data lacks a few controls the engine source expects),
then adds SS2 content. Output: <run>/game.db plus loose resource folders.
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys

import config
import content
import stage
from ssdb import Database


FAILED_MARKER = 'BUILD_FAILED'     # present in the run root while a build is unfinished or failed


def patched_retail_db(paths, db_path):
    """Write a fresh copy of the retail database with the engine port's patches applied."""
    shutil.copyfile(os.path.join(paths['run'], 'game.db.retail'), db_path)
    patches = sorted(glob.glob(os.path.join(paths['engine'], 'tools', 'dbpatch_*.py')))
    for patch in patches:
        subprocess.run([sys.executable, patch, db_path], check=True, capture_output=True)
    return [os.path.basename(p) for p in patches]


def build(extra=(), test=False, skip_dialogue=False):
    """Build the run root. Returns the compiled missions' summaries."""
    paths = config.load()
    run = paths['run']
    copied = stage.stage(paths)
    print('stage: %d files copied' % copied)

    # Build into a work file and swap it in only when everything compiled. Until then the
    # FAILED marker stands, so nothing runs the game on a half-built or stale database.
    db_path = os.path.join(run, 'game.db')
    work_path = db_path + '.work'
    failed = os.path.join(run, FAILED_MARKER)
    with open(failed, 'w') as f:
        f.write('the last build did not finish\n')
    for name in patched_retail_db(paths, work_path):
        print('engine patch: %s' % name)

    db = Database.load(work_path)
    b = content.Build(db, run)
    b.test = test
    b.skip_dialogue = skip_dialogue
    missions = []
    for game_dir in (config.GAME,) + tuple(extra):
        for mission in content.compile_all(b, game_dir):
            print('mission: %(name)s -> map %(variant)d' % mission)
            missions.append(mission)
    for warning in b.warnings:
        print('warning: %s' % warning)
    db.save(work_path)
    os.replace(work_path, db_path)
    b.write_resources()
    os.remove(failed)
    note = '  [TEST BUILD]' if test else '  [dialogues skipped]' if skip_dialogue else ''
    print('built %s (%d loose resources)%s' % (db_path, len(b.resources), note))
    return missions


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--test', action='store_true', help='compile mission test scripts in')
    parser.add_argument('--skip-dialogue', action='store_true',
                        help='log dialogues instead of showing them, for unattended screenshots')
    parser.add_argument('--extra', action='append', default=[], metavar='DIR',
                        help='additional content folder for this build only')
    args = parser.parse_args()
    try:
        build(args.extra, args.test, args.skip_dialogue)
    except ValueError as problem:       # a mistake in the content sources, already described
        sys.exit('build failed: %s' % problem)
