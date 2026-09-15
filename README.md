# NOMAD Semantic Mapper

> **Semantic independence rule:** a Python class named `Sample`, its base classes,
> and its Python inheritance do not create an OWL class or subclass relationship.
> Only `Class(...)`, `SubClassOf(...)`, and the other explicit mapping operations do
> that. Likewise, a mapping attached to `temperature = OntologyMap([...])(
> Quantity(...))` describes the **`temperature` attribute**. It does not describe or
> transform the assigned `Quantity` object. An undecorated class or attribute emits
> no ontology entity.

## 1. Introduction and decorator API

The mapper is a declarative Python-to-OWL compiler. `OntologyMap` can annotate a
Python class or wrap any assigned Python expression. It does not depend on NOMAD's
runtime model: the compiler reads Python syntax without importing or executing the
input file. NOMAD `MSection`, `Quantity`, `SubSection`, and `DataFrame` definitions
are important consumers of the API, but they are not required to understand or use
the decorator grammar.

```text
Python source + declarative OntologyMap calls
        │
        ├─ load and compile the Python AST (the schema is never executed)
        ├─ reason with HermiT or Pellet
        ├─ validate the generated graph and external vocabularies
        ├─ generate ontology.py and ontology.ttl
        └─ generate report.md
```

Owlready2 is always wrapped. Input schemas never import Owlready2 and never contain
backend Python statements. The single [nomad_semantic_mapper.py](nomad_semantic_mapper.py)
file provides the inert decorators, AST compiler, validator, reasoner integration,
code generator, and command-line interface.

### 1.1 SDK-style quickstart without NOMAD

The complete call shape is:

```python
OntologyMap([
    Declaration(iri="absolute IRI", option="value"),  # exactly one
    Operation(option="value"),                         # zero or more
    Operation(option="value"),
])(python_target)
```

For a Python class, use the same object as a decorator. For an attribute, wrap its
assigned expression. This framework-independent file exercises both forms:

```python
from nomad_semantic_mapper import (
    Annotation,
    Class,
    DataProperty,
    Fact,
    Individual,
    ObjectProperty,
    OntologyMap,
    SubClassOf,
)


class SemanticHandles:
    # The attribute is an OWL class handle, even though object() is not a class.
    dataset_kind = OntologyMap([
        Class(iri="https://example.org/lab#DatasetKind"),
        SubClassOf(iri="http://www.w3.org/ns/dcat#Dataset"),
    ])(object())

    # The attribute is an OWL object-property handle.
    source = OntologyMap([
        ObjectProperty(iri="http://www.w3.org/ns/prov#wasDerivedFrom"),
    ])(object())

    # The attribute is an OWL datatype-property handle.
    identifier = OntologyMap([
        DataProperty(
            iri="https://example.org/lab#identifier",
            domain=["dataset_kind"],
            range=["xsd:string"],
        ),
    ])(object())

    # The attribute is a named OWL individual with an assertion.
    run_001 = OntologyMap([
        Individual(
            iri="https://example.org/lab#run-001",
            type="http://www.w3.org/ns/prov#Activity",
        ),
        Fact(
            property="http://www.w3.org/ns/prov#used",
            value="https://example.org/lab#sample-001",
        ),
        Annotation(property="label", literal="Run 001"),
    ])(object())


# A Python class can also be the mapping handle.
@OntologyMap([
    Class(iri="https://example.org/lab#Workflow"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Activity"),
])
class Workflow:
    pass
```

Compile this ordinary Python file exactly like a NOMAD schema:

```bash
python nomad_semantic_mapper.py semantic_model.py build/model \
  --pipeline --reasoner hermit --base-iri https://example.org/lab
```

The important API behavior is summarized below.

| API element | Contract |
| --- | --- |
| `OntologyMap(operations)` | Accepts one literal list of declarative grammar calls |
| first declaration | Determines whether the handle is a class, individual, or property |
| later operations | Add axioms, restrictions, facts, equality, or annotations |
| `(...)(python_target)` | Returns/wraps the Python target while syntax supplies a mapping handle |
| `@OntologyMap(...)` | Uses a Python class name as the handle; class semantics still come only from the list |
| local string reference | Resolves another mapped handle, for example `"dataset_kind"` |
| absolute IRI reference | Reuses or relates to an external ontology term |
| generated output | Owlready2 Python, Turtle RDF, and a validation report |

The mapper wraps Owlready2 internally. Users never write Owlready2 classes,
statements, or raw backend code in `OntologyMap`.

### 1.2 Applying the same API to a NOMAD schema

Python supplies only a local handle. The mapping list supplies all semantics.

```python
@OntologyMap([
    Class(iri="https://example.org/materials#Sample"),
])
class Sample(MSection):
    temperature = OntologyMap([
        DataProperty(iri="https://example.org/materials#temperature"),
    ])(Quantity(type=float, unit="kelvin"))
```

| Source construct | Semantic meaning |
| --- | --- |
| `class Sample(MSection)` | NOMAD structure only; not automatically an OWL class |
| `Sample` | Local mapping handle |
| `Class(iri=...)` | Explicit OWL class declaration |
| `temperature` | Local mapping handle for the assignment |
| `Quantity(...)` | NOMAD grammar preserved as a generated-code comment |
| `DataProperty(iri=...)` | Explicit OWL datatype-property declaration |

No field name is special. `system`, `sample`, `temperature`, and every other
assignment follow the same rule.

### 1.3 Install

```bash
python -m pip install owlready2 rdflib
```

Generating Python needs no NOMAD installation because the mapper reads the schema's
AST rather than importing it. Executing the schema itself still needs NOMAD.

### 1.4 One-output commands

```bash
python nomad_semantic_mapper.py examples/xps_measurement.schema.py ontology.py \
  --to py --base-iri https://nomad-lab.eu/onto/xps

python nomad_semantic_mapper.py examples/xps_measurement.schema.py ontology.ttl \
  --to ttl --base-iri https://nomad-lab.eu/onto/xps
```

### 1.5 Staged pipeline

```bash
python nomad_semantic_mapper.py examples/xps_measurement.schema.py build/xps \
  --pipeline --reasoner hermit \
  --base-iri https://nomad-lab.eu/onto/xps
```

The output directory receives:

| Artifact | Contents |
| --- | --- |
| `ontology.py` | Standalone, inspectable Owlready2 representation |
| `ontology.ttl` | OWL ontology serialized as Turtle |
| `report.md` | Stage results, timings, counts, external checks, and warnings |

Pipeline stages are deliberately separated:

1. **Load and compile** — parse decorators without importing the NOMAD schema.
2. **Reason** — run HermiT by default, or `--reasoner pellet`. Missing Java,
   inconsistency, and unsatisfiable classes are reported.
3. **Validate** — parse the generated RDF, verify local entities, resolve external
   namespaces, load them into isolated temporary graphs, check referenced terms,
   and compare declared OWL entity kinds.
4. **Generate** — write Python and Turtle together.
5. **Report** — write the complete Markdown report.

Use `--offline` when network validation must be skipped, and `--reasoner none` only
when reasoning is intentionally disabled. Reports label skipped stages explicitly.

## 2. Supported operations and OWL grammar

### 2.1 Grammar shape

```text
mapping       := OntologyMap([declaration, operation*])
declaration   := Class | Individual | ObjectProperty |
                 DataProperty | AnnotationProperty
operation     := axiom | restriction | assertion | annotation
expression    := named-reference | IntersectionOf | UnionOf |
                 ComplementOf | OneOf | restriction
reference     := "local.handle" | "absolute IRI"
```

Operations use keyword arguments only. Each mapped target has exactly one
declaration, and each declaration has an explicit IRI.

### 2.2 Entity declarations

| Operation | Required arguments | Optional arguments | OWL result |
| --- | --- | --- | --- |
| `Class` | `iri` | `parents` | `owl:Class` |
| `Individual` | `iri`, `type` | — | `owl:NamedIndividual` and class assertion |
| `ObjectProperty` | `iri` | `characteristics`, `domain`, `range` | `owl:ObjectProperty` |
| `DataProperty` | `iri` | `characteristics`, `domain`, `range` | `owl:DatatypeProperty` |
| `AnnotationProperty` | `iri` | — | `owl:AnnotationProperty` |

### 2.3 Class and property axioms

| Operation | Meaning |
| --- | --- |
| `SubClassOf(iri=...)` | Named superclass |
| `SubClassOf(expression=...)` | Complex superclass expression |
| `EquivalentTo(iri=...)` | Equivalent named class/property |
| `EquivalentTo(expression=...)` | Equivalent complex class expression |
| `DisjointWith(iri=...)` | Pairwise class/property disjointness |
| `DisjointWith(expression=...)` | Disjointness with a class expression |
| `AllDisjoint(entities=[...])` | N-ary disjointness including the mapped entity |
| `SubPropertyOf(iri=...)` | Property hierarchy |
| `InverseOf(iri=...)` | Inverse object property |
| `Domain(iri=...)` | Additional property domain |
| `Range(iri=...)` | Additional property range |
| `PropertyChain(properties=[...])` | Object-property chain |

Domain and range can also be supplied directly on a property declaration.

### 2.4 Class and property expressions

| Expression | Grammar | RDF construct |
| --- | --- | --- |
| intersection | `IntersectionOf(operands=[...])` | `owl:intersectionOf` |
| union | `UnionOf(operands=[...])` | `owl:unionOf` |
| complement | `ComplementOf(operand=...)` | `owl:complementOf` |
| enumeration | `OneOf(individuals=[...])` | `owl:oneOf` |
| inverse property | `Inverse(property=...)` | inverse-property expression |

Expressions may contain other supported expressions or restrictions.

### 2.5 Restrictions

| Operation | Required arguments | Optional arguments | OWL meaning |
| --- | --- | --- | --- |
| `SomeValuesFrom` | `property`, `filler` | `equivalent` | existential / `some` |
| `AllValuesFrom` | `property`, `filler` | `equivalent` | universal / `only` |
| `MinCardinality` | `property`, `count` | `filler`, `equivalent` | minimum cardinality |
| `MaxCardinality` | `property`, `count` | `filler`, `equivalent` | maximum cardinality |
| `ExactCardinality` | `property`, `count` | `filler`, `equivalent` | exact cardinality |
| `HasValue` | `property` plus `value` or `literal` | `equivalent` | value restriction |
| `HasSelf` | `property` | `value`, `equivalent` | self restriction |

At class top level, `equivalent=True` places the restriction in
`owl:equivalentClass`; otherwise it becomes an `rdfs:subClassOf` condition.

### 2.6 Individuals and assertions

| Operation | Meaning |
| --- | --- |
| `Fact(property=..., value=...)` | Object-property assertion |
| `Fact(property=..., literal=...)` | Data-property assertion |
| `Type(iri=...)` | Additional named class assertion |
| `Type(expression=...)` | Complex class assertion |
| `SameAs(iri=...)` | Individual equality |
| `DifferentFrom(iri=...)` | Pairwise inequality |
| `AllDifferent(individuals=[...])` | N-ary inequality |

### 2.7 Annotations

```python
Annotation(property="http://purl.org/dc/terms/title", literal="XPS spectrum")
Annotation(property="seeAlso", value="https://example.org/resource")
```

The property may be a full IRI, a local `AnnotationProperty`, or a builtin such as
`label`, `comment`, `seeAlso`, `isDefinedBy`, or `versionInfo`.

### 2.8 Property characteristics

`ObjectProperty` and `DataProperty` accept `characteristics=[...]`. Supported names:

- `FunctionalProperty`
- `InverseFunctionalProperty`
- `TransitiveProperty`
- `SymmetricProperty`
- `AsymmetricProperty`
- `ReflexiveProperty`
- `IrreflexiveProperty`

Unknown or incompatible mapping operations are rejected during compilation.

### 2.9 Reference and IRI rules

A reference is a literal string containing a local handle (`"Spectrum"`,
`"sample"`, `"Person.parent_of"`) or a complete IRI. Nested lookups start in the
current section and then move outward. Declaration order does not matter.

Prefix variables and string concatenation are not evaluated. Literal strings keep
the compiler deterministic and prevent schema execution.

Reuse an external property directly when its published meaning matches. Do not add
a narrower global domain or range to someone else's term; add a class restriction
instead. Mint a local property only for genuinely local meaning and connect it with
`SubPropertyOf`.

### 2.10 Current OWL 2 boundary

The grammar is broad but not the entire W3C OWL 2 structural specification. Missing
dedicated constructs include `DisjointUnion`, `HasKey`, custom datatype declarations
and facets, negative property assertions, anonymous individuals, axiom annotations,
ontology imports/version declarations, and standalone general class axioms.

The mapper intentionally has no arbitrary backend-code operation. New capabilities
must be added as named grammar, compiler logic, tests, documentation, and examples.

## 3. Example catalog: attribute semantics first

### 3.1 Read this before the examples

**Attribute-level mapping is the primary use case.** In this catalog, 15 of the 20
examples map attributes and five focus on classes. The placement has exact meaning:

```python
temperature = OntologyMap([DataProperty(iri="https://example.org/temperature")])(
    Quantity(type=float)
)
```

| Part | What the mapper does |
| --- | --- |
| `temperature` | Uses this Python attribute name as the local mapping handle |
| `OntologyMap([...])` | Reads this list as the complete semantic declaration |
| `DataProperty(...)` | Declares the IRI as an OWL datatype property |
| `Quantity(type=float)` | Leaves this as NOMAD schema grammar; it is **not** mapped |
| containing Python class | Emits no OWL class unless that class has its own `OntologyMap` |

This remains true for `Quantity`, `SubSection`, `DataFrame`, and any other assigned
object. The mapper attaches semantics to the **attribute**, never to the object on
the right-hand side. Attribute names such as `system`, `atoms`, `results`, and
`temperature` have no built-in behavior.

The examples use these prefixes:

```turtle
@prefix ex:   <https://nomad-lab.eu/onto/readme#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
```

### 3.2 Attribute-level examples (15)

An attribute handle is not limited to an OWL property. Its mapping list may declare
a `Class`, `Individual`, `ObjectProperty`, `DataProperty`, or
`AnnotationProperty`, followed by every operation compatible with that declaration.
The Python value on the right remains unrelated to the declared OWL entity kind.

#### A1 — declare an external object property: reuse `prov:used`

**Use case.** A record says which existing entity an activity used. The NOMAD field
may be implemented as a `Quantity`; the semantic attribute is still the published
PROV object property.

| Mapping decision | Value |
| --- | --- |
| Property | `prov:used` |
| Kind | object property |
| Local term minted | no |

```python
class Process(MSection):
    input_entity = OntologyMap([
        ObjectProperty(iri="http://www.w3.org/ns/prov#used"),
    ])(Quantity(type=str))
```

```turtle
prov:used a owl:ObjectProperty .
```

No OWL class named `Process` is generated.

#### A2 — declare an external object property on a subsection: reuse `prov:generated`

**Use case.** A repeating NOMAD subsection contains results generated by an
activity. Mapping the attribute declares `prov:generated`; it does not turn the
`SubSection` object into an ontology entity.

```python
class Process(MSection):
    results = OntologyMap([
        ObjectProperty(iri="http://www.w3.org/ns/prov#generated"),
    ])(SubSection(sub_section="Result", repeats=True))
```

```turtle
prov:generated a owl:ObjectProperty .
```

#### A3 — declare a class and subclass axiom on an attribute

**Use case.** A schema attribute acts as the handle for the project concept
`SampleKind`, explicitly aligned with `prov:Entity`. The assigned `Quantity` does
not become an OWL class; the `Class` declaration does.

| Independent semantic specification | Value |
| --- | --- |
| entity kind | OWL class |
| local class | `ex:SampleKind` |
| superclass | `prov:Entity` |

```python
class VocabularySection(MSection):
    sample_kind = OntologyMap([
        Class(iri="https://nomad-lab.eu/onto/readme#SampleKind"),
        SubClassOf(iri="http://www.w3.org/ns/prov#Entity"),
    ])(Quantity(type=str))
```

```turtle
ex:SampleKind a owl:Class ;
    rdfs:subClassOf prov:Entity .
```

#### A4 — declare an equivalent class with a restriction on an attribute

**Use case.** The `publishable_dataset_kind` attribute defines a class equivalent to
a DCAT dataset that has at least one DCAT distribution. A sibling attribute supplies
the local handle used by the restriction.

```python
class VocabularySection(MSection):
    distribution = OntologyMap([
        ObjectProperty(iri="http://www.w3.org/ns/dcat#distribution"),
    ])(SubSection(sub_section="Distribution", repeats=True))

    publishable_dataset_kind = OntologyMap([
        Class(iri="https://nomad-lab.eu/onto/readme#PublishableDatasetKind"),
        EquivalentTo(expression=IntersectionOf(operands=[
            "http://www.w3.org/ns/dcat#Dataset",
            SomeValuesFrom(
                property="distribution",
                filler="http://www.w3.org/ns/dcat#Distribution",
            ),
        ])),
    ])(Quantity(type=str))
```

```turtle
ex:PublishableDatasetKind a owl:Class ;
    owl:equivalentClass [ a owl:Class ; owl:intersectionOf (
        dcat:Dataset
        [ a owl:Restriction ; owl:onProperty dcat:distribution ;
          owl:someValuesFrom dcat:Distribution ]
    ) ] .
```

#### A5 — declare an individual and object-property fact on an attribute

**Use case.** An attribute declares a named acquisition run as a PROV activity and
asserts that it used a real external sample resource IRI.

```python
class RunRegistry(MSection):
    run_001 = OntologyMap([
        Individual(
            iri="https://nomad-lab.eu/onto/readme#run-001",
            type="http://www.w3.org/ns/prov#Activity",
        ),
        Fact(
            property="http://www.w3.org/ns/prov#used",
            value="https://www.wikidata.org/entity/Q28816538",
        ),
    ])(Quantity(type=str))
```

```turtle
ex:run-001 a owl:NamedIndividual, prov:Activity ;
    prov:used <https://www.wikidata.org/entity/Q28816538> .
```

#### A6 — add type, equality, and inequality assertions to an attribute individual

**Use case.** A registered instrument is a PROV entity, is known to be the same as
one external identifier, and different from another instrument.

```python
class InstrumentRegistry(MSection):
    instrument_alpha = OntologyMap([
        Individual(
            iri="https://nomad-lab.eu/onto/readme#instrument-alpha",
            type="http://www.w3.org/ns/sosa/Sensor",
        ),
        Type(iri="http://www.w3.org/ns/prov#Entity"),
        SameAs(iri="https://example.org/instruments/alpha"),
        DifferentFrom(iri="https://example.org/instruments/beta"),
    ])(Quantity(type=str))
```

```turtle
ex:instrument-alpha a owl:NamedIndividual, sosa:Sensor, prov:Entity ;
    owl:sameAs <https://example.org/instruments/alpha> ;
    owl:differentFrom <https://example.org/instruments/beta> .
```

#### A7 — declare a subproperty with external domain and range on an attribute

**Use case.** The project needs a precise calibration association while preserving
interoperability with the broader PROV association relation.

```python
class CalibrationRecord(MSection):
    calibrated_by = OntologyMap([
        ObjectProperty(
            iri="https://nomad-lab.eu/onto/readme#calibratedBy",
            domain=["http://www.w3.org/ns/sosa/Observation"],
            range=["http://www.w3.org/ns/prov#Agent"],
        ),
        SubPropertyOf(iri="http://www.w3.org/ns/prov#wasAssociatedWith"),
    ])(Quantity(type=str))
```

```turtle
ex:calibratedBy a owl:ObjectProperty ;
    rdfs:subPropertyOf prov:wasAssociatedWith ;
    rdfs:domain sosa:Observation ;
    rdfs:range prov:Agent .
```

#### A8 — declare an inverse-property axiom on an attribute

**Use case.** A project relation reads in the opposite direction from `prov:used`.

```python
class ProvenanceRelations(MSection):
    was_input_to = OntologyMap([
        ObjectProperty(iri="https://nomad-lab.eu/onto/readme#wasInputTo"),
        InverseOf(iri="http://www.w3.org/ns/prov#used"),
    ])(Quantity(type=str))
```

```turtle
ex:wasInputTo a owl:ObjectProperty ;
    owl:inverseOf prov:used .
```

#### A9 — declare a property-chain axiom on an attribute

**Use case.** Repeating PROV derivation twice implies a project-level indirect
derivation relation.

```python
class ProvenanceRelations(MSection):
    was_indirectly_derived_from = OntologyMap([
        ObjectProperty(
            iri="https://nomad-lab.eu/onto/readme#wasIndirectlyDerivedFrom"
        ),
        PropertyChain(properties=[
            "http://www.w3.org/ns/prov#wasDerivedFrom",
            "http://www.w3.org/ns/prov#wasDerivedFrom",
        ]),
    ])(Quantity(type=str))
```

```turtle
ex:wasIndirectlyDerivedFrom a owl:ObjectProperty ;
    owl:propertyChainAxiom (
        prov:wasDerivedFrom prov:wasDerivedFrom
    ) .
```

#### A10 — declare an external datatype property on an attribute

**Use case.** An observation records the instant at which its result became
available. `sosa:resultTime` is reused directly as an OWL datatype property.

```python
class ObservationRecord(MSection):
    result_time = OntologyMap([
        DataProperty(iri="http://www.w3.org/ns/sosa/resultTime"),
    ])(Quantity(type=str))
```

```turtle
sosa:resultTime a owl:DatatypeProperty .
```

#### A11 — declare a functional datatype property with domain and range

**Use case.** A local laboratory identifier applies to PROV entities and contains a
string. The NOMAD `type=str` does not create the RDF range; `range=["xsd:string"]`
does.

```python
class AnyRecord(MSection):
    laboratory_id = OntologyMap([
        DataProperty(
            iri="https://nomad-lab.eu/onto/readme#laboratoryId",
            characteristics=["FunctionalProperty"],
            domain=["http://www.w3.org/ns/prov#Entity"],
            range=["xsd:string"],
        ),
    ])(Quantity(type=str))
```

```turtle
ex:laboratoryId a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain prov:Entity ;
    rdfs:range xsd:string .
```

#### A12 — declare and annotate an annotation property on an attribute

**Use case.** The project introduces a reusable annotation for human review notes
and labels the annotation property itself.

```python
class DocumentationTerms(MSection):
    review_note = OntologyMap([
        AnnotationProperty(iri="https://nomad-lab.eu/onto/readme#reviewNote"),
        Annotation(property="label", literal="review note"),
    ])(Quantity(type=str))
```

```turtle
ex:reviewNote a owl:AnnotationProperty ;
    rdfs:label "review note" .
```

#### A13 — declare a disjoint-class axiom on an attribute

**Use case.** An attribute declares a result class that is a PROV entity and cannot
also be a PROV activity.

```python
class ResultVocabulary(MSection):
    result_kind = OntologyMap([
        Class(iri="https://nomad-lab.eu/onto/readme#ResultKind"),
        SubClassOf(iri="http://www.w3.org/ns/prov#Entity"),
        DisjointWith(iri="http://www.w3.org/ns/prov#Activity"),
    ])(Quantity(type=str))
```

```turtle
ex:ResultKind a owl:Class ;
    rdfs:subClassOf prov:Entity ;
    owl:disjointWith prov:Activity .
```

#### A14 — declare cardinality and all-values restrictions on an attribute class

**Use case.** An attribute declares a controlled activity class that uses exactly
one PROV entity and whose generated values are all PROV entities.

| Class axiom | Declarative operation |
| --- | --- |
| exactly one input entity | `ExactCardinality` |
| only entity outputs | `AllValuesFrom` |

```python
class ActivityVocabulary(MSection):
    controlled_activity = OntologyMap([
        Class(iri="https://nomad-lab.eu/onto/readme#ControlledActivity"),
        SubClassOf(iri="http://www.w3.org/ns/prov#Activity"),
        ExactCardinality(
            property="http://www.w3.org/ns/prov#used",
            count=1,
            filler="http://www.w3.org/ns/prov#Entity",
        ),
        AllValuesFrom(
            property="http://www.w3.org/ns/prov#generated",
            filler="http://www.w3.org/ns/prov#Entity",
        ),
    ])(Quantity(type=str))
```

```turtle
ex:ControlledActivity a owl:Class ;
    rdfs:subClassOf prov:Activity,
        [ a owl:Restriction ; owl:onProperty prov:used ;
          owl:onClass prov:Entity ; owl:qualifiedCardinality 1 ],
        [ a owl:Restriction ; owl:onProperty prov:generated ;
          owl:allValuesFrom prov:Entity ] .
```

#### A15 — declare n-ary individual inequality on an attribute

**Use case.** An attribute declares one named sensor and states that it and two
external sensor resources are mutually different.

```python
class InstrumentRegistry(MSection):
    sensor_alpha = OntologyMap([
        Individual(
            iri="https://nomad-lab.eu/onto/readme#sensor-alpha",
            type="http://www.w3.org/ns/sosa/Sensor",
        ),
        AllDifferent(individuals=[
            "https://example.org/instruments/sensor-beta",
            "https://example.org/instruments/sensor-gamma",
        ]),
    ])(Quantity(type=str))
```

```turtle
[] a owl:AllDifferent ;
   owl:distinctMembers (
       ex:sensor-alpha
       <https://example.org/instruments/sensor-beta>
       <https://example.org/instruments/sensor-gamma>
   ) .
```

### 3.3 Class-level examples (5)

Class decorators are used only when an OWL class, individual, or class axiom is
actually required. A Python class declaration and Python inheritance remain
semantically inert.

#### C1 — explicitly align a section with PROV Activity

**Use case.** An XPS acquisition is modeled as a kind of PROV activity.

```python
@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/readme#XpsAcquisition"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Activity"),
])
class XpsAcquisition(MSection):
    pass
```

```turtle
ex:XpsAcquisition a owl:Class ;
    rdfs:subClassOf prov:Activity .
```

#### C2 — explicitly align a section with DCAT Dataset

**Use case.** A Python section stores processed data and is intentionally declared
as a DCAT dataset.

```python
@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/readme#ProcessedDataset"),
    SubClassOf(iri="http://www.w3.org/ns/dcat#Dataset"),
])
class ProcessedDataset(MSection):
    pass
```

```turtle
ex:ProcessedDataset a owl:Class ;
    rdfs:subClassOf dcat:Dataset .
```

#### C3 — internal subclass handle plus external alignment

**Use case.** A local XPS result is a local experimental result, and that parent is
aligned with `prov:Entity`. Both ontology edges are explicit; Python inheritance is
irrelevant.

```python
@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/readme#ExperimentalResult"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Entity"),
])
class ExperimentalResult(MSection):
    pass

@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/readme#XpsResult"),
    SubClassOf(iri="ExperimentalResult"),
])
class XpsResult(MSection):
    pass
```

```turtle
ex:ExperimentalResult a owl:Class ; rdfs:subClassOf prov:Entity .
ex:XpsResult a owl:Class ; rdfs:subClassOf ex:ExperimentalResult .
```

#### C4 — define a class with an attribute property restriction

**Use case.** A publishable dataset is exactly a DCAT dataset having at least one
distribution. The attribute declares the property handle; the class decorator uses
that handle in an OWL class expression.

```python
@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/readme#PublishableDataset"),
    EquivalentTo(expression=IntersectionOf(operands=[
        "http://www.w3.org/ns/dcat#Dataset",
        SomeValuesFrom(
            property="distribution",
            filler="http://www.w3.org/ns/dcat#Distribution",
        ),
    ])),
])
class PublishableDataset(MSection):
    distribution = OntologyMap([
        ObjectProperty(iri="http://www.w3.org/ns/dcat#distribution"),
    ])(SubSection(sub_section="Distribution", repeats=True))
```

```turtle
ex:PublishableDataset a owl:Class ;
    owl:equivalentClass [ a owl:Class ; owl:intersectionOf (
        dcat:Dataset
        [ a owl:Restriction ; owl:onProperty dcat:distribution ;
          owl:someValuesFrom dcat:Distribution ]
    ) ] .
```

#### C5 — state class disjointness

**Use case.** A project result is a PROV entity and must not also be a PROV
activity.

```python
@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/readme#ResultEntity"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Entity"),
    DisjointWith(iri="http://www.w3.org/ns/prov#Activity"),
])
class ResultEntity(MSection):
    pass
```

```turtle
ex:ResultEntity a owl:Class ;
    rdfs:subClassOf prov:Entity ;
    owl:disjointWith prov:Activity .
```

### 3.4 Executable examples and full grammar coverage

The short examples above are designed for onboarding. The repository also contains
fourteen complete schemas that can be passed directly to the mapper:

| Focus | Executable example |
| --- | --- |
| attribute-only external and local properties | [attributes_only.schema.py](examples/attributes_only.schema.py) |
| combined class and attribute mappings | [class_and_attributes.schema.py](examples/class_and_attributes.schema.py) |
| subsection and child attributes | [subsections_and_attributes.schema.py](examples/subsections_and_attributes.schema.py) |
| external-first XPS workflow | [xps_measurement.schema.py](examples/xps_measurement.schema.py) |
| SOSA/QUDT observation workflow | [sensor_observation.schema.py](examples/sensor_observation.schema.py) |
| minimal sample onboarding | [simple_sample.schema.py](examples/simple_sample.schema.py) |
| explicit class hierarchy | [class_hierarchy.schema.py](examples/class_hierarchy.schema.py) |
| class-only mapping | [class_only.schema.py](examples/class_only.schema.py) |
| sections as relation endpoints | [section_object_relations.schema.py](examples/section_object_relations.schema.py) |
| intersections, unions, and complements | [defined_classes.schema.py](examples/defined_classes.schema.py) |
| property hierarchy, inverse, and chain | [property_axioms.schema.py](examples/property_axioms.schema.py) |
| datatype restrictions | [data_restrictions.schema.py](examples/data_restrictions.schema.py) |
| individuals and assertions | [individuals_and_facts.schema.py](examples/individuals_and_facts.schema.py) |
| broad OWL axiom families | [owl_axioms.schema.py](examples/owl_axioms.schema.py) |

| Grammar family | Demonstrated in |
| --- | --- |
| declarations: `Class`, property kinds, `Individual` | simple, attributes, individuals |
| class axioms and Boolean expressions | hierarchy, defined classes, OWL axioms |
| property axioms and characteristics | property axioms, sensor |
| object/data restrictions and cardinalities | XPS, data restrictions, OWL axioms |
| facts, types, equality, and inequality | individuals and facts, OWL axioms |
| annotations | all full examples |

The generated end-to-end XPS graph is [ontology.ttl](ontology.ttl). It is output,
not hand-authored input.

## 4. Validation, reports, and failure behavior

The compiler rejects missing or duplicate declarations, duplicate IRIs, positional
arguments, unknown operations/characteristics, incompatible operation/entity pairs,
unresolved handles, malformed nested expressions, and empty mapping files.

The external validator groups referenced IRIs by namespace, follows HTTP redirects,
requests RDF, parses each vocabulary into an isolated in-memory graph, checks each
referenced term, and compares known OWL entity types with the mapping's usage.
Network or parse failures become visible warnings.

HermiT and Pellet require Java. HermiT is the pipeline default. A reasoner failure
does not disappear: its exception and setup guidance are written to `report.md`.

A successful run means serialization completed and the selected checks passed. It
does not prove the scientific intent of every mapping. Review the report and run an
OWL-profile-specific conformance suite before publishing critical ontologies.

## 5. Specifications and implementation references

- [OWL 2 Structural Specification](https://www.w3.org/TR/owl2-syntax/)
- [OWL 2 Mapping to RDF Graphs](https://www.w3.org/TR/owl2-mapping-to-rdf/)
- [OWL 2 Conformance](https://www.w3.org/TR/owl2-conformance/)
- [Owlready2 documentation](https://owlready2.readthedocs.io/)
- [PROV-O](https://www.w3.org/TR/prov-o/)
- [SOSA/SSN](https://www.w3.org/TR/vocab-ssn/)
- [DCAT 3](https://www.w3.org/TR/vocab-dcat-3/)
- [DCMI Metadata Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/)
- [QUDT](https://www.qudt.org/)

For maintainers extending the grammar or pipeline, continue with
[TECHNICAL.md](TECHNICAL.md).
