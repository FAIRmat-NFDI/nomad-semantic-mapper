"""Compact, real XPS schema example.

Only three IRIs are owned by this example: the measurement class, spectrum class,
and Al K-alpha energy individual. Every field reuses a published external property.
NOMAD supplies only Python handles; OntologyMap supplies all OWL meaning.

The converter reads this file as syntax and never imports ``nomad``. Consequently,
conversion works even when the NOMAD package is not installed.

Expected RDF shape (abridged)::

    :AlKAlphaXpsMeasurement rdfs:subClassOf prov:Activity,
        [ owl:onProperty prov:used ; owl:someValuesFrom prov:Entity ],
        [ owl:onProperty prov:generated ; owl:allValuesFrom :Spectrum ] .
    :AlKAlphaEnergy qudt:numericValue 1486.6 ; qudt:hasUnit unit:EV .
"""

from nomad.metainfo import MSection, Quantity, SubSection

from nomad_semantic_mapper import *


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/xps#AlKAlphaXpsMeasurement"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Activity"),
    # Existential, universal, cardinality, and value restrictions.
    SomeValuesFrom(property="sample", filler="http://www.w3.org/ns/prov#Entity"),
    AllValuesFrom(property="spectrum", filler="Spectrum"),
    ExactCardinality(
        property="excitation_energy",
        count=1,
        filler="http://qudt.org/schema/qudt/QuantityValue",
    ),
    HasValue(property="excitation_energy", value="AlKAlphaEnergy"),
    Annotation(
        property="http://purl.org/dc/terms/title",
        literal="Al K-alpha XPS measurement",
    ),
])
class AlKAlphaXpsMeasurement(MSection):
    # Assignment names are handles only. The same pattern works for any Quantity,
    # SubSection, DataFrame, or other assignment -- it is not special to `system`.
    sample = OntologyMap([
        ObjectProperty(iri="http://www.w3.org/ns/prov#used"),
    ])(Quantity(type=str))

    operator = OntologyMap([
        ObjectProperty(iri="http://www.w3.org/ns/prov#wasAssociatedWith"),
    ])(Quantity(type=str))

    spectrum = OntologyMap([
        ObjectProperty(iri="http://www.w3.org/ns/prov#generated"),
    ])(SubSection(sub_section="Spectrum"))

    excitation_energy = OntologyMap([
        ObjectProperty(iri="http://qudt.org/schema/qudt/quantityValue"),
    ])(Quantity(type=float, unit="electron_volt"))

    started_at = OntologyMap([
        DataProperty(iri="http://www.w3.org/ns/prov#startedAtTime"),
    ])(Quantity(type=str))


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/xps#Spectrum"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Entity"),
    SubClassOf(iri="http://www.w3.org/ns/dcat#Dataset"),
    Annotation(property="http://purl.org/dc/terms/title", literal="XPS spectrum"),
    # Fully declarative intersection: no raw Owlready2/Python code is exposed.
    EquivalentTo(expression=IntersectionOf(operands=[
        "http://www.w3.org/ns/prov#Entity",
        "http://www.w3.org/ns/dcat#Dataset",
        SomeValuesFrom(
            property="http://www.w3.org/ns/prov#wasGeneratedBy",
            filler="AlKAlphaXpsMeasurement",
        ),
    ])),
])
class Spectrum(MSection):
    generated_by = OntologyMap([
        ObjectProperty(iri="http://www.w3.org/ns/prov#wasGeneratedBy"),
    ])(Quantity(type=str))


@OntologyMap([
    Individual(
        iri="https://nomad-lab.eu/onto/xps#AlKAlphaEnergy",
        type="http://qudt.org/schema/qudt/QuantityValue",
    ),
    Annotation(property="http://qudt.org/schema/qudt/numericValue", literal=1486.6),
    Fact(property="http://qudt.org/schema/qudt/hasUnit", value="http://qudt.org/vocab/unit/EV"),
    Fact(
        property="http://qudt.org/schema/qudt/hasQuantityKind",
        value="http://qudt.org/vocab/quantitykind/Energy",
    ),
    Annotation(
        property="http://purl.org/dc/terms/title",
        literal="Al K-alpha excitation energy",
    ),
])
class AlKAlphaEnergy(MSection):
    pass
