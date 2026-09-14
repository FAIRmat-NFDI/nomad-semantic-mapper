"""Decorator-only catalog of advanced OWL expressions and axioms.

This deliberately uses example-owned IRIs because it defines a small fictional
family vocabulary. The operations themselves map to standard OWL 2 RDF constructs.

Representative RDF (abridged)::

    :Guardian owl:equivalentClass [ owl:intersectionOf
        ( :Person [ owl:onProperty :parentOf ; owl:someValuesFrom :Person ] ) ] .
    :AgeGroup owl:equivalentClass [ owl:unionOf ( :Adult :Minor ) ] .
    :FamilyMembers owl:equivalentClass [ owl:oneOf ( :alice :bob :charlie ) ] .
    :grandparentOf owl:propertyChainAxiom ( :parentOf :parentOf ) .
"""

from nomad.metainfo import MSection, Quantity

from nomad_semantic_mapper import *


@OntologyMap([
    Class(iri="https://example.org/family#Person"),
    Annotation(property="label", literal="person"),
])
class Person(MSection):
    related_to = OntologyMap([
        ObjectProperty(
            iri="https://example.org/family#relatedTo",
            characteristics=["SymmetricProperty"],
        ),
    ])(Quantity(type=str))

    parent_of = OntologyMap([
        ObjectProperty(
            iri="https://example.org/family#parentOf",
            domain=["Person"],
            range=["Person"],
        ),
        SubPropertyOf(iri="related_to"),
        InverseOf(iri="child_of"),
    ])(Quantity(type=str))

    child_of = OntologyMap([
        ObjectProperty(iri="https://example.org/family#childOf"),
        Domain(iri="Person"),
        Range(iri="Person"),
    ])(Quantity(type=str))

    grandparent_of = OntologyMap([
        ObjectProperty(iri="https://example.org/family#grandparentOf"),
        PropertyChain(properties=["parent_of", "parent_of"]),
    ])(Quantity(type=str))

    age = OntologyMap([
        DataProperty(
            iri="https://example.org/family#age",
            characteristics=["FunctionalProperty"],
            domain=["Person"],
            range=["xsd:nonNegativeInteger"],
        ),
    ])(Quantity(type=int))


@OntologyMap([
    Class(iri="https://example.org/family#Guardian"),
    EquivalentTo(expression=IntersectionOf(operands=[
        "Person",
        SomeValuesFrom(property="Person.parent_of", filler="Person"),
    ])),
])
class Guardian(MSection):
    pass


@OntologyMap([
    Class(iri="https://example.org/family#Adult"),
    SubClassOf(iri="Person"),
    DisjointWith(iri="Minor"),
    AllDisjoint(entities=["Minor"]),
])
class Adult(MSection):
    pass


@OntologyMap([
    Class(iri="https://example.org/family#Minor"),
    SubClassOf(iri="Person"),
])
class Minor(MSection):
    pass


@OntologyMap([
    Class(iri="https://example.org/family#AgeGroup"),
    EquivalentTo(expression=UnionOf(operands=["Adult", "Minor"])),
])
class AgeGroup(MSection):
    pass


@OntologyMap([
    Class(iri="https://example.org/family#NonAdult"),
    EquivalentTo(expression=ComplementOf(operand="Adult")),
])
class NonAdult(MSection):
    pass


@OntologyMap([
    Class(iri="https://example.org/family#EstablishedGuardian"),
    SubClassOf(iri="Guardian"),
    MinCardinality(property="Person.parent_of", count=1, filler="Person"),
    MaxCardinality(property="Person.parent_of", count=10, filler="Person"),
])
class EstablishedGuardian(MSection):
    pass


@OntologyMap([
    Class(iri="https://example.org/family#SelfRelatedPerson"),
    SubClassOf(iri="Person"),
    HasSelf(property="Person.related_to"),
    SomeValuesFrom(
        property=Inverse(property="Person.parent_of"),
        filler="Person",
    ),
])
class SelfRelatedPerson(MSection):
    pass


@OntologyMap([
    Class(iri="https://example.org/family#FamilyMembers"),
    EquivalentTo(expression=OneOf(individuals=["Alice", "Bob", "Charlie"])),
])
class FamilyMembers(MSection):
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


@OntologyMap([
    Individual(iri="https://example.org/family#bob", type="Minor"),
    DifferentFrom(iri="Charlie"),
])
class Bob(MSection):
    pass


@OntologyMap([
    Individual(iri="https://example.org/family#charlie", type="Person"),
    Type(expression=ComplementOf(operand="Guardian")),
])
class Charlie(MSection):
    pass


@OntologyMap([
    Individual(iri="https://example.org/family#alice-alias", type="Person"),
])
class AliceAlias(MSection):
    pass
