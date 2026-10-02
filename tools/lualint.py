"""Check a mission script for mistakes this engine does not report.

    python tools/lualint.py <script.lua> [more.lua ...]    lint files as one script
    python tools/lualint.py --update                       refresh tools/lua_names.json

The engine's Lua 4.0 fails silently in two ways that a mission author cannot
see in the game:

  * A call to a name that does not exist does nothing. A typo is not an error.
  * Many functions the retail scripts call exist only as do-nothing
    placeholders in this engine build.

So every global a script reads must be an engine function that is really
implemented, a helper or constant from the retail script library, or a global
the script itself assigns somewhere. Anything else is reported.

tools/lua_names.json holds the known engine and library names. Refresh it with
--update after the engine port's script API changes; that reads the engine
source (ScriptFunctions.cpp, lua_compat.cpp) and the staged retail scripts
(build/run/scripts/*.l).
"""
import json
import os
import re
import sys

KEYWORDS = {
    'and', 'break', 'do', 'else', 'elseif', 'end', 'for', 'function', 'if', 'in', 'local',
    'nil', 'not', 'or', 'repeat', 'return', 'then', 'until', 'while',
}
NAMES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lua_names.json')

_TOKEN = re.compile(r'''
    (?P<comment>--[^\n]*)
  | (?P<string>"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|\[\[.*?\]\])
  | (?P<number>\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+)
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>\.\.\.|\.\.|==|~=|<=|>=|[-+*/^%<>=(){}\[\];:,.])
  | (?P<space>\s+)
''', re.VERBOSE | re.DOTALL)


def tokenize(source):
    """[(kind, text, line)] without comments and whitespace."""
    tokens = []
    pos, line = 0, 1
    while pos < len(source):
        match = _TOKEN.match(source, pos)
        if not match:
            raise SyntaxError('line %d: cannot read %r' % (line, source[pos:pos + 20]))
        kind = match.lastgroup
        text = match.group()
        if kind not in ('comment', 'space'):
            tokens.append((kind, text, line))
        line += text.count('\n')
        pos = match.end()
    return tokens


def analyse(source):
    """Globals a script defines and reads.

    Returns (top_defs, inner_defs, reads):
      top_defs    {name: token index of its first chunk-level definition}
      inner_defs  {name} assigned only inside functions or blocks
      reads       [(name, line, token index, block depth)], depth 0 = chunk level
    """
    tokens = tokenize(source)
    text_at = lambda k: tokens[k][1] if 0 <= k < len(tokens) else ''
    scopes = [set()]            # local names per open block; scopes[0] is the chunk
    brace = paren = 0
    pending_for = None          # loop variables waiting for their "do"
    top_defs, inner_defs, reads = {}, set(), []

    def is_local(name):
        return any(name in scope for scope in scopes)

    def define(name, index):
        if len(scopes) == 1:
            top_defs.setdefault(name, index)
        else:
            inner_defs.add(name)

    def read(index):
        reads.append((tokens[index][1], tokens[index][2], index, len(scopes) - 1))

    i = 0
    while i < len(tokens):
        kind, text, line = tokens[i]
        prev, nxt = text_at(i - 1), text_at(i + 1)

        if kind == 'op':
            if text == '{':
                brace += 1
            elif text == '}':
                brace -= 1
            elif text == '(':
                paren += 1
            elif text == ')':
                paren -= 1
        elif kind == 'name' and text in KEYWORDS:
            if text == 'function':
                j = i + 1
                if tokens[j][0] == 'name' and tokens[j][1] not in KEYWORDS:
                    if text_at(j + 1) == '(' and not is_local(tokens[j][1]):
                        define(tokens[j][1], j)         # "function Name(" defines a global
                    elif text_at(j + 1) in ('.', ':'):
                        read(j)                         # "function t.f(" reads t
                    while text_at(j) != '(':
                        j += 1
                params = set()
                j += 1
                while text_at(j) != ')':
                    if tokens[j][0] == 'name':
                        params.add(tokens[j][1])
                    j += 1
                scopes.append(params)
                i = j + 1
                continue
            if text == 'for':
                names = set()
                j = i + 1
                while text_at(j) not in ('=', 'in'):
                    if tokens[j][0] == 'name':
                        names.add(tokens[j][1])
                    j += 1
                pending_for = names
                i = j + 1
                continue
            if text == 'do':
                scopes.append(pending_for or set())
                pending_for = None
            elif text in ('if', 'repeat'):
                scopes.append(set())
            elif text in ('end', 'until'):
                if len(scopes) == 1:
                    raise SyntaxError('line %d: "%s" without an open block' % (line, text))
                scopes.pop()
            elif text == 'local':
                j = i + 1
                names = []
                while tokens[j][0] == 'name' and tokens[j][1] not in KEYWORDS:
                    names.append(tokens[j][1])
                    if text_at(j + 1) != ',':
                        break
                    j += 2
                # "local x = x" reads the outer x before the new local exists
                if text_at(j + 1) == '=' and tokens[j + 2][0] == 'name' and text_at(j + 2) in names:
                    if not is_local(text_at(j + 2)):
                        read(j + 2)
                    scopes[-1].update(names)
                    i = j + 3
                    continue
                scopes[-1].update(names)
                i = j + 1
                continue
        elif kind == 'name':
            if prev in ('.', ':', '%'):
                pass                                    # field, method or upvalue
            elif brace and nxt == '=':
                pass                                    # table constructor key
            elif is_local(text):
                pass
            elif nxt == '=' and not paren:
                define(text, i)                         # global assignment
            elif nxt == ',' and not paren and not brace and _is_assignment_list(tokens, i):
                define(text, i)
            else:
                read(i)
        i += 1

    if len(scopes) != 1:
        raise SyntaxError('%d block(s) not closed with "end"' % (len(scopes) - 1))
    return top_defs, inner_defs - set(top_defs), reads


def _is_assignment_list(tokens, i):
    """True for the first names of "a, b = ..." at statement level."""
    if i and tokens[i - 1][1] in (',', '(', '=', 'return', 'in'):
        return False
    j = i
    while tokens[j][0] == 'name' and tokens[j + 1][1] == ',':
        j += 2
    return tokens[j][0] == 'name' and tokens[j + 1][1] == '='


def load_names():
    with open(NAMES_FILE, encoding='utf-8') as f:
        return json.load(f)


def lint(source, names=None):
    """Problems found in a complete mission script, as [(line, message)]."""
    names = names or load_names()
    engine, noop, library = set(names['engine']), set(names['noop']), set(names['library'])
    top_defs, inner_defs, reads = analyse(source)
    problems = []
    reported = set()
    for name, line, index, depth in reads:
        if name in top_defs:
            # a chunk-level statement runs in file order, so it cannot use a function defined further down
            if depth == 0 and index < top_defs[name] and name not in engine and name not in library:
                problems.append((line, '%s is used before the line that defines it' % name))
            continue
        if name in inner_defs or name in engine or name in library or name in reported:
            continue
        reported.add(name)
        if name in noop:
            problems.append((line, '%s does nothing in this engine build' % name))
        else:
            problems.append((line, '%s is not defined anywhere (a call to it would silently do nothing)' % name))
    return sorted(problems)


def update_names():
    """Rebuild lua_names.json from the engine source and the staged retail scripts."""
    import config
    paths = config.load()
    source_root = os.path.join(os.path.dirname(os.path.normpath(paths['engine'])),
                               'Soft', 'Andy', 'Jan03', 'a5dll')
    with open(os.path.join(source_root, 'Main', 'ScriptFunctions.cpp'), encoding='cp1251') as f:
        text = f.read()
    table = text[text.index('pRegList[]'):]
    table = table[:table.index('};')]
    engine = set(re.findall(r'\{\s*"(\w+)"', table)) | set(re.findall(r'REG_FUNCTION\(\s*(\w+)\s*\)', table))
    engine.discard('_ERRORMESSAGE')

    with open(os.path.join(paths['engine'], 'luacompat', 'lua_compat.cpp'), encoding='utf-8', errors='replace') as f:
        text = f.read()
    listed = text[text.index('g_missing[]'):]
    listed = listed[:listed.index('};')]
    noop = set(re.findall(r'"(\w+)"', listed)) - engine

    # the retail library: every file is loaded into the same Lua state
    library = set()
    scripts = os.path.join(paths['run'], 'scripts')
    for name in sorted(os.listdir(scripts)):
        if name.lower().endswith('.l'):
            with open(os.path.join(scripts, name), encoding='cp1251') as f:
                library.update(analyse(f.read())[0])

    with open(NAMES_FILE, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'engine': sorted(engine), 'noop': sorted(noop), 'library': sorted(library)}, f, indent=1)
        f.write('\n')
    print('%s: %d engine functions, %d do-nothing names, %d library names' % (
        NAMES_FILE, len(engine), len(noop), len(library)))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == '--update':
        update_names()
        return
    source = ''
    for path in sys.argv[1:]:
        with open(path, encoding='utf-8') as f:
            source += f.read() + '\n'
    problems = lint(source)
    for line, message in problems:
        print('line %d: %s' % (line, message))
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
