from estnltk.wordnet import wn

wn.all_synsets()

CLOSE_RELS = ['be_in_state', 'fuzzynym', 'has_instance', 'has_subevent', 'has_xpos_hyperonym', 'has_xpos_hyponym',
              'involved', 'involved_agent', 'involved_instrument', 'involved_location', 'involved_patient',
              'involved_target_direction', 'is_caused_by', 'causes', 'is_subevent_of', 'near_antonym', 'near_synonym',
              'role', 'role_agent', 'role_instrument', 'role_location', 'role_patient', 'role_target_direction',
              'state_of', 'xpos_fuzzynym', 'xpos_near_antonym', 'xpos_near_synonym', 'antonym', 'belongs_to_class']

MERONYMS = ['has_mero_part', 'has_mero_location', 'has_mero_madeof', 'has_mero_member', 'has_mero_portion',
            'has_meronym']
HOLONYMS = ['has_holo_part', 'has_holo_location', 'has_holo_madeof', 'has_holo_member', 'has_holo_portion',
            'has_holonym']
HYPERNYM = 'has_hyperonym'
HYPONYM = 'has_hyponym'


def get_lemmas(syns_list):  # sünohulkade listist kõikide lemmad
    lemmas = []
    for syns in syns_list:
        lemmas.extend([lemma.name.lower() for lemma in syns.lemmas()])
    return lemmas


def connected_synsets(syns, holo_max=100, mero_max=100, hypero_max=100, hypo_max=100):
    all_rels = dict()  # list kõigi seotud sõnadega

    # hüperonüümid antud arv tasandeid
    all_rels['hüperonüümid'] = syns.closure(HYPERNYM, hypero_max)

    # holo- ja meronüümid antud arv tasandeid
    for relation in HOLONYMS:
        all_rels['holonüümid'] = syns.closure(relation, holo_max)

    for relation in MERONYMS:
        all_rels['meronüümid'] = syns.closure(relation, mero_max)

    # hüponüümid antud arv tasandeid
    try:
        all_rels['hüponüümid'] = syns.closure(HYPONYM, hypo_max)
        all_rels['taksonoomilised õed'] = syns.hypernyms()[0].hyponyms()  # eeldus, et üks otsene hüperonüüm
        all_rels['taksonoomilised õed'].remove(syns)
    except IndexError:
        pass  # omadussõnad

    # ülejäänud lähisuhted
    for relation in CLOSE_RELS:  # muud suhted
        all_rels[relation] = syns.get_related_synsets(relation)

    return dict(filter(lambda elem: len(elem[1]) != 0, all_rels.items()))  # tühjad jäävad välja


def connected_lemmas(syns, holo_max=3, mero_max=3, hypero_max=3, hypo_max=3):
    all_lemmas = dict()

    if len(syns.closure("has_hyperonym")) <= 3:  # liiga madala hierarhia puhul vaatab ainult lähimaid hüpero-meronüüme
        related_synsets = connected_synsets(syns, 1, mero_max, 1, hypo_max)

    else:
        related_synsets = connected_synsets(syns, holo_max, mero_max, hypero_max, hypo_max)

    for voti, synsets in related_synsets.items():
        all_lemmas[voti] = []
        for synset in synsets:
            all_lemmas[voti].extend(get_lemmas([synset]))

    all_lemmas['sünonüümid'] = get_lemmas([syns])

    return all_lemmas
