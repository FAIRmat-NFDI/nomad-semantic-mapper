#!/usr/bin/env python3
"""Compile OntologyMap([...]) declarations into Owlready2 Python or Turtle.

Contract
--------
The Python side contributes exactly one thing: a *name*. For ``class DIDSample(Section)``
that name is ``DIDSample``; for ``system = OntologyMap([...])(Quantity(...))`` it is
``system``. That name is a local handle used to cross-reference declarations inside
this file. It is not the entity, it is not the IRI, and it says nothing about what
kind of OWL entity is being declared.

Everything semantic comes from the OntologyMap list, and every declaration carries a
mandatory ``iri=``. Being a Python class does not make something an owl:Class; being
a ``Quantity`` does not make something a property. ``Class(iri=...)`` does, and only
that. The base class (``Section``, ``MSection``, anything) is never read.

    @OntologyMap([
        Class(iri='https://nomad-lab.eu/onto/did#DIDSample'),
        SubClassOf(iri='http://purl.obolibrary.org/obo/BFO_0000030'),
    ])
    class DIDSample(Section):

        system = OntologyMap([
            ObjectProperty(iri='https://nomad-lab.eu/onto/did#hasSystem'),
            Domain(iri='DIDSample'),
            Range(iri='https://nomad-lab.eu/onto/nomad#System'),
        ])(Quantity(type=System.m_def))

Internal vs external grammar
----------------------------
``Quantity``, ``SubSection``, ``DataFrame``, ``type``, ``unit`` and ``shape`` are
NOMAD's internal grammar. This compiler does not interpret any of it -- it only
records the wrapped expression as a comment in the generated file. The eventual
``Quantity -> HasQuantity``-style hardcoded layer plugs in at that point; for now the
mapping is one-to-one:

    Quantity(...)  ->  <handle>  ->  user-declared external grammar
                       ^^^^^^^^      (this is all the compiler emits today)

External IRIs are taken on trust. A wrong, unreachable or misspelled IRI is emitted
as written. Checking that external grammar is consistent belongs to a later
``reasoner_validator.py``, not here.

The public mapping language is fully declarative and never accepts arbitrary Python
blocks. Owlready2 is wrapped as an implementation detail.
See ``README.md`` for the supported OWL 2 surface and its explicit limits.

References
----------
Every reference is a string: either a handle declared in this file, or an IRI. An IRI
that matches a local declaration resolves to that declaration, so the two forms are
interchangeable and nothing depends on Python binding order.

Pipeline:  schemas.py (NOMAD) -> this compiler -> ontology.py (Owlready2) -> .ttl
This single file also supplies the inert OntologyMap decorator and operation names
that an ordinary NOMAD module imports at runtime.

Usage:
    python nomad_semantic_mapper.py schemas.py ontology.py  --to py
    python nomad_semantic_mapper.py schemas.py ontology.ttl --to ttl

Turtle output requires: python -m pip install owlready2 rdflib
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# --------------------------------------------------------------------------------
# Operation surface. Every operation is keyword-only; every declaration needs an iri.
# --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Signature:
    required: frozenset[str]
    optional: frozenset[str] = frozenset()
    one_of: frozenset[str] = frozenset()  # exactly one of these must be given

    @property
    def keys(self) -> frozenset[str]:
        return self.required | self.optional | self.one_of


def signature(required: str, optional: str = "", one_of: str = "") -> Signature:
    return Signature(
        frozenset(required.split()),
        frozenset(optional.split()) if optional else frozenset(),
        frozenset(one_of.split()) if one_of else frozenset(),
    )


DECLARATIONS: dict[str, Signature] = {
    "Class": signature("iri", "parents"),
    "Individual": signature("iri type"),
    "ObjectProperty": signature("iri", "characteristics domain range"),
    "DataProperty": signature("iri", "characteristics domain range"),
    "AnnotationProperty": signature("iri"),
}

RESTRICTIONS = {
    "SomeValuesFrom": "some",
    "AllValuesFrom": "only",
    "MinCardinality": "min",
    "MaxCardinality": "max",
    "ExactCardinality": "exactly",
    "HasValue": "value",
    "HasSelf": "has_self",
}

AXIOMS: dict[str, Signature] = {
    "SubClassOf": signature("", one_of="iri expression"),
    "EquivalentTo": signature("", one_of="iri expression"),
    "DisjointWith": signature("", one_of="iri expression"),
    "SubPropertyOf": signature("iri"),
    "InverseOf": signature("iri"),
    "Domain": signature("iri"),
    "Range": signature("iri"),
    "SameAs": signature("iri"),
    "DifferentFrom": signature("iri"),
    "AllDifferent": signature("individuals"),
    "AllDisjoint": signature("entities"),
    "Type": signature("", one_of="iri expression"),
    "PropertyChain": signature("properties"),
    "Fact": signature("property", one_of="value literal"),
    "SomeValuesFrom": signature("property filler", "equivalent"),
    "AllValuesFrom": signature("property filler", "equivalent"),
    "MinCardinality": signature("property count", "filler equivalent"),
    "MaxCardinality": signature("property count", "filler equivalent"),
    "ExactCardinality": signature("property count", "filler equivalent"),
    "HasValue": signature("property", "equivalent", "value literal"),
    "HasSelf": signature("property", "value equivalent"),
}

UNIVERSAL: dict[str, Signature] = {
    "Annotation": signature("property", one_of="value literal"),
}

EXPRESSIONS = {
    "IntersectionOf",
    "UnionOf",
    "ComplementOf",
    "OneOf",
    "Inverse",
    *RESTRICTIONS,
}

SIGNATURES: dict[str, Signature] = {**DECLARATIONS, **AXIOMS, **UNIVERSAL}

# Which axioms each declaration kind accepts. Anything else is rejected at parse time
# rather than silently generating nonsense.
ALLOWED = {
    "Class": {"SubClassOf", "EquivalentTo", "DisjointWith", "AllDisjoint"}
    | set(RESTRICTIONS),
    "Individual": {"SameAs", "DifferentFrom", "AllDifferent", "Type", "Fact"},
    "ObjectProperty": {
        "SubPropertyOf",
        "EquivalentTo",
        "DisjointWith",
        "InverseOf",
        "Domain",
        "Range",
        "PropertyChain",
        "AllDisjoint",
    },
    "DataProperty": {
        "SubPropertyOf", "EquivalentTo", "DisjointWith", "Domain", "Range", "AllDisjoint"
    },
    "AnnotationProperty": {"SubPropertyOf", "Domain", "Range"},
}

PROPERTY_KINDS = {"ObjectProperty", "DataProperty", "AnnotationProperty"}
DATA_KINDS = {"DataProperty", "AnnotationProperty"}

CHARACTERISTICS = {
    "FunctionalProperty",
    "InverseFunctionalProperty",
    "TransitiveProperty",
    "SymmetricProperty",
    "AsymmetricProperty",
    "ReflexiveProperty",
    "IrreflexiveProperty",
}

# Owlready2 exposes these as attributes on every entity.
BUILTIN_ANNOTATIONS = {
    "label",
    "comment",
    "seeAlso",
    "isDefinedBy",
    "versionInfo",
    "deprecated",
    "backwardCompatibleWith",
    "incompatibleWith",
    "priorVersion",
}


class MappingError(ValueError):
    """Anything wrong in the schema file. Always carries file:line."""


# --------------------------------------------------------------------------------
# Parsed model
# --------------------------------------------------------------------------------


@dataclass
class Operation:
    name: str
    kwargs: dict[str, ast.AST]
    line: int

    def get(self, key: str) -> ast.AST | None:
        return self.kwargs.get(key)


@dataclass
class Entity:
    handle: str  # qualified local handle, e.g. "DIDSample.system"
    owner: str | None  # enclosing handle scope
    iri: str  # identity, taken verbatim from the declaration
    var: str  # identifier used in the generated Python
    operations: list[Operation]
    line: int
    origin: str  # wrapped NOMAD expression, emitted as a comment only

    @property
    def declaration(self) -> Operation:
        return next(op for op in self.operations if op.name in DECLARATIONS)

    @property
    def kind(self) -> str:
        return self.declaration.name

    @property
    def scope(self) -> str:
        """Where handle lookups start: this entity, then each enclosing scope."""
        return self.handle


def identifier(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]", "_", value).strip("_") or "Entity"
    return f"N_{value}" if value[0].isdigit() else value


def split_iri(iri: str) -> tuple[str, str]:
    """Namespace/fragment split, matching the runtime helper. Deliberately forgiving."""
    base, _, fragment = iri.partition("#")
    if fragment:
        return base + "#", fragment
    head, separator, tail = iri.rpartition("/")
    if separator and tail:
        return head + separator, tail
    head, separator, tail = iri.rpartition(":")
    if separator and tail:
        return head + separator, tail
    return "", iri


# --------------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------------


def parse_schema(path: Path) -> list[Entity]:
    """Read OntologyMap decorators/wrappers. The wrapped Python is never evaluated."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    entities: list[Entity] = []
    by_handle: dict[str, Entity] = {}
    by_iri: dict[str, Entity] = {}
    used_vars: set[str] = set()

    def fail(line: int, message: str) -> MappingError:
        return MappingError(f"{path}:{line}: {message}")

    def final_name(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return ""

    def literal_str(node: ast.AST, line: int, what: str) -> str:
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            raise fail(line, f"{what} must be a string literal")
        return node.value

    def read_operations(call: ast.Call) -> list[Operation]:
        if len(call.args) != 1 or not isinstance(call.args[0], (ast.List, ast.Tuple)):
            raise fail(call.lineno, "OntologyMap takes exactly one literal list")
        if call.keywords:
            raise fail(call.lineno, "OntologyMap takes no keyword arguments")

        operations: list[Operation] = []
        for item in call.args[0].elts:
            if not isinstance(item, ast.Call):
                raise fail(item.lineno, "each OntologyMap item must be an operation call")
            name = final_name(item.func)
            if name not in SIGNATURES:
                raise fail(
                    item.lineno,
                    f"unknown operation {name!r}; mappings accept named operations only",
                )
            sig = SIGNATURES[name]
            if item.args:
                raise fail(
                    item.lineno,
                    f"{name} takes keyword arguments only; "
                    f"expected {name}({', '.join(sorted(sig.required))}=...)",
                )
            kwargs: dict[str, ast.AST] = {}
            for keyword in item.keywords:
                if keyword.arg is None:
                    raise fail(item.lineno, f"{name} does not accept **kwargs")
                if keyword.arg not in sig.keys:
                    raise fail(
                        item.lineno,
                        f"{name} has no keyword {keyword.arg!r}; "
                        f"accepted: {', '.join(sorted(sig.keys))}",
                    )
                kwargs[keyword.arg] = keyword.value
            missing = sig.required - kwargs.keys()
            if missing:
                raise fail(item.lineno, f"{name} is missing {', '.join(sorted(missing))}=")
            if sig.one_of:
                given = sig.one_of & kwargs.keys()
                if len(given) != 1:
                    options = " or ".join(f"{key}=" for key in sorted(sig.one_of))
                    raise fail(item.lineno, f"{name} needs exactly one of {options}")
            operations.append(Operation(name, kwargs, item.lineno))
        return operations

    def unique_var(handle: str) -> str:
        base = identifier(handle)
        candidate, suffix = base, 2
        while candidate in used_vars:
            candidate, suffix = f"{base}_{suffix}", suffix + 1
        used_vars.add(candidate)
        return candidate

    def add_entity(
        handle: str, owner: str | None, operations: list[Operation], line: int, origin: str
    ) -> None:
        declarations = [op for op in operations if op.name in DECLARATIONS]
        if len(declarations) != 1:
            raise fail(
                line,
                f"{handle} needs exactly one declaration ({', '.join(sorted(DECLARATIONS))})",
            )
        declaration = declarations[0]
        kind = declaration.name

        for op in operations:
            if op.name in DECLARATIONS or op.name in UNIVERSAL:
                continue
            if op.name not in ALLOWED[kind]:
                raise fail(op.line, f"{op.name} is not valid on a {kind}")

        iri = literal_str(declaration.kwargs["iri"], declaration.line, "iri=")
        if ":" not in iri:
            raise fail(declaration.line, f"iri={iri!r} is not an IRI (needs a scheme or prefix)")

        if handle in by_handle:
            raise fail(
                line, f"duplicate handle {handle} (first used at line {by_handle[handle].line})"
            )
        if iri in by_iri:
            raise fail(
                declaration.line,
                f"iri={iri!r} is already declared by {by_iri[iri].handle} "
                f"at line {by_iri[iri].line}",
            )

        entity = Entity(handle, owner, iri, unique_var(handle), operations, line, origin)
        by_handle[handle] = entity
        by_iri[iri] = entity
        entities.append(entity)

    def decorator_of(node: ast.ClassDef) -> ast.Call | None:
        found = [
            item
            for item in node.decorator_list
            if isinstance(item, ast.Call) and final_name(item.func) == "OntologyMap"
        ]
        if len(found) > 1:
            raise fail(node.lineno, f"{node.name} has more than one @OntologyMap decorator")
        return found[0] if found else None

    def wrapper_of(node: ast.AST) -> tuple[str, ast.Call, ast.AST | None] | None:
        """Match  name = OntologyMap([...])(<wrapped>)  in either assignment form."""
        if isinstance(node, ast.Assign):
            target = node.targets[0] if len(node.targets) == 1 else None
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        else:
            return None
        if not isinstance(target, ast.Name) or not isinstance(value, ast.Call):
            return None
        outer = value.func
        if not isinstance(outer, ast.Call) or final_name(outer.func) != "OntologyMap":
            return None
        return target.id, outer, (value.args[0] if value.args else None)

    def visit(body: list[ast.stmt], owner: str | None) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                handle = f"{owner}.{node.name}" if owner else node.name
                decorator = decorator_of(node)
                if decorator is not None:
                    add_entity(
                        handle,
                        owner,
                        read_operations(decorator),
                        node.lineno,
                        f"class {node.name}",
                    )
                visit(node.body, handle)
                continue

            match = wrapper_of(node)
            if match is not None:
                name, outer, wrapped = match
                handle = f"{owner}.{name}" if owner else name
                origin = ast.unparse(wrapped) if wrapped is not None else ""
                add_entity(handle, owner, read_operations(outer), node.lineno, origin)
                continue

            for attribute in ("body", "orelse", "finalbody"):
                nested = getattr(node, attribute, None)
                if isinstance(nested, list) and nested and isinstance(nested[0], ast.stmt):
                    visit(nested, owner)

    visit(tree.body, None)
    if not entities:
        raise MappingError(f"No OntologyMap declarations found in {path}")
    return entities


# --------------------------------------------------------------------------------
# Reference resolution
# --------------------------------------------------------------------------------


class Resolver:
    """Turns reference strings into generated-Python expressions.

    A reference is a local handle or an IRI. IRIs matching a local declaration
    resolve to it; everything else becomes an ``_external`` handle, trusted verbatim.
    """

    def __init__(self, entities: list[Entity], path: Path) -> None:
        self.by_handle = {entity.handle: entity for entity in entities}
        self.by_iri = {entity.iri: entity for entity in entities}
        self.path = path
        # Owlready2 refuses to create an ontology inside `with onto:`, so external
        # namespaces are materialised in a prelude, recorded here in first-seen order.
        self.externals: dict[str, str] = {}
        self.external_kinds: dict[str, set[str]] = {}

    def fail(self, line: int, message: str) -> MappingError:
        return MappingError(f"{self.path}:{line}: {message}")

    def text(self, node: ast.AST | None, line: int, what: str) -> str:
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            raise self.fail(line, f"{what} must be a string literal (a handle or an IRI)")
        return node.value

    def items(self, node: ast.AST | None, line: int, what: str) -> list[str]:
        if node is None:
            return []
        if isinstance(node, (ast.List, ast.Tuple)):
            return [self.text(item, line, what) for item in node.elts]
        return [self.text(node, line, what)]

    def entity(self, reference: str, owner: str | None) -> Entity | None:
        if reference in self.by_iri:
            return self.by_iri[reference]
        scope = owner
        while scope:
            candidate = f"{scope}.{reference}"
            if candidate in self.by_handle:
                return self.by_handle[candidate]
            scope = scope.rpartition(".")[0] or None
        return self.by_handle.get(reference)

    def ref(self, reference: str, owner: str | None, line: int, parent: str = "Thing") -> str:
        target = self.entity(reference, owner)
        if target is not None:
            return target.var
        if ":" not in reference:
            raise self.fail(
                line,
                f"{reference!r} is not a handle declared in this file, and is not an IRI "
                "(an IRI needs a scheme or prefix)",
            )
        expression = f"_external({reference!r}, {parent})"
        self.externals.setdefault(reference, expression)
        self.external_kinds.setdefault(reference, set()).add(parent)
        return expression

    def individual_ref(self, reference: str, owner: str | None, line: int) -> str:
        target = self.entity(reference, owner)
        if target is not None:
            return target.var
        if ":" not in reference:
            raise self.fail(line, f"{reference!r} is not a declared handle or an IRI")
        expression = f"_external_individual({reference!r})"
        self.externals.setdefault(reference, expression)
        self.external_kinds.setdefault(reference, set()).add("Individual")
        return expression

    def datatype_ref(self, reference: str, line: int) -> str:
        if ":" not in reference:
            raise self.fail(line, f"datatype {reference!r} must be an IRI, e.g. 'xsd:string'")
        expression = f"_datatype({reference!r})"
        self.externals.setdefault(reference, expression)
        self.external_kinds.setdefault(reference, set()).add("Datatype")
        return expression


# --------------------------------------------------------------------------------
# Code generation
# --------------------------------------------------------------------------------


def literal(node: ast.AST | None) -> str:
    return "None" if node is None else ast.unparse(node)


def comment_for(entity: Entity) -> str:
    return f"  # {entity.handle}" + (f" <- {entity.origin}" if entity.origin else "")


def declaration_lines(entity: Entity, resolver: Resolver) -> list[str]:
    """Bring the entity into existence. Axioms come later, once everything exists."""
    op = entity.declaration
    _, fragment = split_iri(entity.iri)

    if op.name == "Class":
        bases = "Thing,"
    else:
        characteristics = resolver.items(op.get("characteristics"), op.line, "characteristics=")
        for item in characteristics:
            if item not in CHARACTERISTICS:
                raise resolver.fail(
                    op.line,
                    f"unknown characteristic {item!r}; "
                    f"accepted: {', '.join(sorted(CHARACTERISTICS))}",
                )
        bases = ", ".join([op.name, *characteristics]) + ("" if characteristics else ",")
    return [f"{entity.var} = types.new_class({fragment!r}, ({bases}))" + comment_for(entity)]


def individual_lines(entity: Entity, resolver: Resolver) -> list[str]:
    op = entity.declaration
    _, fragment = split_iri(entity.iri)
    reference = resolver.text(op.get("type"), op.line, "type=")
    owl_class = resolver.ref(reference, entity.scope, op.line)
    return [f"{entity.var} = {owl_class}({fragment!r})" + comment_for(entity)]


def slot_lines(entity: Entity, resolver: Resolver, slot: str, references: list[str], line: int) -> list[str]:
    """Domain and range always append, so declaration keywords and axioms compose."""
    lines: list[str] = []
    for reference in references:
        if slot == "range" and entity.kind in DATA_KINDS:
            value = resolver.datatype_ref(reference, line)
        else:
            value = resolver.ref(reference, entity.scope, line)
        lines.append(f"{entity.var}.{slot}.append({value})")
    return lines


def declaration_axioms(entity: Entity, resolver: Resolver) -> list[str]:
    """Axioms carried as keywords on the declaration itself."""
    op = entity.declaration
    lines: list[str] = []
    if entity.kind == "Class":
        for parent in resolver.items(op.get("parents"), op.line, "parents="):
            lines.append(f"{entity.var}.is_a.append({resolver.ref(parent, entity.scope, op.line)})")
    if entity.kind in PROPERTY_KINDS:
        for slot in ("domain", "range"):
            references = resolver.items(op.get(slot), op.line, f"{slot}=")
            lines.extend(slot_lines(entity, resolver, slot, references, op.line))
    return lines


def object_or_literal(op: Operation, resolver: Resolver, scope: str) -> str:
    """value= is a reference (handle or IRI); literal= is a plain Python literal."""
    if op.get("literal") is not None:
        return literal(op.get("literal"))
    reference = resolver.text(op.get("value"), op.line, "value=")
    return resolver.individual_ref(reference, scope, op.line)


def annotation_lines(entity: Entity, op: Operation, resolver: Resolver) -> list[str]:
    predicate = resolver.text(op.get("property"), op.line, "property=")
    value = object_or_literal(op, resolver, entity.scope)
    target = resolver.entity(predicate, entity.scope)
    if target is not None:
        return [f"{target.var}[{entity.var}].append({value})"]
    if ":" in predicate:
        handle = resolver.ref(predicate, entity.scope, op.line, parent="AnnotationProperty")
        return [f"{handle}[{entity.var}].append({value})"]
    if predicate in BUILTIN_ANNOTATIONS:
        return [f"{entity.var}.{predicate}.append({value})"]
    raise resolver.fail(
        op.line,
        f"annotation property {predicate!r} is neither declared here, an IRI, "
        f"nor an Owlready2 builtin ({', '.join(sorted(BUILTIN_ANNOTATIONS))})",
    )


def _call_kwargs(node: ast.Call, resolver: Resolver, allowed: set[str]) -> dict[str, ast.AST]:
    if node.args:
        raise resolver.fail(node.lineno, "nested expressions take keyword arguments only")
    kwargs: dict[str, ast.AST] = {}
    for keyword in node.keywords:
        if keyword.arg is None or keyword.arg not in allowed:
            raise resolver.fail(node.lineno, "invalid keyword in nested OWL expression")
        kwargs[keyword.arg] = keyword.value
    return kwargs


def _nodes(node: ast.AST | None, resolver: Resolver, line: int, what: str) -> list[ast.AST]:
    if not isinstance(node, (ast.List, ast.Tuple)):
        raise resolver.fail(line, f"{what} must be a literal list")
    return list(node.elts)


def property_expression(
    node: ast.AST | None, resolver: Resolver, owner: str, line: int, data: bool = False
) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return resolver.ref(node.value, owner, line, "DataProperty" if data else "ObjectProperty")
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Inverse":
        kwargs = _call_kwargs(node, resolver, {"property"})
        if "property" not in kwargs:
            raise resolver.fail(node.lineno, "Inverse is missing property=")
        return f"Inverse({property_expression(kwargs['property'], resolver, owner, line)})"
    raise resolver.fail(line, "property= must be an IRI/handle or Inverse(property=...)")


def class_expression(node: ast.AST | None, resolver: Resolver, owner: str, line: int) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return resolver.ref(node.value, owner, line)
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
        raise resolver.fail(line, "expression must be a named OWL expression")
    name = node.func.id
    if name not in EXPRESSIONS:
        raise resolver.fail(node.lineno, f"unknown class expression {name!r}")

    if name in {"IntersectionOf", "UnionOf"}:
        kwargs = _call_kwargs(node, resolver, {"operands"})
        operands = _nodes(kwargs.get("operands"), resolver, node.lineno, "operands=")
        if len(operands) < 2:
            raise resolver.fail(node.lineno, f"{name} needs at least two operands")
        operator = " & " if name == "IntersectionOf" else " | "
        return "(" + operator.join(
            class_expression(item, resolver, owner, node.lineno) for item in operands
        ) + ")"

    if name == "ComplementOf":
        kwargs = _call_kwargs(node, resolver, {"operand"})
        if "operand" not in kwargs:
            raise resolver.fail(node.lineno, "ComplementOf is missing operand=")
        return f"Not({class_expression(kwargs['operand'], resolver, owner, node.lineno)})"

    if name == "OneOf":
        kwargs = _call_kwargs(node, resolver, {"individuals"})
        values = _nodes(kwargs.get("individuals"), resolver, node.lineno, "individuals=")
        if not values:
            raise resolver.fail(node.lineno, "OneOf needs at least one individual")
        rendered = []
        for value in values:
            reference = resolver.text(value, node.lineno, "individual")
            rendered.append(resolver.individual_ref(reference, owner, node.lineno))
        return f"OneOf([{', '.join(rendered)}])"

    if name == "Inverse":
        raise resolver.fail(node.lineno, "Inverse is a property expression, not a class expression")

    signature = AXIOMS[name]
    kwargs = _call_kwargs(node, resolver, set(signature.keys))
    if "equivalent" in kwargs:
        raise resolver.fail(
            node.lineno,
            "equivalent= is only valid for a restriction placed directly in OntologyMap",
        )
    missing = signature.required - kwargs.keys()
    if missing:
        raise resolver.fail(node.lineno, f"{name} is missing {', '.join(sorted(missing))}=")
    if signature.one_of and len(signature.one_of & kwargs.keys()) != 1:
        raise resolver.fail(node.lineno, f"{name} needs exactly one value= or literal=")
    return restriction_expression(Operation(name, kwargs, node.lineno), resolver, owner)


def restriction_expression(op: Operation, resolver: Resolver, owner: str) -> str:
    line = op.line
    method = RESTRICTIONS[op.name]

    property_node = op.get("property")
    reference = (
        property_node.value
        if isinstance(property_node, ast.Constant) and isinstance(property_node.value, str)
        else ""
    )
    prop_entity = resolver.entity(reference, owner) if reference else None
    data = prop_entity is not None and prop_entity.kind in DATA_KINDS
    prop = property_expression(property_node, resolver, owner, line, data)

    if op.name == "HasValue":
        arguments = object_or_literal(op, resolver, owner)
    elif op.name == "HasSelf":
        arguments = literal(op.get("value")) if op.get("value") is not None else "True"
    elif "Cardinality" in op.name:
        parts = [literal(op.get("count"))]
        filler = op.get("filler")
        if filler is not None:
            if data:
                parts.append(
                    resolver.datatype_ref(resolver.text(filler, line, "filler="), line)
                )
            else:
                parts.append(class_expression(filler, resolver, owner, line))
        arguments = ", ".join(parts)
    else:
        filler = op.get("filler")
        if data:
            arguments = resolver.datatype_ref(resolver.text(filler, line, "filler="), line)
        else:
            arguments = class_expression(filler, resolver, owner, line)

    return f"{prop}.{method}({arguments})"


def restriction_lines(entity: Entity, op: Operation, resolver: Resolver) -> list[str]:
    line = op.line
    expression = restriction_expression(op, resolver, entity.scope)

    equivalent_node = op.get("equivalent")
    try:
        equivalent = (
            bool(ast.literal_eval(equivalent_node)) if equivalent_node is not None else False
        )
    except ValueError as exc:
        raise resolver.fail(line, f"equivalent= must be a literal: {exc}") from exc

    slot = "equivalent_to" if equivalent else "is_a"
    return [f"{entity.var}.{slot}.append({expression})"]


def operation_lines(entity: Entity, op: Operation, resolver: Resolver) -> list[str]:
    if op.name in DECLARATIONS:
        return []

    var, owner, line = entity.var, entity.scope, op.line

    def target(parent: str = "Thing") -> str:
        return resolver.ref(resolver.text(op.get("iri"), line, "iri="), owner, line, parent)

    peer = "Thing" if entity.kind == "Class" else entity.kind

    if op.name == "Annotation":
        return annotation_lines(entity, op, resolver)

    if op.name == "SubClassOf":
        value = (
            class_expression(op.get("expression"), resolver, owner, line)
            if op.get("expression") is not None
            else target()
        )
        return [f"{var}.is_a.append({value})"]

    if op.name == "SubPropertyOf":
        return [f"{var}.is_a.append({target(entity.kind)})"]

    if op.name == "EquivalentTo":
        if op.get("expression") is not None:
            if entity.kind != "Class":
                raise resolver.fail(line, "expression= on EquivalentTo is valid only for Class")
            value = class_expression(op.get("expression"), resolver, owner, line)
        else:
            value = target(peer)
        return [f"{var}.equivalent_to.append({value})"]

    if op.name == "DisjointWith":
        value = (
            class_expression(op.get("expression"), resolver, owner, line)
            if op.get("expression") is not None and entity.kind == "Class"
            else target(peer)
        )
        return [f"AllDisjoint([{var}, {value}])"]

    if op.name == "AllDisjoint":
        references = resolver.items(op.get("entities"), line, "entities=")
        if not references:
            raise resolver.fail(line, "AllDisjoint needs at least one additional entity")
        values = [var, *(resolver.ref(item, owner, line, peer) for item in references)]
        return [f"AllDisjoint([{', '.join(values)}])"]

    if op.name == "SameAs":
        # Owlready2 maps equivalent_to on an individual to owl:sameAs.
        reference = resolver.text(op.get("iri"), line, "iri=")
        return [f"{var}.equivalent_to.append({resolver.individual_ref(reference, owner, line)})"]

    if op.name == "DifferentFrom":
        reference = resolver.text(op.get("iri"), line, "iri=")
        other = resolver.individual_ref(reference, owner, line)
        return [f"AllDifferent([{var}, {other}])"]

    if op.name == "AllDifferent":
        references = resolver.items(op.get("individuals"), line, "individuals=")
        if not references:
            raise resolver.fail(line, "AllDifferent needs at least one additional individual")
        values = [var, *(resolver.individual_ref(item, owner, line) for item in references)]
        return [f"AllDifferent([{', '.join(values)}])"]

    if op.name == "Type":
        value = (
            class_expression(op.get("expression"), resolver, owner, line)
            if op.get("expression") is not None
            else target()
        )
        return [f"{var}.is_a.append({value})"]

    if op.name == "InverseOf":
        return [f"{var}.inverse_property = {target('ObjectProperty')}"]

    if op.name in {"Domain", "Range"}:
        reference = resolver.text(op.get("iri"), line, "iri=")
        return slot_lines(entity, resolver, op.name.lower(), [reference], line)

    if op.name == "PropertyChain":
        references = resolver.items(op.get("properties"), line, "properties=")
        if len(references) < 2:
            raise resolver.fail(line, "PropertyChain needs at least two properties")
        values = ", ".join(resolver.ref(item, owner, line, "ObjectProperty") for item in references)
        return [f"{var}.property_chain.append(PropertyChain([{values}]))"]

    if op.name in RESTRICTIONS:
        return restriction_lines(entity, op, resolver)

    if op.name == "Fact":
        reference = resolver.text(op.get("property"), line, "property=")
        data = op.get("literal") is not None
        prop = resolver.ref(reference, owner, line, "DataProperty" if data else "ObjectProperty")
        return [f"{prop}[{var}].append({object_or_literal(op, resolver, owner)})"]

    raise AssertionError(op.name)


# --------------------------------------------------------------------------------
# Generated module template
# --------------------------------------------------------------------------------

TEMPLATE = '''\
"""Generated Owlready2 ontology code from __SOURCE__.

Do not edit; regenerate with nomad_semantic_mapper.py.

Every entity carries the IRI its schema declaration gave it. Nothing here reflects
the Python classes the schema was written with. External IRIs appear exactly as the
author wrote them; nothing checks that they resolve or that the result is consistent.
"""

import datetime
import io
import types
from pathlib import Path

from owlready2 import *

BASE_IRI = __BASE_IRI__

world = World()
ontology = world.get_ontology(BASE_IRI)

_external_cache = {}

_DATATYPES = {
    "xsd:string": str,
    "xsd:normalizedString": str,
    "xsd:anyURI": str,
    "xsd:integer": int,
    "xsd:int": int,
    "xsd:long": int,
    "xsd:nonNegativeInteger": int,
    "xsd:positiveInteger": int,
    "xsd:float": float,
    "xsd:double": float,
    "xsd:decimal": float,
    "xsd:boolean": bool,
    "xsd:date": datetime.date,
    "xsd:dateTime": datetime.datetime,
    "xsd:time": datetime.time,
}
_DATATYPES.update(
    {"http://www.w3.org/2001/XMLSchema#" + key.split(":", 1)[1]: value
     for key, value in list(_DATATYPES.items())}
)


def _split_iri(iri):
    """Namespace/fragment split. Deliberately forgiving; IRIs are trusted."""
    base, _, fragment = iri.partition("#")
    if fragment:
        return base + "#", fragment
    head, separator, tail = iri.rpartition("/")
    if separator and tail:
        return head + separator, tail
    head, separator, tail = iri.rpartition(":")
    if separator and tail:
        return head + separator, tail
    return BASE_IRI, iri


def _external(iri, parent=Thing):
    """Handle for an entity defined elsewhere. The IRI is taken on trust."""
    if iri in _external_cache:
        return _external_cache[iri]
    existing = world[iri]
    if existing is None:
        base, fragment = _split_iri(iri)
        namespace = world.get_ontology(base).get_namespace(base)
        with namespace:
            existing = types.new_class(fragment, (parent,))
    _external_cache[iri] = existing
    return existing


def _external_individual(iri):
    """Handle for an individual defined elsewhere. The IRI is taken on trust."""
    if iri in _external_cache:
        return _external_cache[iri]
    existing = world[iri]
    if existing is None:
        base, fragment = _split_iri(iri)
        namespace = world.get_ontology(base).get_namespace(base)
        existing = Thing(fragment, namespace=namespace)
    _external_cache[iri] = existing
    return existing


def _datatype(iri):
    """Map an XSD IRI to the Python type Owlready2 uses for it."""
    if iri in _DATATYPES:
        return _DATATYPES[iri]
    return _external(iri, Thing)


# --- namespaces ----------------------------------------------------------------
# One per declared IRI namespace. All belong to `ontology`, so a single
# ontology.save() emits every declared entity under the IRI its schema gave it.
__NAMESPACES__

# --- external references -------------------------------------------------------
# Materialised before any `with` block: Owlready2 forbids creating a namespace
# inside `with onto:`.
__EXTERNALS__


# --- declarations --------------------------------------------------------------
__DECLARATIONS__

# --- individuals ---------------------------------------------------------------
__INDIVIDUALS__

# --- axioms --------------------------------------------------------------------
with ontology:
__AXIOMS__


def save_turtle(destination):
    """Serialize this ontology only. External namespaces are referenced, not copied."""
    from rdflib import Graph

    buffer = io.BytesIO()
    ontology.save(file=buffer, format="ntriples")
    buffer.seek(0)
    graph = Graph()
    graph.parse(buffer, format="nt")
    graph.bind("", BASE_IRI)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = graph.serialize(format="turtle")
    destination.write_text(serialized.rstrip() + "\\n", encoding="utf-8")
    return destination


if __name__ == "__main__":
    print(save_turtle(Path(__file__).with_suffix(".ttl")))
'''


def render_python(
    entities: list[Entity], resolver: Resolver, source_name: str, base_iri: str
) -> str:
    namespaces: dict[str, str] = {}

    def namespace_var(iri: str) -> str:
        base, _ = split_iri(iri)
        base = base or base_iri
        if base not in namespaces:
            namespaces[base] = f"_ns{len(namespaces)}"
        return namespaces[base]

    # Declarations and individuals are grouped by namespace; axioms come last so
    # every reference is already bound by the time it is used.
    declarations: dict[str, list[str]] = {}
    individuals: dict[str, list[str]] = {}
    for entity in entities:
        variable = namespace_var(entity.iri)
        if entity.kind == "Individual":
            individuals.setdefault(variable, []).extend(individual_lines(entity, resolver))
        else:
            declarations.setdefault(variable, []).extend(declaration_lines(entity, resolver))

    axioms: list[str] = []
    for entity in entities:
        axioms.extend(declaration_axioms(entity, resolver))
    for entity in entities:
        for operation in entity.operations:
            axioms.extend(operation_lines(entity, operation, resolver))

    def blocks(groups: dict[str, list[str]], empty: str) -> str:
        if not groups:
            return empty
        parts = []
        for variable, lines in groups.items():
            body = "\n".join(f"    {line}" for line in lines)
            parts.append(f"with {variable}:\n{body}")
        return "\n\n".join(parts)

    return (
        TEMPLATE.replace("__SOURCE__", source_name)
        .replace("__BASE_IRI__", repr(base_iri))
        .replace(
            "__NAMESPACES__",
            "\n".join(
                f"{variable} = ontology.get_namespace({base!r})"
                for base, variable in namespaces.items()
            )
            or "pass",
        )
        .replace("__EXTERNALS__", "\n".join(resolver.externals.values()) or "pass")
        .replace("__DECLARATIONS__", blocks(declarations, "# none"))
        .replace("__INDIVIDUALS__", blocks(individuals, "# none"))
        .replace("__AXIOMS__", "\n".join(f"    {line}" for line in axioms) or "    pass")
    )


# --------------------------------------------------------------------------------
# Staged build pipeline
# --------------------------------------------------------------------------------


@dataclass
class StageResult:
    name: str
    status: str
    seconds: float
    details: list[str]
    warnings: list[str]


def _stage(name: str, started: float, details: list[str], warnings: list[str]) -> StageResult:
    status = "warning" if warnings else "passed"
    return StageResult(name, status, time.monotonic() - started, details, warnings)


def _ontology_graph(namespace: dict[str, Any]):
    from rdflib import Graph

    buffer = __import__("io").BytesIO()
    namespace["ontology"].save(file=buffer, format="ntriples")
    buffer.seek(0)
    return Graph().parse(buffer, format="nt")


def _external_namespaces(iris: list[str]) -> list[str]:
    namespaces: list[str] = []
    for iri in iris:
        if not iri.startswith(("http://", "https://")):
            continue
        base, _ = split_iri(iri)
        document = base[:-1] if base.endswith("#") else base
        if document not in namespaces:
            namespaces.append(document)
    return namespaces


def validate_external_vocabularies(
    expected_kinds: dict[str, set[str]], timeout: float
) -> tuple[list[dict[str, Any]], list[str]]:
    """Resolve and parse external vocabularies into isolated temporary RDF graphs."""
    from rdflib import Graph, URIRef
    from rdflib.namespace import OWL, RDF, RDFS

    results: list[dict[str, Any]] = []
    warnings: list[str] = []
    max_bytes = 50 * 1024 * 1024
    accept = "text/turtle, application/rdf+xml, application/n-triples;q=0.8"
    documents = {
        document: [
            iri
            for iri in expected_kinds
            if (split_iri(iri)[0][:-1] if split_iri(iri)[0].endswith("#") else split_iri(iri)[0])
            == document
        ]
        for document in _external_namespaces(list(expected_kinds))
    }
    owl_types = {
        "Thing": {OWL.Class, RDFS.Class},
        "ObjectProperty": {OWL.ObjectProperty},
        "DataProperty": {OWL.DatatypeProperty},
        "AnnotationProperty": {OWL.AnnotationProperty},
        "Datatype": {RDFS.Datatype},
        "Individual": {OWL.NamedIndividual},
    }
    all_entity_types = set().union(*owl_types.values())
    for document, terms in documents.items():
        record: dict[str, Any] = {
            "namespace": document,
            "status": "warning",
            "triples": 0,
            "terms": f"0/{len(terms)}",
        }
        try:
            request = urllib.request.Request(
                document,
                headers={"Accept": accept, "User-Agent": "nomad-semantic-mapper/0.1"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read(max_bytes + 1)
                content_type = response.headers.get_content_type()
                resolved = response.geturl()
            if len(payload) > max_bytes:
                raise ValueError("RDF response exceeds the 50 MiB validation limit")
            formats = {
                "text/turtle": "turtle",
                "application/rdf+xml": "xml",
                "application/n-triples": "nt",
                "application/ld+json": "json-ld",
            }
            candidates = [formats.get(content_type), "turtle", "xml", "nt", "json-ld"]
            parsed = None
            parse_errors: list[str] = []
            for rdf_format in dict.fromkeys(item for item in candidates if item):
                try:
                    graph = Graph().parse(data=payload, format=rdf_format, publicID=resolved)
                    parsed = (graph, rdf_format)
                    break
                except Exception as exc:  # parser messages are retained in the report
                    parse_errors.append(f"{rdf_format}: {exc}")
            if parsed is None:
                raise ValueError("not parseable as RDF (" + "; ".join(parse_errors) + ")")
            graph, rdf_format = parsed
            found = [iri for iri in terms if any(graph.triples((URIRef(iri), None, None)))]
            missing = sorted(set(terms) - set(found))
            if missing:
                warnings.append(
                    f"{document} loaded, but these referenced terms were not declared: "
                    + ", ".join(missing)
                )
            for iri in found:
                declared = set(graph.objects(URIRef(iri), RDF.type)) & all_entity_types
                expected = expected_kinds[iri]
                compatible = set().union(*(owl_types.get(kind, set()) for kind in expected))
                if declared and compatible and declared.isdisjoint(compatible):
                    warnings.append(
                        f"External term {iri} is used as {sorted(expected)}, but its vocabulary "
                        f"declares {sorted(str(item) for item in declared)}."
                    )
                if len(expected) > 1:
                    warnings.append(
                        f"External term {iri} is used with multiple entity kinds: {sorted(expected)}."
                    )
            record.update(
                status="passed",
                triples=len(graph),
                terms=f"{len(found)}/{len(terms)}",
                resolved=resolved,
                format=rdf_format,
            )
        except (OSError, ValueError, urllib.error.URLError) as exc:
            record["message"] = str(exc)
            warnings.append(f"External vocabulary {document} could not be loaded: {exc}")
        results.append(record)
    return results, warnings


def run_reasoner(namespace: dict[str, Any], reasoner: str) -> tuple[list[str], list[str]]:
    """Run an Owlready2 reasoner; unavailable Java/reasoners become report warnings."""
    if reasoner == "none":
        return ["Reasoner explicitly disabled."], []
    ontology = namespace["ontology"]
    details: list[str] = []
    warnings: list[str] = []
    try:
        if reasoner == "pellet":
            namespace["sync_reasoner_pellet"](
                [ontology],
                infer_property_values=True,
                infer_data_property_values=True,
            )
        else:
            namespace["sync_reasoner"](
                [ontology],
                infer_property_values=True,
                ignore_unsupported_datatypes=True,
            )
        inconsistent = list(namespace["world"].inconsistent_classes())
        if inconsistent:
            warnings.append(
                "Unsatisfiable classes: " + ", ".join(item.iri for item in inconsistent)
            )
        details.append(f"{reasoner.title()} completed; {len(inconsistent)} unsatisfiable classes.")
    except Exception as exc:
        warnings.append(
            f"{reasoner.title()} did not complete: {type(exc).__name__}: {exc}. "
            "Check Java and the reasoner installation."
        )
    return details, warnings


def render_report(
    schema: Path,
    base_iri: str,
    entities: list[Entity],
    external_iris: list[str],
    external_results: list[dict[str, Any]],
    stages: list[StageResult],
    graph_size: int,
) -> str:
    operations = sum(len(entity.operations) for entity in entities)
    warnings = [warning for stage in stages for warning in stage.warnings]
    lines = [
        "# NOMAD semantic mapping report",
        "",
        f"- Generated: `{dt.datetime.now(dt.timezone.utc).isoformat()}`",
        f"- Schema: `{schema.name}`",
        f"- Ontology IRI: `{base_iri}`",
        f"- Result: **{'completed with warnings' if warnings else 'passed'}**",
        "",
        "## Pipeline",
        "",
        "| Stage | Status | Duration | Details |",
        "| --- | --- | ---: | --- |",
    ]
    for stage in stages:
        detail = "<br>".join(stage.details) or "—"
        lines.append(f"| {stage.name} | {stage.status} | {stage.seconds:.3f}s | {detail} |")
    lines.extend(
        [
            "",
            "## Model summary",
            "",
            f"- Declared mapped entities: **{len(entities)}**",
            f"- Declarative operations: **{operations}**",
            f"- Generated RDF triples: **{graph_size}**",
            f"- Referenced external IRIs: **{len(external_iris)}**",
            "",
            "## External vocabulary validation",
            "",
            "External documents are downloaded only into isolated temporary RDF graphs. "
            "They are not imported into the generated ontology.",
            "",
            "| Requested namespace | Status | Terms found | Resolved document | RDF format | Triples |",
            "| --- | --- | ---: | --- | --- | ---: |",
        ]
    )
    if external_results:
        for item in external_results:
            lines.append(
                "| {namespace} | {status} | {terms} | {resolved} | {format} | {triples} |".format(
                    namespace=item["namespace"],
                    status=item["status"],
                    terms=item.get("terms", "—"),
                    resolved=item.get("resolved", "—"),
                    format=item.get("format", "—"),
                    triples=item.get("triples", 0),
                )
            )
    else:
        lines.append("| — | skipped | — | — | — | 0 |")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {warning}" for warning in warnings)
    if not warnings:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `ontology.py`: generated Owlready2 representation",
            "- `ontology.ttl`: generated OWL ontology in Turtle",
            "- `report.md`: this pipeline report",
            "",
            "## Interpretation",
            "",
            "A passed serialization check means the graph is valid Turtle and every mapped "
            "local entity occurs in it. A passed reasoner stage means the selected reasoner "
            "completed for the generated model. External resolution proves that a vocabulary "
            "document was reachable and RDF-parseable; it does not prove that every chosen term "
            "has the intended scientific meaning. Review warnings and domain semantics before "
            "publishing.",
            "",
        ]
    )
    return "\n".join(lines)


def run_pipeline(
    schema: Path,
    output_dir: Path,
    base_iri: str,
    reasoner: str,
    offline: bool,
    external_timeout: float,
) -> Path:
    """Load -> reason -> validate -> generate Python/Turtle -> report."""
    stages: list[StageResult] = []

    started = time.monotonic()
    entities = parse_schema(schema)
    resolver = Resolver(entities, schema)
    generated = render_python(entities, resolver, schema.name, base_iri)
    external_iris = list(resolver.externals)
    stages.append(
        _stage(
            "1. Load and compile",
            started,
            [f"{len(entities)} entities", f"{len(external_iris)} external references"],
            [],
        )
    )

    started = time.monotonic()
    namespace: dict[str, Any] = {"__name__": "nomad_generated_ontology"}
    exec(compile(generated, f"<generated from {schema.name}>", "exec"), namespace)
    reasoner_details, reasoner_warnings = run_reasoner(namespace, reasoner)
    reasoner_stage = _stage(
        f"2. Reasoner ({reasoner})", started, reasoner_details, reasoner_warnings
    )
    if reasoner == "none":
        reasoner_stage.status = "skipped"
    stages.append(reasoner_stage)

    started = time.monotonic()
    graph = _ontology_graph(namespace)
    uri_ref = __import__("rdflib").URIRef
    local_missing = [
        entity.iri
        for entity in entities
        if not any(graph.triples((uri_ref(entity.iri), None, None)))
    ]
    validation_details = [f"Turtle-ready RDF graph: {len(graph)} triples"]
    validation_warnings = []
    if local_missing:
        validation_warnings.append("Mapped entities absent from RDF: " + ", ".join(local_missing))
    if offline:
        external_results: list[dict[str, Any]] = []
        validation_details.append("External vocabulary loading skipped (--offline).")
    else:
        external_results, external_warnings = validate_external_vocabularies(
            resolver.external_kinds, external_timeout
        )
        validation_warnings.extend(external_warnings)
        validation_details.append(
            f"Loaded {sum(item['status'] == 'passed' for item in external_results)} of "
            f"{len(external_results)} external vocabulary documents into temporary graphs."
        )
    stages.append(
        _stage("3. Validate", started, validation_details, validation_warnings)
    )

    started = time.monotonic()
    output_dir.mkdir(parents=True, exist_ok=True)
    python_output = output_dir / "ontology.py"
    turtle_output = output_dir / "ontology.ttl"
    python_output.write_text(generated, encoding="utf-8")
    namespace["save_turtle"](turtle_output)
    stages.append(
        _stage(
            "4. Generate",
            started,
            [f"Python: {python_output.name}", f"Turtle: {turtle_output.name}"],
            [],
        )
    )

    report = output_dir / "report.md"
    stages.append(
        StageResult(
            "5. Report",
            "passed",
            0.0,
            [f"Markdown: {report.name}"],
            [],
        )
    )
    report.write_text(
        render_report(
            schema,
            base_iri,
            entities,
            external_iris,
            external_results,
            stages,
            len(graph),
        ),
        encoding="utf-8",
    )
    return report


# --------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile OntologyMap declarations to Python/Turtle, or run the staged "
            "reasoning and validation pipeline."
        )
    )
    parser.add_argument("schemafile", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--to", type=str.lower, choices=("ttl", "py"))
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="run load, reasoner, validation, dual generation, and report stages",
    )
    parser.add_argument(
        "--reasoner",
        choices=("hermit", "pellet", "none"),
        default="hermit",
        help="reasoner used by --pipeline (default: hermit)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="skip external vocabulary resolution/loading in --pipeline",
    )
    parser.add_argument(
        "--external-timeout",
        type=float,
        default=10.0,
        help="seconds allowed per external vocabulary request (default: 10)",
    )
    parser.add_argument(
        "--base-iri",
        help="IRI of the generated ontology document itself. Entity IRIs come from the schema.",
    )
    args = parser.parse_args(argv)

    schema = args.schemafile.resolve()
    if not schema.is_file():
        parser.error(f"schema file does not exist: {schema}")

    if args.pipeline and args.to:
        parser.error("use either --pipeline or --to, not both")
    if not args.pipeline and not args.to:
        parser.error("one of --pipeline or --to is required")
    if args.external_timeout <= 0:
        parser.error("--external-timeout must be greater than zero")

    output = args.output.resolve()
    if not args.pipeline:
        expected = f".{args.to}"
        if not output.suffix:
            output = output.with_suffix(expected)
        elif output.suffix.lower() != expected:
            parser.error(f"--to {args.to} but output file ends in {output.suffix}")

    try:
        base_iri = args.base_iri or f"https://nomad-lab.eu/generated/{identifier(schema.stem)}#"
        if not base_iri.endswith(("#", "/")):
            base_iri += "#"
        if args.pipeline:
            report = run_pipeline(
                schema,
                output,
                base_iri,
                args.reasoner,
                args.offline,
                args.external_timeout,
            )
            print(report)
            return 0
        entities = parse_schema(schema)
        generated = render_python(entities, Resolver(entities, schema), schema.name, base_iri)
    except (SyntaxError, MappingError, ModuleNotFoundError) as exc:
        parser.error(str(exc))

    output.parent.mkdir(parents=True, exist_ok=True)
    if args.to == "py":
        output.write_text(generated, encoding="utf-8")
        print(output)
        return 0

    namespace: dict[str, Any] = {"__name__": "nomad_generated_ontology"}
    try:
        exec(compile(generated, f"<generated from {schema.name}>", "exec"), namespace)
        namespace["save_turtle"](output)
    except ModuleNotFoundError as exc:
        if exc.name == "owlready2":
            parser.error("install Owlready2 first: python -m pip install owlready2")
        if exc.name == "rdflib":
            parser.error("install RDFLib first: python -m pip install rdflib")
        raise
    print(output)
    return 0


# --------------------------------------------------------------------------------
# Inert runtime facade. NOMAD schema modules import these names from this same file.
# Owlready2 is imported only by generated ontology.py, never by this facade.
# --------------------------------------------------------------------------------


@dataclass(frozen=True)
class RuntimeOperation:
    name: str
    kwargs: dict[str, Any]


def _runtime_operation(name: str):
    def factory(**kwargs: Any) -> RuntimeOperation:
        return RuntimeOperation(name, kwargs)

    factory.__name__ = name
    factory.__doc__ = f"Declarative {name} record consumed by the AST compiler."
    return factory


def OntologyMap(operations: list[RuntimeOperation]):
    """Inert NOMAD decorator/wrapper; it never imports or calls Owlready2."""

    def apply(target: Any) -> Any:
        try:
            target.__ontology_map__ = tuple(operations)
        except (AttributeError, TypeError):
            pass
        return target

    return apply


_RUNTIME_NAMES = tuple(dict.fromkeys((*SIGNATURES, *sorted(EXPRESSIONS))))
for _runtime_name in _RUNTIME_NAMES:
    globals()[_runtime_name] = _runtime_operation(_runtime_name)
del _runtime_name

__all__ = ("OntologyMap", *_RUNTIME_NAMES)


if __name__ == "__main__":
    raise SystemExit(main())
