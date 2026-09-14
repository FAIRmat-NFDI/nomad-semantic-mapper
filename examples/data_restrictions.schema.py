"""Datatype-property restrictions on explicitly mapped section classes.

Expected RDF shape (abridged)::

    :TemperatureRecord rdfs:subClassOf
        [ owl:onProperty :value ; owl:allValuesFrom xsd:double ],
        [ owl:onProperty :value ; owl:qualifiedCardinality 1 ] .
    :FreezingPointRecord rdfs:subClassOf
        [ owl:onProperty :value ; owl:hasValue 273.15 ] .
"""

from nomad.metainfo import MSection, Quantity
from nomad_semantic_mapper import *


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/data-example#TemperatureRecord"),
    AllValuesFrom(property="value", filler="xsd:double"),
    ExactCardinality(property="value", count=1, filler="xsd:double"),
    MinCardinality(property="quality_code", count=0, filler="xsd:string"),
    MaxCardinality(property="quality_code", count=1, filler="xsd:string"),
])
class TemperatureRecord(MSection):
    value = OntologyMap([
        DataProperty(
            iri="https://nomad-lab.eu/onto/data-example#value",
            characteristics=["FunctionalProperty"],
            domain=["TemperatureRecord"], range=["xsd:double"],
        ),
    ])(Quantity(type=float, unit="kelvin"))

    quality_code = OntologyMap([
        DataProperty(
            iri="https://nomad-lab.eu/onto/data-example#qualityCode",
            domain=["TemperatureRecord"], range=["xsd:string"],
        ),
    ])(Quantity(type=str))


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/data-example#FreezingPointRecord"),
    SubClassOf(iri="TemperatureRecord"),
    HasValue(property="TemperatureRecord.value", literal=273.15),
])
class FreezingPointRecord(MSection):
    pass
