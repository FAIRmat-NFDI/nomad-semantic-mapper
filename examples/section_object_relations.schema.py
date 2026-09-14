"""NOMAD sections used explicitly as object-property domain and range classes.

The sections become OWL classes only because they carry ``Class`` operations. The
attributes ``instrument``, ``sample``, and ``results`` become relations between
those classes; their assigned Quantity/SubSection definitions remain NOMAD objects.

Expected RDF shape (abridged)::

    :hasInstrument rdfs:domain :Experiment ; rdfs:range :Instrument .
    :hasSample rdfs:domain :Experiment ; rdfs:range :Sample .
    :hasResult rdfs:domain :Experiment ; rdfs:range :Result .
"""

from nomad.metainfo import MSection, Quantity, SubSection
from nomad_semantic_mapper import *


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/section-example#Experiment"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Activity"),
    ExactCardinality(property="instrument", count=1, filler="Instrument"),
    SomeValuesFrom(property="sample", filler="Sample"),
    AllValuesFrom(property="results", filler="Result"),
])
class Experiment(MSection):
    instrument = OntologyMap([
        ObjectProperty(
            iri="https://nomad-lab.eu/onto/section-example#hasInstrument",
            domain=["Experiment"],
            range=["Instrument"],
        ),
    ])(Quantity(type="Instrument"))

    sample = OntologyMap([
        ObjectProperty(
            iri="https://nomad-lab.eu/onto/section-example#hasSample",
            domain=["Experiment"],
            range=["Sample"],
        ),
        SubPropertyOf(iri="http://www.w3.org/ns/prov#used"),
    ])(Quantity(type="Sample"))

    results = OntologyMap([
        ObjectProperty(
            iri="https://nomad-lab.eu/onto/section-example#hasResult",
            domain=["Experiment"],
            range=["Result"],
        ),
        SubPropertyOf(iri="http://www.w3.org/ns/prov#generated"),
    ])(SubSection(sub_section="Result", repeats=True))


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/section-example#Instrument"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Entity"),
])
class Instrument(MSection):
    pass


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/section-example#Sample"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Entity"),
])
class Sample(MSection):
    pass


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/section-example#Result"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Entity"),
    SubClassOf(iri="http://www.w3.org/ns/dcat#Dataset"),
])
class Result(MSection):
    pass
