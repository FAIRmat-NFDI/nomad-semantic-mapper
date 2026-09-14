"""Class-centric ontology design with no mapped attributes.

Python inheritance is intentionally different from the OWL hierarchy below. Every
OWL class and every subclass edge is declared explicitly.

Expected RDF shape (abridged)::

    :ResearchEntity rdfs:subClassOf prov:Entity .
    :MaterialSample rdfs:subClassOf :ResearchEntity, BFO:0000040 .
    :DatasetRecord rdfs:subClassOf :ResearchEntity, dcat:Dataset .
"""

from nomad.metainfo import MSection, Quantity
from nomad_semantic_mapper import *


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/class-example#ResearchEntity"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Entity"),
])
class ResearchEntity(MSection):
    internal_note = Quantity(type=str)  # deliberately absent from the ontology


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/class-example#MaterialSample"),
    SubClassOf(iri="ResearchEntity"),
    SubClassOf(iri="http://purl.obolibrary.org/obo/BFO_0000040"),
    DisjointWith(iri="DatasetRecord"),
])
class MaterialSample(MSection):
    pass


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/class-example#DatasetRecord"),
    SubClassOf(iri="ResearchEntity"),
    SubClassOf(iri="http://www.w3.org/ns/dcat#Dataset"),
])
class DatasetRecord(MaterialSample):
    # Python says MaterialSample; OWL says ResearchEntity + dcat:Dataset.
    pass


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/class-example#ProcessedDataset"),
    SubClassOf(iri="DatasetRecord"),
    Annotation(property="http://purl.org/dc/terms/title", literal="processed dataset"),
])
class ProcessedDataset(MSection):
    pass
