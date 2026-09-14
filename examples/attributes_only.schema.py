"""Ontology mappings only on attributes; the containing class is not mapped.

The ontology contains properties, but no class is generated for Python
``MeasurementRecord``. Domain/range may be external, or omitted entirely.

Expected RDF shape (abridged)::

    :hasResult rdfs:domain prov:Activity ; rdfs:range prov:Entity .
    prov:used a owl:ObjectProperty .
    :freeText a owl:DatatypeProperty .
"""

from nomad.metainfo import MSection, Quantity

from nomad_semantic_mapper import *


class MeasurementRecord(MSection):
    result = OntologyMap([
        # Local property with external cross-mapped domain and range.
        ObjectProperty(iri="https://nomad-lab.eu/onto/examples#hasResult"),
        Domain(iri="http://www.w3.org/ns/prov#Activity"),
        Range(iri="http://www.w3.org/ns/prov#Entity"),
    ])(Quantity(type=str))

    sample = OntologyMap([
        # External property reused without adding global domain/range claims.
        ObjectProperty(iri="http://www.w3.org/ns/prov#used"),
    ])(Quantity(type=str))

    free_text = OntologyMap([
        # Local property without domain or range.
        DataProperty(iri="https://nomad-lab.eu/onto/examples#freeText"),
    ])(Quantity(type=str))

    # No OntologyMap: ignored by the semantic compiler.
    internal_counter = Quantity(type=int)
