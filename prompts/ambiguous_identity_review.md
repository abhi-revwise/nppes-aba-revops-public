# Designed AI review prompt — not executed

Review NPPES-to-CRM identity evidence without making unsupported assertions. Return structured fields: decision (confirmed_same, likely_same_needs_review, different, abstain), confidence, supporting evidence, conflicts, missing fields, proposed human followup. A matching practice address or name alone does NOT prove employment or shared identity. Do not invent NPI, domain, affiliation or website URLs. Never write to production CRM.

Input: NPI={npi}; entity_type={entity_type}; practice_name={practice_name}; practice_address={practice_address}; crm_candidate={crm_candidate}; evidence={evidence}; public_urls={urls}.

Manual verification of AI adjudication not yet performed.
