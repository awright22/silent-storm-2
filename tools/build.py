"""Build Silent Storm 2: stage the run root, then compile game/ into it.

    python tools/build.py

Starts from the pristine retail game.db copy every time, applies the engine
port's UI patches (retail data lacks a few controls the engine source expects),
then adds SS2 content. Output: <run>/game.db plus loose resource folders.
"""
import glob
import os
import shutil
import subprocess
import sys

import config
import content
import stage
from ssdb import Database


def build():
    paths = config.load()
    run = paths['run']
    copied = stage.stage(paths)
    print('stage: %d files copied' % copied)

    db_path = os.path.join(run, 'game.db')
    shutil.copyfile(os.path.join(run, 'game.db.retail'), db_path)
    for patch in sorted(glob.glob(os.path.join(paths['engine'], 'tools', 'dbpatch_*.py'))):
        subprocess.run([sys.executable, patch, db_path], check=True, capture_output=True)
        print('engine patch: %s' % os.path.basename(patch))

    db = Database.load(db_path)
    b = content.Build(db, run)
    for mission in content.compile_all(b, config.GAME):
        print('mission: %(name)s -> map %(variant)d' % mission)
    db.save(db_path)
    b.write_resources()
    print('built %s (%d loose resources)' % (db_path, len(b.resources)))


if __name__ == '__main__':
    build()
