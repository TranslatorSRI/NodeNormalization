# NodeNorm Translator May 2024 Release

- Babel: [2024mar24](https://stars.renci.org/var/babel_outputs/2024mar24/)
  (Babel Translator May 2024 Release)
- NodeNorm: [v2.3.8](https://github.com/TranslatorSRI/NodeNormalization/releases/tag/v2.3.8)

Next release: _None as yet_

## New features
* Minor changes 

## Babel updates (from Babel Translator May 2024 Release)
* [New identifiers] 36.9 million PubMed IDs (e.g. `PMID:25061375`) have been added as `biolink:JournalArticle`, as well as
  the mappings to PMC (e.g. `PMC:PMC4109484`) and DOIs (e.g. `doi:10.3897/zookeys.420.7089`) that are included in PubMed.
  Details in [TranslatorSRI/Babel#227](https://github.com/TranslatorSRI/Babel/pull/227).
* Fixed type determination for DrugChemical conflation. Details in
  [TranslatorSRI/Babel#266](https://github.com/TranslatorSRI/Babel/pull/266).
* Synonym files now include the clique identifier count (the number of identifiers in each clique) in synonyms file.
* Minor fixes.

## Releases since [Translator December 2023 release](TranslatorDecember2023.md)
* [NodeNorm v2.3.7](https://github.com/TranslatorSRI/NodeNormalization/releases/tag/v2.3.7)
  * Added Translator release information
  * Fixed examples
* [NodeNorm v2.3.6](https://github.com/TranslatorSRI/NodeNormalization/releases/tag/v2.3.6)
  * Reverted NodeNorm loader to Redis v6