"""Minimal material sample mapping.

Semantics: Sample is a BFO material entity. ``sample_id`` is a functional local
datatype property whose values are strings.

Expected RDF shape (abridged)::

    :Sample rdfs:subClassOf <http://purl.obolibrary.org/obo/BFO_0000040> .
    :sampleId a owl:DatatypeProperty, owl:FunctionalProperty ;
        rdfs:domain :Sample ; rdfs:range xsd:string .
"""

from nomad.metainfo import MSection, Quantity

from nomad_semantic_mapper import *


@OntologyMap([
    # Usage: Python inheritance has no OWL meaning; this explicitly creates a class.
    Class(iri="https://nomad-lab.eu/onto/examples#Sample"),
    SubClassOf(iri="http://purl.obolibrary.org/obo/BFO_0000040"),
    Annotation(property="http://purl.org/dc/terms/title", literal="material sample"),
])
class Sample(MSection):
    sample_id = OntologyMap([
        # Usage: Quantity contributes only the handle; this list supplies semantics.
        DataProperty(
            iri="https://nomad-lab.eu/onto/examples#sampleId",
            characteristics=["FunctionalProperty"],
            domain=["Sample"],
            range=["xsd:string"],
        ),
    ])(Quantity(type=str))
