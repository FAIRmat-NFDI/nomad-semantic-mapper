"""Generated Owlready2 ontology code from xps_measurement.schema.py.

Do not edit; regenerate with nomad_semantic_mapper.py.

Every entity carries the IRI its schema declaration gave it. Nothing here reflects
the Python classes the schema was written with. External IRIs appear exactly as the
author wrote them; nothing checks that they resolve or that the result is consistent.
"""

import datetime
import io
import types
from pathlib import Path

from owlready2 import *

BASE_IRI = 'https://nomad-lab.eu/onto/xps#'

world = World()
ontology = world.get_ontology(BASE_IRI)

_external_cache = {}

_DATATYPES = {
    "xsd:string": str,
    "xsd:normalizedString": str,
    "xsd:anyURI": str,
    "xsd:integer": int,
    "xsd:int": int,
    "xsd:long": int,
    "xsd:nonNegativeInteger": int,
    "xsd:positiveInteger": int,
    "xsd:float": float,
    "xsd:double": float,
    "xsd:decimal": float,
    "xsd:boolean": bool,
    "xsd:date": datetime.date,
    "xsd:dateTime": datetime.datetime,
    "xsd:time": datetime.time,
}
_DATATYPES.update(
    {"http://www.w3.org/2001/XMLSchema#" + key.split(":", 1)[1]: value
     for key, value in list(_DATATYPES.items())}
)


def _split_iri(iri):
    """Namespace/fragment split. Deliberately forgiving; IRIs are trusted."""
    base, _, fragment = iri.partition("#")
    if fragment:
        return base + "#", fragment
    head, separator, tail = iri.rpartition("/")
    if separator and tail:
        return head + separator, tail
    head, separator, tail = iri.rpartition(":")
    if separator and tail:
        return head + separator, tail
    return BASE_IRI, iri


def _external(iri, parent=Thing):
    """Handle for an entity defined elsewhere. The IRI is taken on trust."""
    if iri in _external_cache:
        return _external_cache[iri]
    existing = world[iri]
    if existing is None:
        base, fragment = _split_iri(iri)
        namespace = world.get_ontology(base).get_namespace(base)
        with namespace:
            existing = types.new_class(fragment, (parent,))
    _external_cache[iri] = existing
    return existing


def _external_individual(iri):
    """Handle for an individual defined elsewhere. The IRI is taken on trust."""
    if iri in _external_cache:
        return _external_cache[iri]
    existing = world[iri]
    if existing is None:
        base, fragment = _split_iri(iri)
        namespace = world.get_ontology(base).get_namespace(base)
        existing = Thing(fragment, namespace=namespace)
    _external_cache[iri] = existing
    return existing


def _datatype(iri):
    """Map an XSD IRI to the Python type Owlready2 uses for it."""
    if iri in _DATATYPES:
        return _DATATYPES[iri]
    return _external(iri, Thing)


# --- namespaces ----------------------------------------------------------------
# One per declared IRI namespace. All belong to `ontology`, so a single
# ontology.save() emits every declared entity under the IRI its schema gave it.
_ns0 = ontology.get_namespace('https://nomad-lab.eu/onto/xps#')
_ns1 = ontology.get_namespace('http://www.w3.org/ns/prov#')
_ns2 = ontology.get_namespace('http://qudt.org/schema/qudt/')

# --- external references -------------------------------------------------------
# Materialised before any `with` block: Owlready2 forbids creating a namespace
# inside `with onto:`.
_external('http://qudt.org/schema/qudt/QuantityValue', Thing)
_external('http://www.w3.org/ns/prov#Activity', Thing)
_external('http://www.w3.org/ns/prov#Entity', Thing)
_external('http://purl.org/dc/terms/title', AnnotationProperty)
_external('http://www.w3.org/ns/dcat#Dataset', Thing)
_external('http://qudt.org/schema/qudt/numericValue', AnnotationProperty)
_external('http://qudt.org/schema/qudt/hasUnit', ObjectProperty)
_external_individual('http://qudt.org/vocab/unit/EV')
_external('http://qudt.org/schema/qudt/hasQuantityKind', ObjectProperty)
_external_individual('http://qudt.org/vocab/quantitykind/Energy')


# --- declarations --------------------------------------------------------------
with _ns0:
    AlKAlphaXpsMeasurement = types.new_class('AlKAlphaXpsMeasurement', (Thing,))  # AlKAlphaXpsMeasurement <- class AlKAlphaXpsMeasurement
    Spectrum = types.new_class('Spectrum', (Thing,))  # Spectrum <- class Spectrum

with _ns1:
    AlKAlphaXpsMeasurement_sample = types.new_class('used', (ObjectProperty,))  # AlKAlphaXpsMeasurement.sample <- Quantity(type=str)
    AlKAlphaXpsMeasurement_operator = types.new_class('wasAssociatedWith', (ObjectProperty,))  # AlKAlphaXpsMeasurement.operator <- Quantity(type=str)
    AlKAlphaXpsMeasurement_spectrum = types.new_class('generated', (ObjectProperty,))  # AlKAlphaXpsMeasurement.spectrum <- SubSection(sub_section='Spectrum')
    AlKAlphaXpsMeasurement_started_at = types.new_class('startedAtTime', (DataProperty,))  # AlKAlphaXpsMeasurement.started_at <- Quantity(type=str)
    Spectrum_generated_by = types.new_class('wasGeneratedBy', (ObjectProperty,))  # Spectrum.generated_by <- Quantity(type=str)

with _ns2:
    AlKAlphaXpsMeasurement_excitation_energy = types.new_class('quantityValue', (ObjectProperty,))  # AlKAlphaXpsMeasurement.excitation_energy <- Quantity(type=float, unit='electron_volt')

# --- individuals ---------------------------------------------------------------
with _ns0:
    AlKAlphaEnergy = _external('http://qudt.org/schema/qudt/QuantityValue', Thing)('AlKAlphaEnergy')  # AlKAlphaEnergy <- class AlKAlphaEnergy

# --- axioms --------------------------------------------------------------------
with ontology:
    AlKAlphaXpsMeasurement.is_a.append(_external('http://www.w3.org/ns/prov#Activity', Thing))
    AlKAlphaXpsMeasurement.is_a.append(AlKAlphaXpsMeasurement_sample.some(_external('http://www.w3.org/ns/prov#Entity', Thing)))
    AlKAlphaXpsMeasurement.is_a.append(AlKAlphaXpsMeasurement_spectrum.only(Spectrum))
    AlKAlphaXpsMeasurement.is_a.append(AlKAlphaXpsMeasurement_excitation_energy.exactly(1, _external('http://qudt.org/schema/qudt/QuantityValue', Thing)))
    AlKAlphaXpsMeasurement.is_a.append(AlKAlphaXpsMeasurement_excitation_energy.value(AlKAlphaEnergy))
    _external('http://purl.org/dc/terms/title', AnnotationProperty)[AlKAlphaXpsMeasurement].append('Al K-alpha XPS measurement')
    Spectrum.is_a.append(_external('http://www.w3.org/ns/prov#Entity', Thing))
    Spectrum.is_a.append(_external('http://www.w3.org/ns/dcat#Dataset', Thing))
    _external('http://purl.org/dc/terms/title', AnnotationProperty)[Spectrum].append('XPS spectrum')
    Spectrum.equivalent_to.append((_external('http://www.w3.org/ns/prov#Entity', Thing) & _external('http://www.w3.org/ns/dcat#Dataset', Thing) & Spectrum_generated_by.some(AlKAlphaXpsMeasurement)))
    _external('http://qudt.org/schema/qudt/numericValue', AnnotationProperty)[AlKAlphaEnergy].append(1486.6)
    _external('http://qudt.org/schema/qudt/hasUnit', ObjectProperty)[AlKAlphaEnergy].append(_external_individual('http://qudt.org/vocab/unit/EV'))
    _external('http://qudt.org/schema/qudt/hasQuantityKind', ObjectProperty)[AlKAlphaEnergy].append(_external_individual('http://qudt.org/vocab/quantitykind/Energy'))
    _external('http://purl.org/dc/terms/title', AnnotationProperty)[AlKAlphaEnergy].append('Al K-alpha excitation energy')


def save_turtle(destination):
    """Serialize this ontology only. External namespaces are referenced, not copied."""
    from rdflib import Graph

    buffer = io.BytesIO()
    ontology.save(file=buffer, format="ntriples")
    buffer.seek(0)
    graph = Graph()
    graph.parse(buffer, format="nt")
    graph.bind("", BASE_IRI)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = graph.serialize(format="turtle")
    destination.write_text(serialized.rstrip() + "\n", encoding="utf-8")
    return destination


if __name__ == "__main__":
    print(save_turtle(Path(__file__).with_suffix(".ttl")))
