"""Mappings on both classes and their attributes.

This demonstrates local declarations, external reuse, and cross-mapping through
domain/range handles. Python inheritance remains irrelevant to the OWL result.

Expected RDF shape (abridged)::

    :Measurement rdfs:subClassOf prov:Activity .
    :hasResult rdfs:domain :Measurement ; rdfs:range :Result .
    prov:used a owl:ObjectProperty .
"""

from nomad.metainfo import MSection, Quantity, SubSection

from nomad_semantic_mapper import *


@OntologyMap([
    # Local OWL class, explicitly related to the external PROV class.
    Class(iri="https://nomad-lab.eu/onto/examples#Measurement"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Activity"),
])
class Measurement(MSection):
    result = OntologyMap([
        # Local property cross-mapped to local class handles.
        ObjectProperty(
            iri="https://nomad-lab.eu/onto/examples#hasResult",
            domain=["Measurement"],
            range=["Result"],
        ),
    ])(SubSection(sub_section="Result"))

    sample = OntologyMap([
        # Exact external reuse. No local property IRI is created.
        ObjectProperty(iri="http://www.w3.org/ns/prov#used"),
    ])(Quantity(type=str))

    method_name = OntologyMap([
        # Local attribute property with an internal domain and XSD range.
        DataProperty(
            iri="https://nomad-lab.eu/onto/examples#methodName",
            domain=["Measurement"],
            range=["xsd:string"],
        ),
    ])(Quantity(type=str))


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/examples#Result"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Entity"),
])
class Result(MSection):
    pass
