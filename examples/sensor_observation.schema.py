"""SOSA/QUDT temperature observation with external-first mappings.

Semantics
---------
``TemperatureObservation`` is a SOSA observation that has exactly one QUDT
quantity-value result. Each NOMAD assignment maps directly to a published SOSA
property; no Python class or Quantity is automatically treated as an OWL entity.

Expected RDF shape (abridged)::

    :TemperatureObservation rdfs:subClassOf sosa:Observation,
        [ a owl:Restriction ; owl:onProperty sosa:hasResult ;
          owl:qualifiedCardinality 1 ; owl:onClass qudt:QuantityValue ] .
    :TemperatureResult rdfs:subClassOf qudt:QuantityValue .
"""

from nomad.metainfo import MSection, Quantity, SubSection

from nomad_semantic_mapper import *


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/examples#TemperatureObservation"),
    SubClassOf(iri="http://www.w3.org/ns/sosa/Observation"),
    ExactCardinality(
        property="result",
        count=1,
        filler="TemperatureResult",
    ),
    SomeValuesFrom(
        property="feature_of_interest",
        filler="http://www.w3.org/ns/sosa/FeatureOfInterest",
    ),
    Annotation(
        property="http://purl.org/dc/terms/title",
        literal="Temperature observation",
    ),
])
class TemperatureObservation(MSection):
    result = OntologyMap([
        ObjectProperty(iri="http://www.w3.org/ns/sosa/hasResult"),
    ])(SubSection(sub_section="TemperatureResult"))

    feature_of_interest = OntologyMap([
        ObjectProperty(iri="http://www.w3.org/ns/sosa/hasFeatureOfInterest"),
    ])(Quantity(type=str))

    made_by_sensor = OntologyMap([
        ObjectProperty(iri="http://www.w3.org/ns/sosa/madeBySensor"),
    ])(Quantity(type=str))

    result_time = OntologyMap([
        DataProperty(iri="http://www.w3.org/ns/sosa/resultTime"),
    ])(Quantity(type=str))


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/examples#TemperatureResult"),
    SubClassOf(iri="http://qudt.org/schema/qudt/QuantityValue"),
])
class TemperatureResult(MSection):
    numeric_value = OntologyMap([
        AnnotationProperty(iri="http://qudt.org/schema/qudt/numericValue"),
    ])(Quantity(type=float, unit="kelvin"))
