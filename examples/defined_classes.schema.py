"""Defined classes built from Boolean expressions and nested restrictions.

Expected RDF shape (abridged)::

    :SuccessfulAcquisition owl:equivalentClass [ owl:intersectionOf
        ( :Acquisition [ owl:onProperty :hasOutput ; owl:someValuesFrom :Dataset ] ) ] .
    :ResearchResource owl:equivalentClass [ owl:unionOf ( :Sample :Dataset ) ] .
    :NonDataset owl:equivalentClass [ owl:complementOf :Dataset ] .
"""

from nomad.metainfo import MSection, Quantity
from nomad_semantic_mapper import *


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/defined-example#Acquisition"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Activity"),
])
class Acquisition(MSection):
    output = OntologyMap([
        ObjectProperty(
            iri="https://nomad-lab.eu/onto/defined-example#hasOutput",
            domain=["Acquisition"], range=["Dataset"],
        ),
    ])(Quantity(type="Dataset"))


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/defined-example#Sample"),
    SubClassOf(iri="http://www.w3.org/ns/prov#Entity"),
])
class Sample(MSection):
    pass


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/defined-example#Dataset"),
    SubClassOf(iri="http://www.w3.org/ns/dcat#Dataset"),
])
class Dataset(MSection):
    pass


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/defined-example#SuccessfulAcquisition"),
    EquivalentTo(expression=IntersectionOf(operands=[
        "Acquisition",
        SomeValuesFrom(property="Acquisition.output", filler="Dataset"),
    ])),
])
class SuccessfulAcquisition(MSection):
    pass


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/defined-example#ResearchResource"),
    EquivalentTo(expression=UnionOf(operands=["Sample", "Dataset"])),
])
class ResearchResource(MSection):
    pass


@OntologyMap([
    Class(iri="https://nomad-lab.eu/onto/defined-example#NonDataset"),
    EquivalentTo(expression=ComplementOf(operand="Dataset")),
])
class NonDataset(MSection):
    pass
