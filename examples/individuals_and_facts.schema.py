"""Classes, named individuals, types, facts, equality, and inequality.

Expected RDF shape (abridged)::

    :run-001 a :MeasurementRun ; :usedInstrument :instrument-001 .
    :instrument-001 :serialNumber "SN-001" ; owl:sameAs :instrument-primary .
    _:different a owl:AllDifferent ; owl:distinctMembers ( :run-001 :run-002 ) .
"""

from nomad.metainfo import MSection, Quantity
from nomad_semantic_mapper import *


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/individual-example#Instrument"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Entity"),
])
class Instrument(MSection):
    serial_number = OntologyMap([
        DataProperty(
            iri="https://nomad-lab.eu/onto/individual-example#serialNumber",
            domain=["Instrument"], range=["xsd:string"],
        ),
    ])(Quantity(type=str))


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/individual-example#MeasurementRun"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Activity"),
])
class MeasurementRun(MSection):
    used_instrument = OntologyMap([
        ObjectProperty(
            iri="https://nomad-lab.eu/onto/individual-example#usedInstrument",
            domain=["MeasurementRun"], range=["Instrument"],
        ),
        SubPropertyOf(iri="http://www.w3.org/ns/prov#used"),
    ])(Quantity(type="Instrument"))


@OntologyMap([
    Individual(
        iri="https://nomad-lab.eu/onto/individual-example#instrument-001",
        type="Instrument",
    ),
    Fact(property="Instrument.serial_number", literal="SN-001"),
    SameAs(iri="PrimaryInstrument"),
])
class Instrument001(MSection):
    pass


@OntologyMap([
    Individual(
        iri="https://nomad-lab.eu/onto/individual-example#instrument-primary",
        type="Instrument",
    ),
])
class PrimaryInstrument(MSection):
    pass


@OntologyMap([
    Individual(
        iri="https://nomad-lab.eu/onto/individual-example#run-001",
        type="MeasurementRun",
    ),
    Fact(property="MeasurementRun.used_instrument", value="Instrument001"),
    Type(iri="http://www.w3.org/ns/prov#Activity"),
    DifferentFrom(iri="Run002"),
    AllDifferent(individuals=["Run002"]),
])
class Run001(MSection):
    pass


@OntologyMap([
    Individual(
        iri="https://nomad-lab.eu/onto/individual-example#run-002",
        type="MeasurementRun",
    ),
])
class Run002(MSection):
    pass
