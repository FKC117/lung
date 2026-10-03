# Prescription option resolution rules

The server resolves only existing catalog rows. It never trusts option IDs returned by a provider, creates catalog rows, or treats fuzzy similarity as approval.

Resolution is restricted to the supplied parent scope before matching. Rules, in order:

1. A unique administered drug alias may resolve. A conflicting exact canonical drug name or multiple alias targets produces an exception.
2. For diagnosis groups/subgroups only, a unique ICD-10 code may resolve after removing display punctuation and uppercasing.
3. A unique case-insensitive exact name may resolve.
4. A unique normalized name may resolve. Approved implementation normalization removes accents, case, whitespace and nonclinical separators, while preserving polarity, comparison signs, percentages and decimal punctuation. It does not translate narrative diagnoses or infer clinical semantics.
5. Similar names are suggestions only; no selected ID is assigned. Duplicate exact/normalized/code matches are ambiguous.

Every result records its method and a SHA-256 fingerprint of current catalog rows and applicable administered aliases. Fingerprints describe the catalog at matching time; they are not a permission to bypass current validation. Saves and publication validate IDs, resource, multiselect cardinality and parent relationships against the current database. A deleted row fails validation. If the catalog changes after automatic matching, approval/publication requires selecting the current option again; draft saves remain possible. Explicit reviewer selections are still checked for existence and scope. Legacy resolutions without fingerprints remain compatible and receive current ID/scope checks.

Multiselect automatic resolution is all-or-none and requires distinct approved options for every supplied value. Original values remain in immutable extraction evidence.

The actual form scopes disease subgroup, molecular exon, panel version/target, protocol membership and protocol drugs to resolved parents. Parent changes clear dependent selections. Patient thana is checked against district on the server. Missing parents/options produce exceptions, never invented IDs.

Drug aliases are administered approved entries in `PrescriptionDrugAlias`; there is no provider-created or pending alias auto-resolution path. General catalog/alias administration improvements remain P5.5.

Verification: backend option automation and existing intake/schema tests cover exact/alias/code/normalized matches, clinical polarity, conflicting aliases/names, duplicate names, fuzzy suggestions, missing/wrong parents, deleted IDs, multiselect completeness and fingerprint changes. Frontend scoped-catalog and form tests cover parent filtering and invalidation. All fixtures are synthetic.
