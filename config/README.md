# Reviewed mappings

The country-name crosswalks and file/metadata corrections were inspected during
the audit and explicitly approved for integration on 25 September 2026. Speech
filename identity takes priority over mutable metadata display names. Crosswalks
are authoritative inputs, not output learned from conflict labels.

- `speech_entity_rules.csv`: time-valid exceptional or excluded speech identities.
- `metadata_key_corrections.csv`: documented ISO typos and shifted metadata keys.
- `sipri_country_crosswalk.csv`: included source countries versus aggregates and
  historical exclusions. Its year bounds describe the workbook coverage; they
  are not state-existence dates. Cell markers retain that separate information.
- `ucdp_country_crosswalk.csv`: reviewed location aliases, historical exclusions
  and time ranges. Bounds cover observed conflict records in v26.1, not periods
  of peace or independence. Every actual source row must map exactly once.
- `region_income_snapshot.csv`: public World Bank country API snapshot retrieved
  24 September 2026 from
  https://api.worldbank.org/v2/country?format=json&per_page=400 . Current region
  and income labels are used for descriptive coverage, not as historical income.
  This small public lookup contains no private speech or analytical observations.

Review mappings if the source datasets change. Missing SIPRI values are not zero.
