"""Mappings on a SubSection assignment and attributes inside the child section.

``results`` describes the subsection relation, not the SubSection object. ``value``
and ``unit`` describe child attributes, not their Quantity objects.

Expected RDF shape (abridged)::

    :hasResult rdfs:domain :Experiment ; rdfs:range :Result .
    :numericValue rdfs:domain :Result ; rdfs:range xsd:double .
    qudt:hasUnit a owl:ObjectProperty .
"""

from nomad.metainfo import MSection, Quantity, SubSection

from nomad_semantic_mapper import *


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/examples#Experiment"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Activity"),
])
class Experiment(MSection):
    results = OntologyMap([
        # Mapping belongs to the `results` attribute; SubSection is only NOMAD grammar.
        ObjectProperty(
            iri="https://nomad-lab.eu/onto/examples#hasResult",
            domain=["Experiment"],
            range=["Result"],
        ),
    ])(SubSection(sub_section="Result", repeats=True))


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/examples#Result"),
    SubClassOf(iri="http://qudt.org/schema/qudt/QuantityValue"),
])
class Result(MSection):
    value = OntologyMap([
        # Local child attribute with internal domain cross-reference.
        DataProperty(
            iri="https://nomad-lab.eu/onto/examples#numericValue",
            domain=["Result"],
            range=["xsd:double"],
        ),
    ])(Quantity(type=float))

    unit = OntologyMap([
        # Published external property reused directly.
        ObjectProperty(iri="http://qudt.org/schema/qudt/hasUnit"),
    ])(Quantity(type=str))
