# NOMAD semantic mapping report

- Generated: `2026-09-14T13:28:30.649322+00:00`
- Schema: `xps_measurement.schema.py`
- Ontology IRI: `https://nomad-lab.eu/onto/xps#`
- Result: **passed**

## Pipeline

| Stage | Status | Duration | Details |
| --- | --- | ---: | --- |
| 1. Load and compile | passed | 0.000s | 9 entities<br>10 external references |
| 2. Reasoner (hermit) | passed | 0.640s | Hermit completed; 0 unsatisfiable classes. |
| 3. Validate | passed | 14.594s | Turtle-ready RDF graph: 51 triples<br>Loaded 6 of 6 external vocabulary documents into temporary graphs. |
| 4. Generate | passed | 0.016s | Python: ontology.py<br>Turtle: ontology.ttl |
| 5. Report | passed | 0.000s | Markdown: report.md |

## Model summary

- Declared mapped entities: **9**
- Declarative operations: **23**
- Generated RDF triples: **51**
- Referenced external IRIs: **10**

## External vocabulary validation

External documents are downloaded only into isolated temporary RDF graphs. They are not imported into the generated ontology.

| Requested namespace | Status | Terms found | Resolved document | RDF format | Triples |
| --- | --- | ---: | --- | --- | ---: |
| http://qudt.org/schema/qudt/ | passed | 4/4 | https://qudt.org/schema/qudt/ | turtle | 2153 |
| http://www.w3.org/ns/prov | passed | 2/2 | https://www.w3.org/ns/prov | turtle | 1664 |
| http://purl.org/dc/terms/ | passed | 1/1 | https://www.dublincore.org/specifications/dublin-core/dcmi-terms/dublin_core_terms.ttl | turtle | 700 |
| http://www.w3.org/ns/dcat | passed | 1/1 | https://www.w3.org/ns/dcat | turtle | 1695 |
| http://qudt.org/vocab/unit/ | passed | 1/1 | https://qudt.org/vocab/unit/ | turtle | 86645 |
| http://qudt.org/vocab/quantitykind/ | passed | 1/1 | https://qudt.org/vocab/quantitykind/ | turtle | 29072 |

## Warnings

- None.

## Artifacts

- `ontology.py`: generated Owlready2 representation
- `ontology.ttl`: generated OWL ontology in Turtle
- `report.md`: this pipeline report

## Interpretation

A passed serialization check means the graph is valid Turtle and every mapped local entity occurs in it. A passed reasoner stage means the selected reasoner completed for the generated model. External resolution proves that a vocabulary document was reachable and RDF-parseable; it does not prove that every chosen term has the intended scientific meaning. Review warnings and domain semantics before publishing.
