# Technical architecture and extension guide

This document is for FAIRmat/NOMAD maintainers who need to review, integrate, or
extend the semantic decorator. The public onboarding and grammar catalog live in
[README.md](README.md).

## 1. Design goals

The implementation keeps four concerns separate:

1. NOMAD owns schema structure and values.
2. `OntologyMap` owns explicit semantic declarations.
3. Owlready2 is a wrapped backend, not user-facing schema grammar.
4. Validation and reasoning report evidence; they do not silently rewrite intent.

Two invariants must survive any NOMAD integration:

- Python class identity, base classes, and inheritance never imply OWL class identity
  or subclass axioms. Only explicit semantic operations create them.
- A wrapper on an assignment maps the attribute handle. It does not map, replace, or
  reinterpret the assigned `Quantity`, `SubSection`, `DataFrame`, or other object.

The mapper is standalone and deliberately does not modify NOMAD internals. It can be
prototyped beside NOMAD and later integrated into `nomad.metainfo` after the grammar
and lifecycle are accepted.

## 2. Single-file architecture

`nomad_semantic_mapper.py` contains these layers in dependency order:

```text
operation signatures and compatibility table
        ↓
parsed Operation / Entity model
        ↓
AST-only schema loader
        ↓
scope and IRI resolver
        ↓
OWL expression and axiom renderer
        ↓
generated Owlready2 module template
        ↓
reasoner + external vocabulary validator
        ↓
pipeline report and CLI
        ↓
inert runtime decorator facade
```

Only generated `ontology.py` imports Owlready2. Importing
`nomad_semantic_mapper` for decorators uses the inert facade and has no Owlready2 or
NOMAD dependency.

## 3. How the decorator works

At normal NOMAD runtime, an operation call produces a `RuntimeOperation` record:

```python
Class(iri="https://example.org/onto#Sample")
# RuntimeOperation(name="Class", kwargs={"iri": "...#Sample"})
```

`OntologyMap(operations)` returns an inert decorator/wrapper. It returns the NOMAD
target unchanged and, where the target permits attributes, stores the records in
`__ontology_map__` for future NOMAD-side inspection.

This runtime behavior does not generate OWL. The compiler independently reads the
source AST. Keeping these paths separate has two advantages:

- conversion works when `nomad` is not installed;
- Python expressions, imports, descriptors, and schema initialization never execute
  during ontology compilation.

## 4. How Owlready2 is wrapped

The compiler emits a standalone Python module containing:

- an isolated Owlready2 `World`;
- one generated ontology;
- namespaces for explicitly declared IRIs;
- temporary handles for externally owned entities;
- declarations first, individuals second, and axioms last;
- a Turtle serializer that passes N-Triples through RDFLib.

Conceptual translation:

| Declarative grammar | Generated Owlready2 backend |
| --- | --- |
| `Class(iri=...)` | `types.new_class(fragment, (Thing,))` in the IRI namespace |
| `ObjectProperty(iri=...)` | `types.new_class(..., (ObjectProperty, ...))` |
| `Individual(iri=..., type=...)` | an instance of the resolved Owlready2 class |
| `SubClassOf` | append to `.is_a` |
| `EquivalentTo` | append to `.equivalent_to` |
| `SomeValuesFrom` | `property.some(filler)` |
| `AllValuesFrom` | `property.only(filler)` |
| Boolean expressions | Owlready2 `And`, `Or`, `Not`, and `OneOf` objects |
| `PropertyChain` | Owlready2 `PropertyChain` |
| inequality | Owlready2 `AllDifferent` |

Schema authors never depend on these backend expressions. A future backend can
implement the same declarative operation model without changing schema syntax.

## 5. AST compilation

`parse_schema(path)` uses `ast.parse` and recognizes two forms:

```python
@OntologyMap([...])
class SectionName(...):
    ...

field_name = OntologyMap([...])(Quantity(...))
```

The parser records:

- the qualified handle (`SectionName.field_name`);
- the enclosing scope;
- the mandatory semantic IRI;
- the declaration kind;
- every operation and source line;
- the wrapped NOMAD expression as a comment only.

Operation arguments must be literal AST structures accepted by the grammar. In
particular, the compiler does not evaluate variables used as IRI prefixes.

## 6. Declaration and compatibility model

`DECLARATIONS`, `AXIOMS`, and `UNIVERSAL` define keyword signatures. `ALLOWED`
defines which top-level axioms are valid for each declaration kind. This is the
first place a new operation must be registered.

Each `Signature` contains:

- `required`: keywords that must be present;
- `optional`: accepted optional keywords;
- `one_of`: a mutually exclusive group where exactly one must be present.

Example:

```python
"Fact": signature("property", one_of="value literal")
```

This rejects both an assertion with no value and one containing both an object and
a literal.

## 7. Resolution rules

`Resolver` indexes all declarations by qualified handle and by IRI before rendering.
Forward references therefore work.

Resolution order is:

1. exact local IRI;
2. handle in the current scope;
3. handle in each parent scope;
4. global handle;
5. external IRI.

An unresolved string without an IRI scheme is an error. External references are
materialized before generated `with ontology:` blocks because Owlready2 cannot safely
create a new namespace while another ontology context is active.

`Resolver.external_kinds` also records how each external IRI is used. The validator
compares those expectations with published RDF types when available.

## 8. Expression rendering

`class_expression` recursively handles named references, Boolean expressions,
enumerations, and nested restrictions. `property_expression` handles named properties
and inverse-property expressions. `restriction_expression` is shared by top-level
and nested restrictions.

New expression implementations must:

- validate keyword names and required arguments;
- recurse only through the supported expression functions;
- register every external reference through `Resolver`;
- produce an Owlready2 expression, not a free-form statement;
- include positive and negative tests.

## 9. Staged pipeline

`run_pipeline` implements:

```text
load/compile → reason → validate → generate → report
```

### Stage 1: load and compile

The AST is parsed, entities are validated, references are resolved, and generated
Python is prepared in memory. Syntax and mapping errors are fatal.

### Stage 2: reason

The generated module is executed in an isolated namespace and passed to HermiT or
Pellet through Owlready2. HermiT is the default. Both reasoners require Java.

The stage records:

- whether the reasoner completed;
- thrown inconsistency or environment errors;
- classes inferred equivalent to `owl:Nothing`.

Reasoner failure becomes a warning so the report and artifacts can still explain
what happened. A CI policy may choose to treat report warnings as build failures.

### Stage 3: validate

Internal validation serializes the current ontology to N-Triples, parses it with
RDFLib, counts triples, and verifies that every locally mapped entity occurs as an
RDF subject.

External validation:

1. groups external IRIs by namespace document;
2. requests RDF using content negotiation and follows redirects;
3. parses each response into an isolated in-memory RDF graph;
4. checks whether every referenced term occurs as a subject;
5. compares known OWL/RDFS entity types with mapping usage;
6. records all failures and mismatches as warnings.

External graphs are never merged into the generated ontology. This avoids silently
copying large third-party vocabularies into NOMAD output.

### Stage 4: generate

The exact compiled model is written as `ontology.py` and `ontology.ttl`.

### Stage 5: report

`report.md` records stage state, duration, model counts, external redirects, parsed
formats, term coverage, warnings, and interpretation limits.

## 10. Adding a new decorator operation

Use this checklist for every addition.

### Step 1: define syntax

Choose one narrow semantic name and a keyword-only signature. Avoid a generic code
or triple escape hatch.

For example, a future operation might begin as:

```python
"DisjointUnion": signature("classes")
```

### Step 2: declare compatibility

Add it only to the relevant `ALLOWED` declaration kinds. `DisjointUnion` would be
valid on `Class`, not on a data property or individual.

### Step 3: implement rendering

Add a branch in `operation_lines`, or a dedicated expression renderer when nesting
is legal. Resolve references through `Resolver`; never interpolate unchecked source
text into generated Python.

### Step 4: expose the inert runtime name

Names in `SIGNATURES` and `EXPRESSIONS` are automatically exported by the runtime
facade. Confirm `from nomad_semantic_mapper import *` exposes the new factory.

### Step 5: validate generated RDF

Assert the expected W3C RDF mapping, such as `owl:disjointUnionOf`, rather than only
asserting that Python generation succeeded.

### Step 6: document and demonstrate

Update the operation catalog, coverage table, executable example, expected Turtle,
and current OWL 2 boundary.

## 11. Adding a pipeline validator

A validator should return structured details and warnings, not print ad-hoc output.
It must not mutate the ontology unless that behavior is explicitly part of a stage.

Recommended categories:

- **syntax** — mapping grammar and literal argument validation;
- **identity** — duplicate IRIs and unresolved handles;
- **vocabulary** — resolution, redirects, term existence, entity-kind compatibility;
- **OWL profile** — DL/EL/QL/RL structural constraints;
- **reasoning** — consistency and unsatisfiable classes;
- **domain semantics** — optional project rules, clearly separated from OWL validity.

Network validators require a timeout and must degrade to report warnings. Tests must
have an offline mode and must not depend on third-party availability.

## 12. Testing expectations

At minimum, changes should test:

1. mapper import without NOMAD or Owlready2;
2. AST parsing without executing a schema;
3. valid Python generation;
4. Turtle parsing with RDFLib;
5. the exact RDF predicate for each new construct;
6. forward and scoped handle resolution;
7. invalid signatures and entity/operation combinations;
8. offline pipeline output and `report.md` structure;
9. reasoner success when Java is available;
10. external failure, redirect, missing-term, and entity-kind warning paths.

Passing selected examples is useful regression evidence but is not formal OWL 2
conformance. The W3C conformance suite explains why passing a finite set of tests
cannot alone prove full conformance.

## 13. Security and operational limits

- The schema is parsed, never imported, during conversion.
- The public grammar cannot inject arbitrary backend Python.
- Generated Python is executed only from compiler-produced templates.
- External documents are untrusted data and are parsed in isolated graphs.
- Redirects and downloads are reported and bounded by per-request timeouts.
- External vocabulary availability is not guaranteed; preserve offline builds.
- HermiT/Pellet invoke Java subprocesses through Owlready2.
- Reasoning can be expensive; production CI should set resource/time policies around
  the mapper process.

## 14. Integration path into NOMAD

A conservative upstream path is:

1. stabilize operation names in this standalone prototype;
2. add unit and RDF golden tests for every supported operation;
3. agree whether mapping records belong on definitions directly or in NOMAD's
   annotation infrastructure;
4. move only the inert semantic model into `nomad.metainfo`;
5. keep compilation, network validation, and reasoning as an optional tool/plugin;
6. add versioning and migration rules before schemas depend on the API broadly.

This keeps NOMAD schema loading lightweight while allowing semantic publishing and
quality checks to evolve independently.

## 15. References

- [OWL 2 Structural Specification](https://www.w3.org/TR/owl2-syntax/)
- [OWL 2 Mapping to RDF Graphs](https://www.w3.org/TR/owl2-mapping-to-rdf/)
- [OWL 2 Conformance](https://www.w3.org/TR/owl2-conformance/)
- [Owlready2 reasoning](https://owlready2.readthedocs.io/en/latest/reasoning.html)
- [Owlready2 worlds](https://owlready2.readthedocs.io/en/latest/world.html)
- [NOMAD schema packages](https://docs.nomad-lab.eu/howto/plugins/types/schema_packages.html#definitions)
