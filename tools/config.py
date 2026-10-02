"""Paths for the SS2 build, read from ss2.local.toml at the repo root.

    [paths]
    retail = "D:/SteamLibrary/steamapps/common/Silent Storm"   # owned game install, read-only
    engine = "D:/Code/Silent-Storm/port"                       # ported engine checkout
    run    = "build/run"                                       # staged run root (optional)
"""
import os
import sys
import tomllib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(REPO, 'game')


def load():
    path = os.path.join(REPO, 'ss2.local.toml')
    if not os.path.exists(path):
        sys.exit('ss2.local.toml not found - copy ss2.local.example.toml and set your paths')
    with open(path, 'rb') as f:
        paths = tomllib.load(f)['paths']
    paths.setdefault('run', 'build/run')
    paths['run'] = os.path.join(REPO, paths['run'])
    for key in ('retail', 'engine'):
        if not os.path.isdir(paths[key]):
            sys.exit('ss2.local.toml: paths.%s is not a directory: %s' % (key, paths[key]))
    return paths
