"""Build Silent Storm 2: stage the run root, then compile game/ into it.

    python tools/build.py [--extra DIR ...]

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


def patched_retail_db(paths, db_path):
    """Write a fresh copy of the retail database with the engine port's patches applied."""
    shutil.copyfile(os.path.join(paths['run'], 'game.db.retail'), db_path)
    patches = sorted(glob.glob(os.path.join(paths['engine'], 'tools', 'dbpatch_*.py')))
    for patch in patches:
        subprocess.run([sys.executable, patch, db_path], check=True, capture_output=True)
    return [os.path.basename(p) for p in patches]


def build(extra=()):
    paths = config.load()
    run = paths['run']
    copied = stage.stage(paths)
    print('stage: %d files copied' % copied)

    db_path = os.path.join(run, 'game.db')
    for name in patched_retail_db(paths, db_path):
        print('engine patch: %s' % name)

    db = Database.load(db_path)
    b = content.Build(db, run)
    for game_dir in (config.GAME,) + tuple(extra):
        for mission in content.compile_all(b, game_dir):
            print('mission: %(name)s -> map %(variant)d' % mission)
    db.save(db_path)
    b.write_resources()
    print('built %s (%d loose resources)' % (db_path, len(b.resources)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--extra', action='append', default=[], metavar='DIR',
                        help='additional content folder for this build only')
    build(parser.parse_args().extra)
