"""Object-property hierarchy, inverse relation, characteristics, and chain.

Expected RDF shape (abridged)::

    :hasDirectPart rdfs:subPropertyOf :hasPart .
    :isPartOf owl:inverseOf :hasPart .
    :hasAncestorPart owl:propertyChainAxiom ( :hasPart :hasPart ) .
"""

from nomad.metainfo import MSection, Quantity
from nomad_semantic_mapper import *


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/property-example#Assembly"),
])
class Assembly(MSection):
    has_part = OntologyMap([
        ObjectProperty(
            iri="https://nomad-lab.eu/onto/property-example#hasPart",
            characteristics=["TransitiveProperty"],
            domain=["Assembly"], range=["Assembly"],
        ),
        InverseOf(iri="is_part_of"),
    ])(Quantity(type="Assembly"))

    is_part_of = OntologyMap([
        ObjectProperty(
            iri="https://nomad-lab.eu/onto/property-example#isPartOf",
            domain=["Assembly"], range=["Assembly"],
        ),
    ])(Quantity(type="Assembly"))

    has_direct_part = OntologyMap([
        ObjectProperty(
            iri="https://nomad-lab.eu/onto/property-example#hasDirectPart",
            characteristics=["AsymmetricProperty", "IrreflexiveProperty"],
        ),
        SubPropertyOf(iri="has_part"),
        Domain(iri="Assembly"),
        Range(iri="Assembly"),
    ])(Quantity(type="Assembly"))

    has_ancestor_part = OntologyMap([
        ObjectProperty(iri="https://nomad-lab.eu/onto/property-example#hasAncestorPart"),
        PropertyChain(properties=["has_part", "has_part"]),
    ])(Quantity(type="Assembly"))
