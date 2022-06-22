# GNF-2-ESDL

This is starting point for an implementation to convert GNF files to ESDL files. It currently maps the following asset types
and creates the connections between them:

| GNF type | ESDL asset type | State |
| ----------- | ----------- | --- |
| NODE | Joint | |
| PROFILE | GenericProfile | Not yet implemented |
| LINK | ElectricityCable | Unclear yet if this is right |
| CABLE | ElectricityCable | |
| TRANSFORMER | Transformer | |
| SOURCE | Import |  |
| HOME | ElectricityDemand |  |


- Documentation about the GNF file format: https://www.phasetophase.nl/downloads/Formaat%20netwerkbestand%20Gaia%207.12.docx
- Documentation about the ESDL format: https://energytransition.github.io/
