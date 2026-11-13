"""Public-safe provider persona and CRM action rules for synthetic examples."""
BCBA='103K00000X'
def classify(entity_type, taxonomy_codes, crm_candidate_ids, match_method='', phone='', practice_address='', *, new_this_run=True):
    taxonomy=set(c.strip() for c in taxonomy_codes.split(';'))
    has_bcba=BCBA in taxonomy
    candidates=[c.strip() for c in crm_candidate_ids.split(';') if c.strip()]
    has_company=bool(candidates)
    if entity_type=='2':
        provider_type='New ABA Organization'
        evidence='Type 2 NPI; actual business launch not independently verified'
    elif not has_bcba:
        provider_type='Individual at Existing Company'
        evidence='Possible company affiliation; verify' if has_company else 'supervised credential; employer not yet identified'
    elif has_company:
        provider_type='Individual at Existing Company'
        evidence='Possible company affiliation; verify employer'
    else:
        provider_type='Solo Practitioner (possible new practice)'
        evidence='BCBA without company evidence; launch remains unverified'
    if entity_type=='1' and not has_company and not has_bcba:
        status='';action='Do not import; market signal'
    elif has_company and entity_type=='2':
        status='Already in CRM';action='No new record; notify owner'
    elif has_company:
        status='New Contact at Existing Account';action='Create Contact, associate to existing Company'
    else:
        status='Net New Account';action='Create Company + Contact'
    score=0
    if entity_type=='2' or provider_type.startswith('Solo'):score+=40
    if has_bcba:score+=25
    elif '106E00000X' in taxonomy:score+=10
    if status=='Net New Account':score+=20
    elif status=='New Contact at Existing Account':score+=10
    if phone and practice_address:score+=10
    score=min(score,100)
    if entity_type=='1' and not has_bcba:score=min(score,39)
    tier='Tier 1' if score>=70 else 'Tier 2' if score>=40 else 'Tier 3'
    review=(entity_type=='1' or has_company or len(candidates)>1 or 'address' in match_method.lower())
    eligible=(status=='Net New Account' and tier=='Tier 1' and not review and bool(phone or practice_address))
    return {'provider_type':provider_type,'type_evidence':evidence,'crm_match_status':status,'crm_action':action,
            'score':score,'tier':tier,'review_required':'YES' if review else 'NO',
            'crm_import_allowed':'YES' if eligible else 'NO','new_this_run':bool(new_this_run)}
