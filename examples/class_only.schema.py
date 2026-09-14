"""Ontology mappings only on classes; attributes remain ordinary NOMAD fields.

Expected RDF shape (abridged)::

    :ResearchActivity rdfs:subClassOf prov:Activity .
    :XpsActivity rdfs:subClassOf :ResearchActivity .

The undecorated ``title`` and ``beam_energy`` fields emit no OWL entities.
"""

from nomad.metainfo import MSection, Quantity

from nomad_semantic_mapper import *


@OntologyMap([
    # Local class mapped to an external ontology class.
    Class(iri="https://nomad-lab.eu/onto/examples#ResearchActivity"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Activity"),
])
class ResearchActivity(MSection):
    # No OntologyMap: this attribute has no emitted semantic declaration.
    title = Quantity(type=str)


@OntologyMap([
    # Internal cross-reference between two explicitly mapped classes.
    Class(iri="https://nomad-lab.eu/onto/examples#XpsActivity"),
    SubClassOf(iri="ResearchActivity"),
    Annotation(property="http://purl.org/dc/terms/title", literal="XPS activity"),
])
class XpsActivity(ResearchActivity):
    # Python inheritance does not create the OWL subclass axiom above.
    beam_energy = Quantity(type=float, unit="electron_volt")
