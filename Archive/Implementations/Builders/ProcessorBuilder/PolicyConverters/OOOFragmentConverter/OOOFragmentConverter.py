"""MFOTL -> ooo-fragment policy converter (syntax rewriting, no safety
analysis: the generated policies are already TimelyMon-monitorable, so every
node maps one to one; wf_tra re-verifies the result at load via -columns).

Mapping (rosetta: frontend/tests t1..t6 of formalized_streaming_monitor):
    P(t..)                 -> (PRED P t..)
    phi AND psi            -> (JOIN phi' psi')
    phi AND NOT psi        -> (ANTIJOIN phi' psi')
    phi AND (x = t)        -> (FILTEREQ phi' false x t)   [x in fv(phi)]
                           -> (EXTENDEQ phi' i t)         [x new column i]
    phi AND NOT (x = t)    -> (FILTEREQ phi' true x t)
    phi OR psi             -> (UNION phi' psi')
    EXISTS y. phi          -> (EXISTS phi')               [de Bruijn, binds x0]
    x = t (standalone)     -> (EQ x t)
    PREVIOUS[I] phi        -> (PREV [I] phi')
    NEXT[I] phi            -> (NEXT [I] phi')
    ONCE[I] phi            -> (SINCE (EQ 0 0) [I] phi')
    EVENTUALLY[I] phi      -> (UNTIL (EQ 0 0) [I] phi')
    phi SINCE[I] psi       -> (SINCE phi' [I] psi')
    (NOT phi) SINCE[I] psi -> (NEGSINCE phi' [I] psi')
    phi UNTIL[I] psi       -> (UNTIL phi' [I] psi'), NEGUNTIL analogous

Variables: free MFOTL variables sorted by natural name order become x0, x1,
... at the top level; each EXISTS binds index 0 and shifts the frame.
Intervals: [l,r] closed, [l,*) -> [l,*]; a finite half-open [l,r) becomes
[l,r-1] (integer timestamps)."""

import re
from typing import Any, Dict, List, Tuple

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.Builders.ProcessorBuilder.PolicyConverters.PolicyConverterTemplate import (
    PolicyConverterTemplate, PolicyTransformationException)

TOKEN_RE = re.compile(r'"[^"]*"|-?\d+\.\d+|-?\d+|[A-Za-z_][A-Za-z0-9_]*|[()\[\],.*=]')
TEMPORAL_UNARY = {"ONCE", "EVENTUALLY", "PREVIOUS", "NEXT"}
TEMPORAL_BINARY = {"SINCE", "UNTIL"}
TRUE_LEFT = "(EQ 0 0)"


class _Tokens:
    def __init__(self, text: str):
        self.tokens = TOKEN_RE.findall(text)
        self.position = 0

    def peek(self):
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def next(self):
        if self.position >= len(self.tokens):
            raise PolicyTransformationException("OOOFragmentConverter: unexpected end of policy")
        token = self.tokens[self.position]
        self.position += 1
        return token

    def expect(self, token: str):
        got = self.next()
        if got != token:
            raise PolicyTransformationException(
                f"OOOFragmentConverter: expected {token!r}, got {got!r}")


def _is_const(token: str) -> bool:
    return token.startswith('"') or re.fullmatch(r"-?\d+(\.\d+)?", token) is not None


def _parse_term(tk: _Tokens):
    token = tk.next()
    if _is_const(token):
        return ("const", token)
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
        return ("var", token)
    raise PolicyTransformationException(f"OOOFragmentConverter: bad term {token!r}")


def _parse_interval(tk: _Tokens) -> Tuple[int, Any]:
    tk.expect("[")
    low = int(tk.next())
    tk.expect(",")
    right = tk.next()
    if right == "*":
        closer = tk.next()
        if closer not in (")", "]"):
            raise PolicyTransformationException(
                f"OOOFragmentConverter: bad interval closer {closer!r}")
        return low, None
    high = int(right)
    closer = tk.next()
    if closer == "]":
        return low, high
    if closer == ")":
        if high - 1 < low:
            raise PolicyTransformationException(
                f"OOOFragmentConverter: empty interval [{low},{high})")
        return low, high - 1
    raise PolicyTransformationException(f"OOOFragmentConverter: bad interval closer {closer!r}")


def _parse_formula(tk: _Tokens):
    tk.expect("(")
    node = _parse_inner(tk)
    tk.expect(")")
    return node


def _parse_operand(tk: _Tokens):
    token = tk.peek()
    if token == "(":
        return _parse_formula(tk)
    if token == "NOT":
        tk.next()
        return ("not", _parse_formula(tk))
    if token == "EXISTS":
        tk.next()
        var = tk.next()
        tk.expect(".")
        return ("exists", var, _parse_formula(tk))
    if token in TEMPORAL_UNARY:
        tk.next()
        interval = _parse_interval(tk)
        return (token.lower(), interval, _parse_formula(tk))
    if token is not None and _is_const(token):
        left = _parse_term(tk)
        tk.expect("=")
        return ("eq", left, _parse_term(tk))
    name = tk.next()
    if tk.peek() == "(":
        tk.next()
        args = []
        while tk.peek() != ")":
            args.append(_parse_term(tk))
            if tk.peek() == ",":
                tk.next()
        tk.expect(")")
        return ("pred", name, args)
    if tk.peek() == "=":
        tk.next()
        return ("eq", ("var", name), _parse_term(tk))
    raise PolicyTransformationException(
        f"OOOFragmentConverter: cannot parse at {name!r} {tk.peek()!r}")


def _parse_inner(tk: _Tokens):
    left = _parse_operand(tk)
    while True:
        token = tk.peek()
        if token is None or token == ")":
            return left
        op = tk.next().upper()
        if op == "AND":
            left = ("and", left, _parse_operand(tk))
        elif op == "OR":
            left = ("or", left, _parse_operand(tk))
        elif op in TEMPORAL_BINARY:
            interval = _parse_interval(tk)
            left = (op.lower(), left, interval, _parse_operand(tk))
        else:
            raise PolicyTransformationException(
                f"OOOFragmentConverter: unknown connective {op!r}")


def _collect_free(node, bound: frozenset, acc: List[str]):
    kind = node[0]
    if kind == "pred":
        for term in node[2]:
            if term[0] == "var" and term[1] not in bound and term[1] not in acc:
                acc.append(term[1])
    elif kind == "eq":
        for term in (node[1], node[2]):
            if term[0] == "var" and term[1] not in bound and term[1] not in acc:
                acc.append(term[1])
    elif kind in ("and", "or"):
        _collect_free(node[1], bound, acc)
        _collect_free(node[2], bound, acc)
    elif kind in ("since", "until"):
        _collect_free(node[1], bound, acc)
        _collect_free(node[3], bound, acc)
    elif kind == "not":
        _collect_free(node[1], bound, acc)
    elif kind == "exists":
        _collect_free(node[2], bound | {node[1]}, acc)
    elif kind in ("once", "eventually", "previous", "next"):
        _collect_free(node[2], bound, acc)
    else:
        raise PolicyTransformationException(f"OOOFragmentConverter: unknown node {kind!r}")


def _natural_key(name: str):
    match = re.match(r"([A-Za-z_]+)(\d*)$", name)
    if match is None:
        return (name, 0)
    return (match.group(1), int(match.group(2) or 0))


class _Emitter:
    def __init__(self, free_index: Dict[str, int]):
        self.free_index = free_index

    def var_idx(self, name: str, env: List[str]) -> int:
        if name in env:
            return env.index(name)
        if name in self.free_index:
            return len(env) + self.free_index[name]
        raise PolicyTransformationException(f"OOOFragmentConverter: unbound variable {name!r}")

    def term(self, term, env: List[str]) -> str:
        if term[0] == "const":
            return term[1]
        return f"x{self.var_idx(term[1], env)}"

    def fv(self, node, env: List[str]) -> set:
        kind = node[0]
        if kind == "pred":
            return {self.var_idx(t[1], env) for t in node[2] if t[0] == "var"}
        if kind == "eq":
            return {self.var_idx(t[1], env) for t in (node[1], node[2]) if t[0] == "var"}
        if kind in ("and", "or"):
            return self.fv(node[1], env) | self.fv(node[2], env)
        if kind in ("since", "until"):
            return self.fv(node[1], env) | self.fv(node[3], env)
        if kind == "not":
            return self.fv(node[1], env)
        if kind == "exists":
            inner = self.fv(node[2], [node[1]] + env)
            return {i - 1 for i in inner if i >= 1}
        if kind in ("once", "eventually", "previous", "next"):
            return self.fv(node[2], env)
        raise PolicyTransformationException(f"OOOFragmentConverter: unknown node {kind!r}")

    def interval(self, interval) -> str:
        low, high = interval
        return f"[{low},{'*' if high is None else high}]"

    def emit(self, node, env: List[str]) -> str:
        kind = node[0]
        if kind == "pred":
            args = " ".join(self.term(t, env) for t in node[2])
            return f"(PRED {node[1]} {args})" if args else f"(PRED {node[1]})"
        if kind == "eq":
            return f"(EQ {self.term(node[1], env)} {self.term(node[2], env)})"
        if kind == "or":
            return f"(UNION {self.emit(node[1], env)} {self.emit(node[2], env)})"
        if kind == "exists":
            return f"(EXISTS {self.emit(node[2], [node[1]] + env)})"
        if kind == "previous":
            return f"(PREV {self.interval(node[1])} {self.emit(node[2], env)})"
        if kind == "next":
            return f"(NEXT {self.interval(node[1])} {self.emit(node[2], env)})"
        if kind == "once":
            return f"(SINCE {TRUE_LEFT} {self.interval(node[1])} {self.emit(node[2], env)})"
        if kind == "eventually":
            return f"(UNTIL {TRUE_LEFT} {self.interval(node[1])} {self.emit(node[2], env)})"
        if kind in ("since", "until"):
            left, interval, right = node[1], node[2], node[3]
            op = "SINCE" if kind == "since" else "UNTIL"
            if left[0] == "not":
                op = "NEG" + op
                left = left[1]
            return f"({op} {self.emit(left, env)} {self.interval(interval)} {self.emit(right, env)})"
        if kind == "and":
            return self.emit_and(node[1], node[2], env)
        if kind == "not":
            raise PolicyTransformationException(
                "OOOFragmentConverter: unguarded NOT (only AND NOT, NOT-eq conjuncts "
                "and NOT on the left of SINCE/UNTIL are in the fragment)")
        raise PolicyTransformationException(f"OOOFragmentConverter: unknown node {kind!r}")

    def emit_and(self, left, right, env: List[str]) -> str:
        def eq_of(n):
            if n[0] == "eq":
                return n, False
            if n[0] == "not" and n[1][0] == "eq":
                return n[1], True
            return None, None

        right_eq, right_neg = eq_of(right)
        left_eq, left_neg = eq_of(left)
        if right_eq is not None and left_eq is None:
            return self.emit_eq_conjunct(left, right_eq, right_neg, env)
        if left_eq is not None and right_eq is None:
            return self.emit_eq_conjunct(right, left_eq, left_neg, env)
        if right[0] == "not":
            return f"(ANTIJOIN {self.emit(left, env)} {self.emit(right[1], env)})"
        if left[0] == "not":
            return f"(ANTIJOIN {self.emit(right, env)} {self.emit(left[1], env)})"
        return f"(JOIN {self.emit(left, env)} {self.emit(right, env)})"

    def emit_eq_conjunct(self, plan, eq_node, negated, env: List[str]) -> str:
        plan_fv = self.fv(plan, env)
        plan_str = self.emit(plan, env)
        t1, t2 = eq_node[1], eq_node[2]

        def new_var(term):
            return (term[0] == "var" and self.var_idx(term[1], env) not in plan_fv)

        def grounded(term):
            return term[0] == "const" or self.var_idx(term[1], env) in plan_fv

        if new_var(t1) and grounded(t2):
            fresh, known = t1, t2
        elif new_var(t2) and grounded(t1):
            fresh, known = t2, t1
        else:
            fresh = None
        if fresh is not None:
            if negated:
                raise PolicyTransformationException(
                    "OOOFragmentConverter: negated equality on a fresh variable is unsafe")
            return f"(EXTENDEQ {plan_str} {self.var_idx(fresh[1], env)} {self.term(known, env)})"
        if all(t[0] == "const" or self.var_idx(t[1], env) in plan_fv for t in (t1, t2)):
            flag = "true" if negated else "false"
            return f"(FILTEREQ {plan_str} {flag} {self.term(t1, env)} {self.term(t2, env)})"
        raise PolicyTransformationException(
            "OOOFragmentConverter: equality conjunct relates variables outside the plan")


def convert_mfotl_to_fragment(text: str) -> str:
    tokens = _Tokens(text.strip())
    ast = _parse_formula(tokens)
    if tokens.peek() is not None:
        raise PolicyTransformationException(
            f"OOOFragmentConverter: trailing tokens after policy: {tokens.peek()!r}")
    free: List[str] = []
    _collect_free(ast, frozenset(), free)
    free_index = {name: i for i, name in enumerate(sorted(free, key=_natural_key))}
    return _Emitter(free_index).emit(ast, [])


class OOOFragmentConverter(PolicyConverterTemplate):
    def __init__(self, name, path_to_project):
        pass

    def auto_convert(self, path_to_folder: str, input_file: str, path_to_output_folder: str, output_file: str,
                     source: InputOutputPolicyFormats, target: InputOutputPolicyFormats, params: Dict[str, Any]):
        if source != InputOutputPolicyFormats.MFOTL or target != InputOutputPolicyFormats.OOO_FRAGMENT:
            raise PolicyTransformationException(
                f"OOOFragmentConverter: incompatible conversion from {source} to {target}")
        with open(f"{path_to_folder}/{input_file}", "r") as f:
            policy = f.read()
        converted = convert_mfotl_to_fragment(policy)
        with open(f"{path_to_output_folder}/{output_file}", "w") as f:
            f.write(converted + "\n")

    @staticmethod
    def conversion_scheme() -> List[Tuple[InputOutputPolicyFormats, InputOutputPolicyFormats]]:
        return [(InputOutputPolicyFormats.MFOTL, InputOutputPolicyFormats.OOO_FRAGMENT)]
