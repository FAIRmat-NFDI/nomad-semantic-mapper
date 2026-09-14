# NOMAD Semantic Mapper

> **Semantic independence rule:** a Python class named `Sample`, its base classes,
> and its Python inheritance do not create an OWL class or subclass relationship.
> Only `Class(...)`, `SubClassOf(...)`, and the other explicit mapping operations do
> that. Likewise, a mapping attached to `temperature = OntologyMap([...])(
> Quantity(...))` describes the **`temperature` attribute**. It does not describe or
> transform the assigned `Quantity` object. An undecorated class or attribute emits
> no ontology entity.

## 1. Introduction

NOMAD Semantic Mapper adds an explicit OWL mapping grammar to ordinary NOMAD
schemas. A schema author attaches `OntologyMap([...])` to a section or wraps any
assigned definition—`Quantity`, `SubSection`, `DataFrame`, or another object.

```text
NOMAD schema + declarative decorators
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

### 1.1 The core rule

Python supplies only a local handle. The decorator supplies all semantics.

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

### 1.2 Install

```bash
python -m pip install owlready2 rdflib
```

Generating Python needs no NOMAD installation because the mapper reads the schema's
AST rather than importing it. Executing the schema itself still needs NOMAD.

### 1.3 One-output commands

```bash
python nomad_semantic_mapper.py examples/xps_measurement.schema.py ontology.py \
  --to py --base-iri https://nomad-lab.eu/onto/xps

python nomad_semantic_mapper.py examples/xps_measurement.schema.py ontology.ttl \
  --to ttl --base-iri https://nomad-lab.eu/onto/xps
```

### 1.4 Staged pipeline

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

## 3. Examples

Fourteen executable examples intentionally vary where mappings are placed and which
semantic structures dominate:

| Placement pattern | Internal/local mapping | External mapping | Cross-map/domain-range | Example |
| --- | --- | --- | --- | --- |
| class and attributes | local classes and properties | PROV classes/properties | local handles in domain/range | [class_and_attributes.schema.py](examples/class_and_attributes.schema.py) |
| class only | local class hierarchy | external PROV superclass | internal `SubClassOf` handle | [class_only.schema.py](examples/class_only.schema.py) |
| attributes only | local properties | reused `prov:used` | external domain/range and no-domain variants | [attributes_only.schema.py](examples/attributes_only.schema.py) |
| subsection and child attributes | local subsection/value properties | QUDT/PROV reuse | parent/child handles in domain/range | [subsections_and_attributes.schema.py](examples/subsections_and_attributes.schema.py) |
| minimal onboarding | local class/property | external BFO superclass | declaration keywords | [simple_sample.schema.py](examples/simple_sample.schema.py) |
| observation model | local SOSA-specialized classes | SOSA and QUDT | restrictions over mapped fields | [sensor_observation.schema.py](examples/sensor_observation.schema.py) |
| advanced OWL grammar | local family ontology | standard OWL/XSD terms | scoped cross-references | [owl_axioms.schema.py](examples/owl_axioms.schema.py) |
| scientific workflow | three local XPS entities | PROV/DCAT/QUDT/DCTERMS | nested restrictions and expressions | [xps_measurement.schema.py](examples/xps_measurement.schema.py) |
| class hierarchy only | four explicit local classes | PROV, BFO, and DCAT superclasses | internal and external subclass edges | [class_hierarchy.schema.py](examples/class_hierarchy.schema.py) |
| sections as relation endpoints | Experiment, Instrument, Sample, Result | PROV/DCAT superclasses | sections used as domain/range classes | [section_object_relations.schema.py](examples/section_object_relations.schema.py) |
| defined classes | acquisitions and research resources | PROV/DCAT alignment | intersection, union, complement | [defined_classes.schema.py](examples/defined_classes.schema.py) |
| property ontology | assembly relation family | OWL characteristics | hierarchy, inverse, chain, domain/range | [property_axioms.schema.py](examples/property_axioms.schema.py) |
| datatype restrictions | temperature record classes | XSD datatypes | universal/value/cardinality restrictions | [data_restrictions.schema.py](examples/data_restrictions.schema.py) |
| individuals and facts | runs and instruments | PROV alignment | facts, types, same/different individuals | [individuals_and_facts.schema.py](examples/individuals_and_facts.schema.py) |

### 3.1 Simple — material sample and identifier

The developer wants to say: “A NOMAD `Sample` represents a material entity, and its
identifier is a functional string-valued property.” Neither the Python class nor the
`Quantity` implies OWL semantics; both declarations are explicit.

Executable schema: [examples/simple_sample.schema.py](examples/simple_sample.schema.py)

```python
from nomad.metainfo import MSection, Quantity
from nomad_semantic_mapper import *

@OntologyMap([
    # Usage: explicitly create the semantic class and connect it to BFO.
    Class(iri="https://nomad-lab.eu/onto/examples#Sample"),
    SubClassOf(iri="http://purl.obolibrary.org/obo/BFO_0000040"),
    Annotation(property="http://purl.org/dc/terms/title", literal="material sample"),
])
class Sample(MSection):
    sample_id = OntologyMap([
        # Usage: Quantity is ignored; this list explicitly creates the OWL property.
        DataProperty(
            iri="https://nomad-lab.eu/onto/examples#sampleId",
            characteristics=["FunctionalProperty"],
            domain=["Sample"],
            range=["xsd:string"],
        ),
    ])(Quantity(type=str))
```

Representative Turtle:

```turtle
:Sample a owl:Class ;
    rdfs:subClassOf <http://purl.obolibrary.org/obo/BFO_0000040> .
:sampleId a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain :Sample ; rdfs:range xsd:string .
```

### 3.2 Advanced — external-first XPS measurement

The developer wants to say: “An Al K-alpha XPS measurement is a PROV activity that
uses a sample, generates only XPS spectra, has exactly one QUDT excitation-energy
value, and records its operator and start time with published properties.” Only
three project terms are minted; the rest are PROV, DCAT, DCTERMS, and QUDT IRIs.

Executable schema: [examples/xps_measurement.schema.py](examples/xps_measurement.schema.py)

```python
@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/xps#AlKAlphaXpsMeasurement"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Activity"),
    # Usage: require at least one used PROV entity.
    SomeValuesFrom(property="sample", filler="http://www.w3.org/ns/prov#Entity"),
    # Usage: every generated result must be our Spectrum class.
    AllValuesFrom(property="spectrum", filler="Spectrum"),
    ExactCardinality(
        property="excitation_energy", count=1,
        filler="http://qudt.org/schema/qudt/QuantityValue",
    ),
    HasValue(property="excitation_energy", value="AlKAlphaEnergy"),
])
class AlKAlphaXpsMeasurement(MSection):
    sample = OntologyMap([
        # Direct one-to-one reuse; no local property is minted.
        ObjectProperty(iri="http://www.w3.org/ns/prov#used"),
    ])(Quantity(type=str))
    spectrum = OntologyMap([
        ObjectProperty(iri="http://www.w3.org/ns/prov#generated"),
    ])(SubSection(sub_section="Spectrum"))
```

Representative Turtle:

```turtle
:AlKAlphaXpsMeasurement a owl:Class ;
    rdfs:subClassOf prov:Activity,
        [ a owl:Restriction ; owl:onProperty prov:used ;
          owl:someValuesFrom prov:Entity ],
        [ a owl:Restriction ; owl:onProperty prov:generated ;
          owl:allValuesFrom :Spectrum ],
        [ a owl:Restriction ; owl:onProperty qudt:quantityValue ;
          owl:onClass qudt:QuantityValue ; owl:qualifiedCardinality 1 ] .
```

The complete generated graph is [ontology.ttl](ontology.ttl).

### 3.3 Complex — composed expressions and axiom families

The developer wants a family vocabulary containing a guardian as the intersection
of a person and a parental restriction, an age group as a union, a non-adult as a
complement, an enumerated family, inverse/chained properties, cardinality/self
restrictions, and equality/inequality assertions.

Executable schema: [examples/owl_axioms.schema.py](examples/owl_axioms.schema.py)

```python
@OntologyMap([
    Class(iri="https://example.org/family#Guardian"),
    # Usage: compose a named class and a nested existential restriction.
    EquivalentTo(expression=IntersectionOf(operands=[
        "Person",
        SomeValuesFrom(property="Person.parent_of", filler="Person"),
    ])),
])
class Guardian(MSection):
    pass

@OntologyMap([
    Class(iri="https://example.org/family#AgeGroup"),
    EquivalentTo(expression=UnionOf(operands=["Adult", "Minor"])),
])
class AgeGroup(MSection):
    pass

@OntologyMap([
    Individual(iri="https://example.org/family#alice", type="Adult"),
    Fact(property="Person.parent_of", value="Bob"),
    Fact(property="Person.age", literal=42),
    SameAs(iri="AliceAlias"),
    AllDifferent(individuals=["Bob", "Charlie"]),
])
class Alice(MSection):
    pass
```

Representative Turtle:

```turtle
:Guardian owl:equivalentClass [
    owl:intersectionOf ( :Person [ a owl:Restriction ;
        owl:onProperty :parentOf ; owl:someValuesFrom :Person ] )
] .
:AgeGroup owl:equivalentClass [ owl:unionOf ( :Adult :Minor ) ] .
:FamilyMembers owl:equivalentClass [ owl:oneOf ( :alice :bob :charlie ) ] .
:grandparentOf owl:propertyChainAxiom ( :parentOf :parentOf ) .
```

#### Coverage across the executable examples

| Supported operation | Demonstrated in |
| --- | --- |
| `Class`, `ObjectProperty`, `DataProperty`, `Individual`, `AnnotationProperty` | simple description, XPS, sensor, complex |
| `SubClassOf`, `EquivalentTo`, `DisjointWith`, `AllDisjoint` | XPS and complex |
| `SubPropertyOf`, `InverseOf`, `Domain`, `Range`, `PropertyChain` | complex |
| `IntersectionOf`, `UnionOf`, `ComplementOf`, `OneOf`, `Inverse` | complex |
| `SomeValuesFrom`, `AllValuesFrom`, `ExactCardinality`, `HasValue` | XPS |
| `MinCardinality`, `MaxCardinality`, `HasSelf` | complex |
| `Fact`, `Type`, `SameAs`, `DifferentFrom`, `AllDifferent` | complex |
| `Annotation` | all examples |
| property characteristics | simple, sensor, and complex |

The SOSA/QUDT companion is
[examples/sensor_observation.schema.py](examples/sensor_observation.schema.py).

### 3.4 Placement-specific patterns

These examples answer a separate question from OWL expressiveness: **where may a
mapping be attached in a NOMAD schema?**

#### Class mapping only

In [class_only.schema.py](examples/class_only.schema.py), attributes remain ordinary
NOMAD definitions. The OWL hierarchy exists only because both semantic operations
are written explicitly:

```python
@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/examples#XpsActivity"),
    SubClassOf(iri="ResearchActivity"),  # internal mapping handle
])
class XpsActivity(ResearchActivity):
    beam_energy = Quantity(type=float)  # no mapping, therefore no OWL property
```

```turtle
:XpsActivity a owl:Class ; rdfs:subClassOf :ResearchActivity .
```

The Python inheritance happens to look similar, but the compiler does not read it.
Removing `SubClassOf` removes the OWL relationship while leaving Python unchanged.

#### Attribute mapping only

In [attributes_only.schema.py](examples/attributes_only.schema.py), the containing
Python class has no semantic declaration. Its mapped attributes still create OWL
properties. One has external domain/range cross-maps, one directly reuses an
external property, and one intentionally has no domain/range:

```python
class MeasurementRecord(MSection):  # no Class(...) declaration
    result = OntologyMap([
        ObjectProperty(iri="https://nomad-lab.eu/onto/examples#hasResult"),
        Domain(iri="http://www.w3.org/ns/prov#Activity"),
        Range(iri="http://www.w3.org/ns/prov#Entity"),
    ])(Quantity(type=str))

    free_text = OntologyMap([
        DataProperty(iri="https://nomad-lab.eu/onto/examples#freeText"),
        # Deliberately no domain or range.
    ])(Quantity(type=str))
```

```turtle
:hasResult a owl:ObjectProperty ;
    rdfs:domain prov:Activity ; rdfs:range prov:Entity .
:freeText a owl:DatatypeProperty .
```

No OWL class is generated for `MeasurementRecord`.

#### Class and attribute mappings together

[class_and_attributes.schema.py](examples/class_and_attributes.schema.py) combines
local classes, a local property whose domain/range reference those classes, and
direct reuse of `prov:used`:

```python
result = OntologyMap([
    ObjectProperty(
        iri="https://nomad-lab.eu/onto/examples#hasResult",
        domain=["Measurement"],
        range=["Result"],
    ),
])(SubSection(sub_section="Result"))
```

The mapping declares the `result` relation. It does not declare the `SubSection`
instance as an OWL object.

#### Subsection and child-attribute mappings

[subsections_and_attributes.schema.py](examples/subsections_and_attributes.schema.py)
maps a repeating subsection relation and then independently maps fields inside the
child section:

```python
results = OntologyMap([
    ObjectProperty(
        iri="https://nomad-lab.eu/onto/examples#hasResult",
        domain=["Experiment"], range=["Result"],
    ),
])(SubSection(sub_section="Result", repeats=True))
```

```turtle
:hasResult a owl:ObjectProperty ;
    rdfs:domain :Experiment ; rdfs:range :Result .
:numericValue a owl:DatatypeProperty ;
    rdfs:domain :Result ; rdfs:range xsd:double .
```

`results` is the semantic property handle; `SubSection(...)` remains NOMAD grammar.

### 3.5 Additional class-centered modeling examples

The following executable files focus on semantic structures that are easy to miss
when looking only at attribute-property examples:

- [class_hierarchy.schema.py](examples/class_hierarchy.schema.py) declares an OWL
  hierarchy independently of a deliberately different Python inheritance tree.
- [section_object_relations.schema.py](examples/section_object_relations.schema.py)
  turns explicitly mapped NOMAD sections into the domain and range of object
  properties, including a repeating subsection relation.
- [defined_classes.schema.py](examples/defined_classes.schema.py) defines classes
  through intersections, unions, complements, and nested restrictions.
- [property_axioms.schema.py](examples/property_axioms.schema.py) treats relations as
  a property ontology with subproperties, inverse properties, characteristics, and
  a property chain.
- [data_restrictions.schema.py](examples/data_restrictions.schema.py) applies
  universal, exact, minimum, maximum, and literal-value restrictions to data
  properties.
- [individuals_and_facts.schema.py](examples/individuals_and_facts.schema.py)
  declares named individuals and connects them using object/data facts, additional
  types, equality, and inequality.

For example, using mapped sections as object-property endpoints is explicit:

```python
@OntologyMap([Class(iri="https://nomad-lab.eu/onto/section-example#Experiment")])
class Experiment(MSection):
    instrument = OntologyMap([
        ObjectProperty(
            iri="https://nomad-lab.eu/onto/section-example#hasInstrument",
            domain=["Experiment"],
            range=["Instrument"],
        ),
    ])(Quantity(type="Instrument"))
```

```turtle
:Experiment a owl:Class .
:Instrument a owl:Class .
:hasInstrument a owl:ObjectProperty ;
    rdfs:domain :Experiment ;
    rdfs:range :Instrument .
```

The ontology uses the mapped section classes. It does not turn the assigned NOMAD
`Quantity` into an OWL individual, class, or property.

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



For maintainers extending the grammar or pipeline, continue with
[TECHNICAL.md](TECHNICAL.md).
