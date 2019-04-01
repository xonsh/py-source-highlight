#!/usr/bin/env python3
"""Generates languages, styles, etc. from pygments for use with
source-highlight.
"""
import os
import re
import sys
import inspect
import itertools
from re import sre_parse
from pprint import pprint

from pygments import lexers
from pygments import styles
from pygments.lexer import words, default, using, this, DelegatingLexer, RegexLexer
from pygments.token import Token

import exrex

from xonsh.color_tools import make_palette, find_closest_color, rgb_to_256


BASE_DIR = "share/py-source-highlight"
CURRENT_LEXER = None
LEXER_STACK = None


def quote_safe(s):
    return s.replace("'", r"\x27")


def token_to_rulename(token):
    return str(token).replace(".", "_")


def top_level_groups(s):
    level = 0
    groups = []
    inrange = False
    g = ""
    for c in s:
        g += c
        if not inrange and c == ")":
            level -= 1
            if level == 0:
                groups.append(g)
                g = ""
        elif not inrange and c == "(":
            level += 1
        elif c == "[":
            inrange = True
        elif inrange and c == "]":
            inrange = False
    if g:
        groups.append(g)
    return groups


def exrex_safe(s):
    """Translates a regex string to be exrex safe, for some missed cases"""
    return s.replace("*?", "{0,100}").replace("+?", "{1,100}")


def longest_sample(regex, n=100, limit=100):
    regex = exrex_safe(regex)
    s = ""
    for i, t in zip(range(n), exrex.generate(regex, limit=limit)):
        t = t.replace("\n", "").replace("\r", "")
        if len(t) > len(s):
            s = t
    return s


def getone_match(regex, n=100, replace_newlines=True):
    m = None
    safe = exrex_safe(regex)
    while m is None and n > 0:
        sample = exrex.getone(safe, n)
        if replace_newlines:
            sample = sample.replace("\n", "").replace("\r", "")
        m = re.match(regex, sample)
        n -= 1
    return m


#
# Language translators
#


def get_match(regex):
    sample = longest_sample(regex)
    m = re.match(regex, sample)
    if m is not None:
        return m
    m = getone_match(regex)
    if m is not None:
        return m
    m = getone_match(regex, replace_newlines=False)
    if m is not None:
        return m
    raise ValueError("cannot compute callback")


def token_from_using(callback, regex):
    global CURRENT_LEXER
    lexer = CURRENT_LEXER
    try:
        m = get_match(regex)
    except Exception:
        return Token.Text
    try:
        _, token, _ = next(callback(lexer, m))
    except StopIteration:
        token = Token.Text
    return token


UNCAPTURED_GROUP_PREFIXES = ["(?:", "(?=", "(?!", "(?<=", "(?<!"]


class EchoTranslator:
    """Translates regexes into the same regex, useful for
    subclassing only a part of the regex.
    """

    def translate(self, s, paren=True):
        if isinstance(s, str):
            sre_obj = exrex.parse(s)
        else:
            sre_obj = s
        # dispatch to the proper method
        ret = ""
        for i in sre_obj:
            meth = getattr(self, "translate_" + i[0].name.lower(), None)
            if meth is None:
                raise ValueError(f"could not find translation method for {i}")
            ret += meth(i, paren=paren)
        return ret

    def translate_in(self, i, paren=True):
        ret = "[{0}]".format(self.translate(i[1], paren=paren))
        return ret

    def translate_literal(self, i, paren=True):
        n = i[1]
        c = chr(n)
        if c in sre_parse.SPECIAL_CHARS:
            # format literal special characters with hex codes
            ret = "\\{0}".format(c)
        else:
            ret = c
        return ret

    def translate_category(self, i, paren=True):
        return exrex.REVERSE_CATEGORIES[i[1]]

    def translate_any(self, i, paren=True):
        return "."

    def translate_branch(self, i, paren=True):
        # TODO simplifications here
        parts = [self.translate(x, paren=paren) for x in i[1][1]]
        if not any(parts):
            return ""
        if i[1][0]:
            if len(parts) == 1:
                paren = False
            prefix = ""
        else:
            prefix = "?:"
        branch = "|".join(parts)
        if paren:
            ret = "({0}{1})".format(prefix, branch)
        else:
            ret = "{0}".format(branch)
        return ret

    def translate_subpattern(self, i, paren=True):
        subexpr = i[1][1]
        if exrex.IS_PY36_OR_GREATER and i[0] == sre_parse.SUBPATTERN:
            subexpr = i[1][3]
        if i[1][0]:
            ret = "({0})".format(self.translate(subexpr, paren=False))
        else:
            ret = "{0}".format(self.translate(subexpr, paren=paren))
        return ret

    def translate_not_literal(self, i, paren=True):
        return "[^{0}]".format(chr(i[1]))

    def translate_max_repeat(self, i, paren=True):
        if i[1][0] == i[1][1]:
            range_str = "{{{0}}}".format(i[1][0])
        else:
            if i[1][0] == 0 and i[1][1] - i[1][0] == sre_parse.MAXREPEAT:
                range_str = "*"
            elif i[1][0] == 1 and i[1][1] - i[1][0] == sre_parse.MAXREPEAT - 1:
                range_str = "+"
            else:
                range_str = "{{{0},{1}}}".format(i[1][0], i[1][1])
        ret = self.translate(i[1][2], paren=paren) + range_str
        return ret

    def translate_min_repeat(self, i, paren=True):
        if i[1][0] == 0 and i[1][1] == sre_parse.MAXREPEAT:
            range_str = "*?"
        elif i[1][0] == 1 and i[1][1] == sre_parse.MAXREPEAT:
            range_str = "+?"
        elif i[1][1] == sre_parse.MAXREPEAT:
            range_str = "{{{0},}}?".format(i[1][0])
        else:
            range_str = "{{{0},{1}}}?".format(i[1][0], i[1][1])
        ret = self.translate(i[1][2], paren=paren) + range_str
        return ret

    def translate_groupref(self, i, paren=True):
        return "\\{0}".format(i[1])

    def translate_groupref_exists(self, i, paren=True):
        nameid, yesexpr, noexpr = i[1]
        yes = self.translate(yesexpr, paren=paren)
        prefix = f"(?({nameid}){yes}"
        if noexpr is None:
            ret = prefix + ")"
        else:
            no = self.translate(yesexpr, paren=paren)
            ret = prefix + "|" + no + ")"
        return ret

    def translate_at(self, i, paren=True):
        if i[1] == sre_parse.AT_BEGINNING:
            ret = "^"
        elif i[1] == sre_parse.AT_END:
            ret = "$"
        else:
            ret = ""
        return ret

    def translate_negate(self, i, paren=True):
        return "^"

    def translate_range(self, i, paren=True):
        return "{0}-{1}".format(chr(i[1][0]), chr(i[1][1]))

    def translate_assert(self, i, paren=True):
        if i[1][0]:
            ret = "(?={0})".format(self.translate(i[1][1], paren=False))
        else:
            ret = "{0}".format(self.translate(i[1][1], paren=paren))
        return ret

    def translate_assert_not(self, i, paren=True):
        if i[1][0]:
            ret = "(?!{0})".format(self.translate(i[1][1], paren=False))
        else:
            raise NotImplementedError
            # ret = '{0}'.format(self.translate(i[1][1], paren=paren))
        return ret


ECHO_TRANSLATOR = EchoTranslator()
echo_translate = ECHO_TRANSLATOR.translate


class NoncapturingTranslator(EchoTranslator):
    """Translator that does not include non-capturing sub-expressions"""

    def translate_branch(self, i, paren=True):
        # TODO simplifications here
        parts = [self.translate(x, paren=paren) for x in i[1][1]]
        if not any(parts):
            return ""
        if i[1][0]:
            if len(parts) == 1:
                paren = False
            prefix = ""
        else:
            paren = False
        branch = "|".join(parts)
        if paren:
            ret = "({0}{1})".format(prefix, branch)
        else:
            ret = "{0}".format(branch)
        return ret


NONCAPTURING_TRANSLATOR = NoncapturingTranslator()
noncapturing_translate = NONCAPTURING_TRANSLATOR.translate


def remove_noncapturing_transform(s, ret=None):
    """Removes non-capturing expressions from regex"""
    sre_obj = exrex.parse(s) if isinstance(s, str) else s
    ret = [] if ret is None else ret
    need_to_expand = False
    expansions = {}
    for n, i in enumerate(sre_obj):
        if i[0] == sre_parse.BRANCH:
            parts = list(map(remove_noncapturing_transform, i[1][1]))
            if not any(parts):
                continue
            ret.append((sre_parse.BRANCH, (i[1][0], parts)))
        elif i[0] == sre_parse.SUBPATTERN:
            if exrex.IS_PY36_OR_GREATER and i[0] == sre_parse.SUBPATTERN:
                subexpr = i[1][3]
            else:
                raise RuntimeError("Python >=3.6 required")
                # subexpr = i[1][1]  expr for Python < 3.6
            parts = remove_noncapturing_transform(subexpr)
            if len(parts) == 0:
                continue
            if i[1][0]:
                # captured subpattern, just copy and return
                if (
                    len(parts) == 1
                    and parts[0][0] == sre_parse.MAX_REPEAT
                    and parts[0][1][2][0][0] == sre_parse.SUBPATTERN
                    and parts[0][1][2][0][1][0] is None
                ):
                    # Matches things like "((?:hello)?)" and converts to "(|hello)"
                    sub = list(parts[0][1][2][0][1][3])
                    low = parts[0][1][0]
                    high = parts[0][1][1] + 1
                    if high < 102:
                        branches = [sub * n for n in range(low, high)]
                        parts = [(sre_parse.BRANCH, (None, branches))]
                elif (
                    len(parts) == 1
                    and parts[0][0] == sre_parse.MAX_REPEAT
                    and len(parts[0][1][2]) > 1
                ):
                    sub = list(parts[0][1][2])
                    low = parts[0][1][0]
                    high = parts[0][1][1] + 1
                    if high < 102:
                        branches = [sub * n for n in range(low, high)]
                        parts = [(sre_parse.BRANCH, (None, branches))]
                ret.append((sre_parse.SUBPATTERN, (i[1][0], i[1][1], i[1][2], parts)))
            else:
                # uncaptured subexpression, (?:...), may need to expand
                if parts[0][0] == sre_parse.BRANCH:
                    need_to_expand = True
                    expansions[n] = parts[0][1][1]
                    ret.append(n)
                else:
                    # non-branching, just add to current level
                    ret.extend(parts)
        elif i[0] == sre_parse.ASSERT:
            subexpr = i[1][1]
            parts = remove_noncapturing_transform(subexpr)
            if len(parts) == 0:
                continue
            if parts[0][0] == sre_parse.BRANCH:
                need_to_expand = True
                expansions[n] = parts[0][1][1]
                ret.append(n)
            else:
                # non-branching, just add to current level
                ret.extend(parts)
        elif i[0] == sre_parse.ASSERT_NOT:
            subexpr = i[1][1]
            parts = remove_noncapturing_transform(subexpr)
            if len(parts) == 0:
                continue
            if parts[0][0] == sre_parse.IN:
                ins = [(sre_parse.NEGATE, None)] + parts[0][1]
                ret.append((sre_parse.MAX_REPEAT, (0, 1, [(sre_parse.IN, ins)])))
            elif parts[0][0] == sre_parse.BRANCH:
                literals = parts[0][1][1]
                removals = []
                for n, literal in enumerate(literals):
                    if literal[0] == sre_parse.AT:
                        removals.append(n)
                    elif (
                        isinstance(literal, list) and literal[0][0] == sre_parse.LITERAL
                    ):
                        msg = "unsafe translation of {0!r} to {1!r}"
                        sys.stdout.flush()
                        print(
                            msg.format(
                                echo_translate(literal), echo_translate([literal[0]])
                            ),
                            file=sys.stderr,
                            flush=True,
                        )
                        literals[n] = literal[0]
                    elif literal[0] != sre_parse.LITERAL:
                        raise RuntimeError(f"Cannot translate expression: {literal}")
                for n in reversed(removals):
                    del literals[n]
                ins = [(sre_parse.NEGATE, None)] + literals
                ret.append((sre_parse.MAX_REPEAT, (0, 1, [(sre_parse.IN, ins)])))
            elif len(parts) == 1 and parts[0][0] == sre_parse.LITERAL:
                ret.append(
                    (
                        sre_parse.MAX_REPEAT,
                        (0, 1, [(sre_parse.NOT_LITERAL, parts[0][1])]),
                    )
                )
            elif len(parts) == 1 and parts[0][0] == sre_parse.GROUPREF:
                ret.append(
                    (sre_parse.MAX_REPEAT, (0, 0, [(sre_parse.GROUPREF, parts[0][1])]))
                )
            elif len(parts) > 1 and parts[0][0] == sre_parse.LITERAL:
                replacement = (
                    sre_parse.MAX_REPEAT,
                    (0, 1, [(sre_parse.NOT_LITERAL, parts[0][1])]),
                )
                msg = "unsafe translation of {0!r} to {1!r}"
                sys.stdout.flush()
                print(
                    msg.format(echo_translate(subexpr), echo_translate([replacement])),
                    file=sys.stderr,
                    flush=True,
                )
                ret.append(replacement)
            else:
                print(repr(echo_translate(subexpr)))
                raise RuntimeError(
                    "cannot translate multi-character assert-not (?!...)"
                )
        elif i[0] == sre_parse.MAX_REPEAT:
            parts = remove_noncapturing_transform(i[1][2])
            ret.append((sre_parse.MAX_REPEAT, (i[1][0], i[1][1], parts)))
        elif i[0] == sre_parse.MIN_REPEAT:
            parts = remove_noncapturing_transform(i[1][2])
            ret.append((sre_parse.MIN_REPEAT, (i[1][0], i[1][1], parts)))
        else:
            ret.append(i)
    # OK do the expansions
    if need_to_expand:
        iters = []
        ntimes = max(map(len, expansions.values()))
        for i in ret:
            if isinstance(i, int):
                iters.append(expansions[i])
            else:
                iters.append(itertools.repeat(i, 1))
        parts = []
        for prod in itertools.product(*iters):
            p = []
            for elem in prod:
                if isinstance(elem, list):
                    p.extend(elem)
                else:
                    p.append(elem)
            parts.append(p)
        ret = [(sre_parse.BRANCH, (None, parts))]
    return ret


def remove_noncapturing(s):
    sre_obj = remove_noncapturing_transform(s)
    ret = noncapturing_translate(sre_obj)
    return ret


def bygroup_translator(regex, bg, **kwargs):
    tokens = inspect.getclosurevars(bg).nonlocals["args"]
    token_names = []
    for i, token in enumerate(tokens):
        if token in Token:
            token_names.append(token_to_rulename(token))
        elif callable(token) and "using" in token.__qualname__:
            group = top_level_groups(regex)[: i + 1][-1]
            token = token_from_using(token, group)
            token_names.append(token_to_rulename(token))
    # rewrite the regex, to make it safe for source-highlight
    orig_regex = regex
    if regex.startswith("^"):
        regex = regex[1:]
    try:
        regex = remove_noncapturing(regex)
    except Exception:
        print(f"Original Regex is: {orig_regex!r}")
        raise
    for prefix in UNCAPTURED_GROUP_PREFIXES:
        if prefix in regex:
            groups = top_level_groups(orig_regex)
            gmsg = "\n------\n".join(groups)
            troups = top_level_groups(regex)
            tmsg = "\n------\n".join(troups)
            raise ValueError(
                f"uncaptured prefix {prefix!r} is in regex '{regex}' "
                "that is being applied to a bygroup transformation. "
                "\n\nTop level groups of original regex:\n\n"
                + gmsg
                + "\n\nTop level groups of transformed regex:\n\n"
                + tmsg
            )
    rule = "(" + ",".join(token_names) + ") = `" + regex + "`"
    return rule


def using_translator_other(regex, callback, nonlocals, level=0, **kwargs):
    global CURRENT_LEXER, LEXER_STACK
    lexer_class = nonlocals["_other"]
    CURRENT_LEXER = lexer = lexer_class()
    LEXER_STACK.append(lexer)
    rules = genrulelines(lexer, level=level)
    del LEXER_STACK[-1]
    CURRENT_LEXER = LEXER_STACK[-1]
    return rules


def using_translator_stack(regex, callback, nonlocals, level=0, **kwargs):
    global CURRENT_LEXER, LEXER_STACK
    stack = nonlocals["gt_kwargs"]["stack"]
    lexer = CURRENT_LEXER
    rules = genrulelines(lexer, state_key=stack[-1], level=level)
    return rules


def using_translator(regex, callback, level=0, **kwargs):
    global CURRENT_LEXER, LEXER_STACK
    nonlocals = inspect.getclosurevars(callback).nonlocals
    if "_other" in nonlocals:
        f = using_translator_other
    elif "gt_kwargs" in nonlocals and "stack" in nonlocals["gt_kwargs"]:
        f = using_translator_stack
    else:
        raise ValueError("could not interpret using")
    rules = f(regex, callback, nonlocals, level=level, **kwargs)
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
        if name in CALLABLE_RULES:
            translator = CALLABLE_RULES[name]
            rule = translator(regex, token, level=level)
        else:
            rule = ""
            sys.stdout.flush()
            print(
                f'skipping rule "{regex}" with {token} because {name} does '
                "not have a translator",
                file=sys.stderr,
                flush=True,
            )
    elif regex == "\\n" and action == "#pop":
        rule = token_to_rulename(token) + " = '$'"
    elif regex.endswith("\\n") or regex.endswith(".*"):
        rule = token_to_rulename(token)
        regex = regex[:-2]
        if regex.endswith(".*"):
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
    regexes = [elem[0].lstrip("^") for elem in elems]
    grouped = "(" + ")|(".join(regexes) + ")"
    return grouped


VARIANTS = (
    "full",
    "basic",
    "none",
    "+i6t-not-inline",
    "+i6t-inline",
    "+i6t-use-option",
)


def ensure_elems(lexer, state_key, elems):
    global LEXER_STACK
    if elems is not None:
        return elems
    if isinstance(lexer, DelegatingLexer):
        LEXER_STACK.append(lexer.language_lexer)
        elems = ensure_elems(lexer.language_lexer, state_key, elems)
        del LEXER_STACK[-1]
        if elems is None:
            LEXER_STACK.append(lexer.root_lexer)
            elems = ensure_elems(lexer.root_lexer, state_key, elems)
            del LEXER_STACK[-1]
        return elems
    for l in reversed(LEXER_STACK):
        if hasattr(l, "tokens") and state_key in l.tokens:
            elems = l.tokens[state_key]
            if elems is not None:
                break
        elif hasattr(l, "tokens") and len(set(VARIANTS) & set(l.tokens.keys())) > 0:
            for variant in VARIANTS:
                elems = l.tokens.get(variant, {}).get(state_key, None)
                if elems is not None:
                    break
        if elems is not None:
            break
        for lexcls in inspect.getmro(l.__class__):
            if not hasattr(lexcls, "tokens"):
                break
            if state_key in lexcls.tokens:
                elems = lexcls.tokens[state_key]
            if elems is not None:
                break
            elif len(set(VARIANTS) & set(lexcls.tokens.keys())) > 0:
                for variant in VARIANTS:
                    elems = lexcls.tokens.get(variant, {}).get(state_key, None)
                    if elems is not None:
                        break
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
    if elems is None:
        import pdb

        pdb.set_trace()
    stack = ["root"] if stack is None else stack
    if state_key == "root":
        pass
    elif state_key in stack:
        # need to prevent recurrsion
        return []
    else:
        stack.append(state_key)
    needle = lexer.needle if isinstance(lexer, DelegatingLexer) else None
    for elem in elems:
        if isinstance(elem, default):
            # translate default statements into equivalent tuples
            elem = ("", Token.Text, elem.state)
        n = len(elem)
        if isinstance(elem, str):
            if elem == "root":
                return_to_root(lines, indent)
            else:
                # dive into new state
                lines.extend(
                    genrulelines(lexer, state_key=elem, level=level, stack=stack)
                )
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
            lines.extend(genrulelines(lexer.root_lexer, level=level + 1, stack=stack))
            del LEXER_STACK[-1]
            lines.append(indent + "end")
        elif n == 2:
            regex, token = elem
            rule = regex_to_rule(regex, token, level=level + 1)
            if isinstance(rule, str):
                lines.append(indent + rule)
            else:
                lines.extend(rule)
        elif n == 3 and isinstance(elem[2], str) and not elem[2] == "root":
            return_to_root(lines, indent)
        elif n == 3 and isinstance(elem[2], str) and not elem[2].startswith("#"):
            regex, token, key = elem
            rule = regex_to_rule(regex, token)
            lines.append(indent + "# " + key + " state")
            lines.append(indent + "state " + rule + " begin")
            lines.extend(
                genrulelines(lexer, state_key=key, level=level + 1, stack=stack)
            )
            lines.append(indent + "end")
        elif n == 3 and elem[2] == "#push":
            pushers, poppers, others = _push_pop_other(lexer.tokens[state_key])
            push_delim = group_regexes(pushers)
            pop_delim = group_regexes(poppers)
            multiline = ("\n" in push_delim) or ("\n" in pop_delim)
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
                lines.extend(
                    genrulelines(lexer, elems=others, level=level + 1, stack=stack)
                )
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
        elif n == 3 and isinstance(elem[2], (tuple, list)):
            # suppossed to push multiple states onto stack
            regex, token, keys = elem
            nstack = 0
            for i, key in enumerate(reversed(keys)):
                rule = regex_to_rule(regex, token)
                if key == "#pop":
                    pass
                elif key.startswith("#"):
                    raise ValueError("Don't know how to interpret action")
                elif key == "root":
                    return_to_root(lines, "  " * (level + 1 + i))
                else:
                    lines.append(indent + "# " + key + " state")
                    if not isinstance(rule, str):
                        rule = next(rule)
                    lines.append(indent + "state " + rule + " begin")
                    lines.extend(
                        genrulelines(
                            lexer, state_key=key, level=level + 1 + i, stack=stack
                        )
                    )
                    lines.append(indent + "end")
                    stack.append(key)
                    nstack += 1
                regex = ".*?"
                token = Token.Text
            del stack[-nstack:]
        else:
            raise ValueError("Could not interpret: " + repr(elem))
    if len(stack) == 0:
        stack.append("root")
    elif len(stack) == 1:
        pass
    else:
        del stack[-1]
    lines = filter(str.strip, lines)
    return lines


def genlang(lexer):
    lines = ["# autogenerated from pygments for " + lexer.name]
    lines.extend(genrulelines(lexer))
    lang = "\n".join(lines) + "\n"
    norm_name = lexer.name.lower().replace(" ", "-").replace("+", "").replace("/", "")
    fname = os.path.join(BASE_DIR, norm_name + ".lang")
    with open(fname, "w", errors="backslashreplace") as f:
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
        modname = name.replace(" ", "")
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
    raise RuntimeError("could not find lexer " + name)


def genlangs():
    global CURRENT_LEXER, LEXER_STACK
    # lexer_names = ["ActionScript3", "diff", "ini", "pkgconfig", "c"]
    # lexer_names = ["adl"]
    lexer_lookups = {x[0]: x for x in lexers.get_all_lexers()}
    lexer_names = list(lexer_lookups.keys())
    lang_map = {}
    for lexer_name in lexer_names:
        lexer = get_lexer_from_lookup(lexer_name, lexer_lookups)
        if not isinstance(lexer, (RegexLexer, DelegatingLexer)):
            print(
                "Skipping " + lexer_name + " because it is not "
                "a RegexLexer or Delegating lexer."
            )
            continue
        print("Generating lexer " + lexer_name)
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
MODIFIER_TRANSLATIONS = {"bold": "b", "italic": "i", "underline": "u"}


def pygments_to_srchilite_color(color, hexes_to_names):
    parts = color.split()
    translated = []
    modifiers = []
    for part in parts:
        if part.startswith("#"):
            translated.append(hexes_to_names[part[1:]])
        elif part.startswith("bg:#"):
            translated.append("bg:" + hexes_to_names[part[4:]])
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
    fgcolor = "#" + max(hexes_to_names.keys())
    for token, color in sorted(style.styles.items()):
        rulename = token_to_rulename(token)
        color = find_token_color(style, token, color, default=fgcolor)
        shcolor = pygments_to_srchilite_color(color, hexes_to_names)
        lines.append(rulename + " " + shcolor + ";")
    s = "\n".join(lines) + "\n"
    fname = os.path.join(BASE_DIR, style_name.lower() + ".style")
    with open(fname, "w") as f:
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
    with open(fname, "w") as f:
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


def test():
    r = r"Isaac (?!B|A)"
    r = r"(if(?:(?=\()|(?=\^?[\t\v\f\r ,;=\xa0]|[&<>|\n\x1a]))(?!\^))((?:(?:(?:\^[\n\x1a])?[\t\v\f\r ,;=\xa0])+)?)((?:/i(?=\^?[\t\v\f\r ,;=\xa0]|[&<>|\n\x1a]))?)((?:(?:(?:\^[\n\x1a])?[\t\v\f\r ,;=\xa0])+)?)((?:not(?=\^?[\t\v\f\r ,;=\xa0]|[&<>|\n\x1a]))?)((?:(?:(?:\^[\n\x1a])?[\t\v\f\r ,;=\xa0])+)?)"
    r = r"((?:(?<=[\n\x1a\t\v\f\r ,;=\xa0])\d)?)"
    # r = r'(?<=[\n\x1a\t\v\f\r ,;=\xa0])\d'
    r = r"(?<=[-+/*%=<>&!^|~,(])(\\s*)(%([\\t ])(?:(?:\\\\\\3|(?!\\3).)*)\\3)"
    pprint(exrex.parse(r))
    print("-" * 40)
    try:
        pprint(remove_noncapturing_transform(r))
    except:
        pprint(exrex.parse(r))
    pprint(remove_noncapturing(r))


if __name__ == "__main__":
    main()
    # test()
