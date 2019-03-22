#!/usr/bin/env python3
"""Generates languages, styles, etc. from pygments for use with
source-highlight.
"""
import os
import re
import inspect

from pygments import lexers
from pygments import styles
from pygments.lexer import words, default, using, this, DelegatingLexer
from pygments.token import Token

import exrex

from xonsh.color_tools import make_palette, find_closest_color, rgb_to_256


BASE_DIR = "share/py-source-highlight"
CURRENT_LEXER = None
LEXER_STACK = None


def quote_safe(s):
    return s.replace("'", r"\x27")


def token_to_rulename(token):
    return str(token).replace(".", '_')


def top_level_groups(s):
    level = 0
    groups = []
    inrange = False
    g = ''
    for c in s:
        g += c
        if not inrange and c == ')':
            level -= 1
            if level == 0:
                groups.append(g)
                g = ''
        elif not inrange and c == '(':
            level += 1
        elif c == '[':
            inrange = True
        elif inrange and c == ']':
            inrange = False
    return groups


def exrex_safe(s):
    """Translates a regex string to be exrex safe, for some missed cases"""
    return s.replace('*?', '{0,100}').replace('+?', '{1,100}')


def longest_sample(regex, n=100, limit=100):
    regex = exrex_safe(regex)
    s = ''
    for i, t in zip(range(n), exrex.generate(regex, limit=limit)):
        t = t.replace('\n', '').replace('\r', '')
        if len(t) > len(s):
            s = t
    return s


#
# Language translators
#

def token_from_using(callback, regex):
    global CURRENT_LEXER
    lexer = CURRENT_LEXER
    sample = longest_sample(regex)
    m = re.match(regex, sample)
    if m is None:
        raise ValueError('cannot compute callback')
    _, token, _ = next(callback(lexer, m))
    return token


# order might matter here
UNCAPTURED_GROUP_TRANSLATORS = [
    # (from, to)
    ('(?!:)',  '[^:]'),
    (r'(\.\.\.)?', r'(|\.\.\.)'),
    (r'((?:\{.*\})?)', r'(|\{.*\})'),
    (r'((?:\d+\.\.)?(?:\d+|\*))', r'(\d+|\*|\d+\.\.\d+|\d+\.\.\*)'),
    (r'((?:\s*;\s*(?:ordered|unordered|unique)){,2})',
     r'(|\s*;\s*ordered|\s*;\s*unordered|\s*;\s*unique|'
     r'\s*;\s*ordered\s*;\s*unique|\s*;\s*unique\s*;\s*ordered|'
     r'\s*;\s*unordered\s*;\s*unique|\s*;\s*unique\s*;\s*unordered)'),
    (r'(\w[\w-]*(?:\([^)\n]+\))?)',
     r'(\w[\w-]*|\w[\w-]*\([^)\n]+\))'),
    (r'((?:[,;])?)', r'(|[,;])'),
    (r'((?:[$a-zA-Z_]\w*|\.)+)', r'([$a-zA-Z_0-9.]+)'),
    (r'([$a-zA-Z_]\w*(?:\.<\w+>)?)', r'([$a-zA-Z_]\w*|[$a-zA-Z_]\w*\.<\w+>)'),
    (r'([$a-zA-Z_]\w*(?:\.<\w+>)?|\*)', r'([$a-zA-Z_]\w*|[$a-zA-Z_]\w*\.<\w+>|\*)'),
    (r'([A-Za-z]\w*|\'(?:\\\\|\\\'|[^\']*)\'|[0-9]+|\*)',
     r'([A-Za-z]\w*|\'\\\\\'|\'\\\'\'|\'[^\']*\'|[0-9]+|\*)'),
]

UNCAPTURED_GROUP_PREFIXES = [
    "(?:",
    "(?=",
    "(?!",
    "(?<=",
    "(?<!",
]


def bygroup_translator(regex, bg, **kwargs):
    tokens = inspect.getclosurevars(bg).nonlocals['args']
    token_names = []
    for i, token in enumerate(tokens):
        if token in Token:
            token_names.append(token_to_rulename(token))
        elif callable(token) and 'using' in token.__qualname__:
            group = top_level_groups(regex)[i]
            token = token_from_using(token, group)
            token_names.append(token_to_rulename(token))
    # rewrite the regex, to make it safe for source-highlight
    if regex.startswith('^'):
        regex = regex[1:]
    for bad, good in UNCAPTURED_GROUP_TRANSLATORS:
        regex = regex.replace(bad, good)
    for prefix in UNCAPTURED_GROUP_PREFIXES:
        if prefix in regex:
            raise ValueError(f"uncaptured prefix {prefix!r} is in regex '{regex}' "
                             "that is being applied to a bygroup transformation")
    rule = "(" + ",".join(token_names) + ") = `" + regex + "`"
    return rule


def using_translator(regex, callback, level=0, **kwargs):
    global CURRENT_LEXER, LEXER_STACK
    lexer_class = inspect.getclosurevars(callback).nonlocals['_other']
    CURRENT_LEXER = lexer = lexer_class()
    LEXER_STACK.append(lexer)
    rules = genrulelines(lexer, level=level)
    del LEXER_STACK[-1]
    CURRENT_LEXER = LEXER_STACK[-1]
    return rules


CALLABLE_RULES = {
    "bygroup": bygroup_translator,
    "bygroups.<locals>.callback": bygroup_translator,
    "using": using_translator,
    "using.<locals>.callback": using_translator,
}

def regex_to_rule(regex, token, action="#none", level=0):
    # some prep
    if isinstance(regex, words):
        regex = regex.get()
    # determine rule
    if callable(token):
        name = token.__qualname__
        translator = CALLABLE_RULES[name]
        rule = translator(regex, token, level=level)
    elif regex == "\\n" and action == "#pop":
        rule = token_to_rulename(token) + " = '$'"
    elif regex.endswith("\\n") or regex.endswith('.*'):
        rule = token_to_rulename(token)
        regex = regex[:-2]
        if regex.endswith('.*'):
            regex = regex[:-2]
        if not regex:
            return ""
        rule += " start '" + quote_safe(regex) + "'"
    else:
        rule = token_to_rulename(token)
        rule += " = '" + quote_safe(regex) + "'"
    return rule


def _push_pop_other(elems):
    push = []
    pop = []
    other = []
    for elem in elems:
        n = len(elem)
        if n == 3 and elem[2] == "#push":
            push.append(elem)
        elif n == 3 and elem[2] == "#pop":
            pop.append(elem)
        else:
            other.append(elem)
    return push, pop, other


def group_regexes(elems):
    if len(elems) == 1:
        return elems[0][0]
    regexes = [elem[0].lstrip('^') for elem in elems]
    grouped = '(' + ')|('.join(regexes) + ')'
    return grouped


def ensure_elems(lexer, state_key, elems):
    global LEXER_STACK
    if elems is not None:
        return elems
    if isinstance(lexer, DelegatingLexer):
        LEXER_STACK.append(lexer.language_lexer)
        elems = ensure_elems(lexer.language_lexer, state_key, elems)
        del LEXER_STACK[-1]
        return elems
    for l in reversed(LEXER_STACK):
        if hasattr(l, 'tokens') and state_key in l.tokens:
            elems = l.tokens[state_key]
            if elems is not None:
                break
        for lexcls in inspect.getmro(l.__class__):
            if not hasattr(lexcls, 'tokens'):
                break
            if state_key in lexcls.tokens:
                elems = lexcls.tokens[state_key]
                if elems is not None:
                    break
        if elems is not None:
            break
    return elems


def return_to_root(lines, indent):
    # go back to root
    if len(lines) == 0:
        return
    prev2 = set(lines[-1].split()[-2:])
    if "exit" not in prev2 and "exitall" not in prev2:
        lines.append(indent + "exitall")


def genrulelines(lexer, state_key="root", level=0, stack=None, elems=None):
    global LEXER_STACK
    lines = []
    indent = "  " * level
    elems = ensure_elems(lexer, state_key, elems)
    stack = ["root"] if stack is None else stack
    needle = lexer.needle if isinstance(lexer, DelegatingLexer) else None
    for elem in elems:
        if isinstance(elem, default):
            # translate default statements into equivalent tuples
            elem = ('', Token.Text, elem.state)
        n = len(elem)
        if isinstance(elem, str):
            if elem == "root":
                return_to_root(lines, indent)
            else:
                # dive into new state
                lines.extend(genrulelines(lexer, state_key=elem, level=level))
        elif n >= 2 and needle is not None and elem[1] is needle:
            # in a delegating lexer that is pointing us elsewhere
            if n > 2:
                raise NotImplementedError
            regex, token = elem
            rule = regex_to_rule(regex, token)
            lines.append(indent + "# delegating to " + lexer.root_lexer.name + " lexer")
            lines.append(indent + "state " + rule + " begin")
            # delegating lexers always delegate to root state
            LEXER_STACK.append(lexer.root_lexer)
            lines.extend(genrulelines(lexer.root_lexer, level=level+1))
            del LEXER_STACK[-1]
            lines.append(indent + "end")
        elif n == 2:
            regex, token = elem
            rule = regex_to_rule(regex, token, level=level+1)
            if isinstance(rule, str):
                lines.append(indent + rule)
            else:
                lines.extend(rule)
        elif n == 3 and isinstance(elem[2], str) and not elem[2] == "root":
            return_to_root(lines, indent)
        elif n == 3 and isinstance(elem[2], str) and not elem[2].startswith('#'):
            regex, token, key = elem
            rule = regex_to_rule(regex, token)
            lines.append(indent + "# " + key + " state")
            lines.append(indent + "state " + rule + " begin")
            lines.extend(genrulelines(lexer, state_key=key, level=level+1))
            lines.append(indent + "end")
        elif n == 3 and elem[2] == "#push":
            pushers, poppers, others = _push_pop_other(lexer.tokens[state_key])
            push_delim = group_regexes(pushers)
            pop_delim = group_regexes(poppers)
            multiline = ('\n' in push_delim) or ('\n' in pop_delim)
            token = elem[1]
            token_name = token_to_rulename(token)
            rule = token_name + " delim '" + quote_safe(push_delim) + "' '"
            rule += quote_safe(pop_delim) + "' "
            if multiline:
                rule += "multiline "
            rule += "nested"
            if len(others) == 0:
                # no internal highlighting rules, just nested
                lines.append(indent + rule)
            else:
                # nested with internal highlighting
                lines.append(indent + "# nested " + state_key + " state")
                lines.append(indent + "state " + rule + " begin")
                lines.extend(genrulelines(lexer, elems=others, level=level+1))
                lines.append(indent + "end")
        elif n == 3 and isinstance(elem[2], str) and elem[2].startswith("#pop"):
            regex, token, action = elem
            rule = regex_to_rule(regex, token, action)
            if rule:
                line = indent + rule + " exit"
                if ":" in action:
                    _, _, n = action.partition(":")
                    line += " " + n
                lines.append(line)
        elif n == 3 and isinstance(elem[2], (tuple, list)) and len(elem[2]) == 2:
            # suppossed to push multiple states onto stack
            regex, token, (key0, key1) = elem
            rule = regex_to_rule(regex, token)
            lines.append(indent + "# " + key1 + " state")
            lines.append(indent + "state " + rule + " begin")
            lines.extend(genrulelines(lexer, state_key=key1, level=level+1))
            if key0 == "#pop":
                pass
            else:
                lines.append(indent + "  # " + key0 + " state")
                lines.append(indent + "  state " + rule + " begin")
                lines.extend(genrulelines(lexer, state_key=key0, level=level+2))
                lines.append(indent + "  end")
            lines.append(indent + "end")
        else:
            raise ValueError("Could not interpret: " + repr(elem))
    lines = filter(str.strip, lines)
    return lines


def genlang(lexer):
    lines = ["# autogenerated from pygments for " + lexer.name]
    lines.extend(genrulelines(lexer))
    lang = "\n".join(lines) + "\n"
    norm_name = lexer.name.lower().replace(' ', '-').replace('+', '')
    fname = os.path.join(BASE_DIR, norm_name + ".lang")
    with open(fname, "w") as f:
        f.write(lang)
    return fname


def add_to_lang_map(lexer, base, lang_map):
    lang_map[lexer.name] = base
    lang_map[lexer.name.lower()] = base
    for alias in lexer.aliases:
        lang_map[alias] = base
        lang_map[alias.lower()] = base
    for filename in lexer.filenames:
        _, _, name = filename.rpartition(".")
        lang_map[name] = base
        lang_map[name.lower()] = base
    for filename in lexer.alias_filenames:
        _, _, name = filename.rpartition(".")
        lang_map[name] = base
        lang_map[name.lower()] = base


def write_lang_map(lang_map, base="lang.map"):
    print("Writing " + base)
    lines = []
    for key, value in sorted(lang_map.items()):
        lines.append(key + " = " + value)
    s = "\n".join(lines) + "\n"
    fname = os.path.join(BASE_DIR, base)
    with open(fname, "w") as f:
        f.write(s)


def get_lexer_from_lookup(name, lookups):
    lxr = None
    try:
        lxr = lexers.get_lexer_by_name(name)
        return lxr
    except Exception:
        pass
    try:
        modname = name.replace(' ', '')
        lxr = lexers.get_lexer_by_name(modname)
        return lxr
    except Exception:
        pass
    for alias in lookups[name][1]:
        try:
            lxr = lexers.get_lexer_by_name(alias)
            return lxr
        except Exception:
            pass
    raise RuntimeError('could not find lexer ' + name)

def genlangs():
    global CURRENT_LEXER, LEXER_STACK
    #lexer_names = ["ActionScript3", "diff", "ini", "pkgconfig", "c"]
    #lexer_names = ["adl"]
    lexer_lookups = {x[0]: x for x in lexers.get_all_lexers()}
    lexer_names = list(lexer_lookups.keys())
    lang_map = {}
    for lexer_name in lexer_names:
        print("Generating lexer " + lexer_name)
        lexer = get_lexer_from_lookup(lexer_name, lexer_lookups)
        CURRENT_LEXER = lexer
        LEXER_STACK = [lexer]
        fname = genlang(lexer)
        base = os.path.basename(fname)
        add_to_lang_map(lexer, base, lang_map)
    CURRENT_LEXER = None
    write_lang_map(lang_map)


#
# Style translators
#

LOGICAL_COLORS = {
    "black": (0, 0, 0),
    "red": (255, 0, 0),
    "darkred": (170, 0, 0),
    "brown": (170, 85, 0),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "blue": (0, 0, 255),
    "pink": (255, 0, 255),
    "purple": (170, 0, 170),
    "orange": (252, 127, 0),
    "brightorange": (252, 170, 0),
    "green": (0, 255, 0),
    "brightgreen": (85, 255, 85),
    "darkgreen": (0, 128, 0),
    "teal": (0, 128, 128),
    "gray": (170, 170, 170),
    "darkblue": (0, 0, 170),
    "white": (255, 255, 255),
}
MODIFIER_TRANSLATIONS = {
    "bold": "b",
    "italic": "i",
    "underline": "u",
}


def pygments_to_srchilite_color(color, hexes_to_names):
    parts = color.split()
    translated = []
    modifiers = []
    for part in parts:
        if part.startswith('#'):
           translated.append(hexes_to_names[part[1:]])
        elif part.startswith('bg:#'):
            translated.append('bg:' + hexes_to_names[part[4:]])
        elif part in MODIFIER_TRANSLATIONS:
            modifiers.append(MODIFIER_TRANSLATIONS[part])
        else:
            raise ValueError(f"could not translate pygments color {color!r}.")
    if modifiers:
        translated.append(", ".join(modifiers))
    rtn = " ".join(translated)
    return rtn


def find_token_color(style, token, color, default="#000000"):
    while not color:
        if color is None:
            color = default
        elif len(color) == 0:
            token = token.parent
            color = style.styles.get(token, default)
        else:
            raise ValueError("could not find token color")
    return color


def make_color_translators(palette):
    """Makes style translation dicts based on a color palette."""
    names_to_hexes = {}
    hexes_to_names = {}
    names_to_short = {}
    short_to_names = {}
    for name, t in LOGICAL_COLORS.items():
        color = find_closest_color(t, palette)
        names_to_hexes[name] = color
        hexes_to_names[color] = name
        short = rgb_to_256(color)[0]
        names_to_short[name] = short
        short_to_names[short] = name
    return names_to_hexes, hexes_to_names, names_to_short, short_to_names


def genstyle(style, style_name, hexes_to_names):
    lines = []
    fgcolor = '#' + max(hexes_to_names.keys())
    for token, color in sorted(style.styles.items()):
        rulename = token_to_rulename(token)
        color = find_token_color(style, token, color, default=fgcolor)
        shcolor = pygments_to_srchilite_color(color, hexes_to_names)
        lines.append(rulename + " " + shcolor +  ";")
    s = "\n".join(lines) + "\n"
    fname = os.path.join(BASE_DIR, style_name.lower() + ".style")
    with open(fname, 'w') as f:
        f.write(s)
    return fname


ESC256_OUTLANG = """# style map for {style_name}
extension "txt"

styletemplate "\\x1b[$stylem$text\\x1b[m"
color "00;38;05;$style"

colormap
{colors}
default "255"
end
"""


def genstyle_esc256outlang(style_name, names_to_short):
    colors = []
    for name, short in sorted(names_to_short.items()):
        colors.append(f'"{name}" "{short}"')
    colors = "\n".join(colors)
    s = ESC256_OUTLANG.format(colors=colors, style_name=style_name)
    fname = os.path.join(BASE_DIR, style_name.lower() + "_esc256.outlang")
    with open(fname, 'w') as f:
        f.write(s)
    return fname


def genstyles():
    style_names = ["monokai"]
    outlang_map = {}
    for style_name in style_names:
        print("Generating style " + style_name)
        style = styles.get_style_by_name(style_name)
        palette = make_palette(style.styles.values())
        translators = make_color_translators(palette)
        fname = genstyle(style, style_name, translators[1])
        fname = genstyle_esc256outlang(style_name, translators[2])
        base = os.path.basename(fname)
        ol = os.path.splitext(base)[0]
        outlang_map[ol] = base
    write_lang_map(outlang_map, base="outlang.map")

#
# Main
#


def main(args=None):
    genlangs()
    genstyles()


if __name__ == "__main__":
    main()
