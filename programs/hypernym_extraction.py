import argparse
import csv
from closest_relations import get_lemmas, connected_synsets
from estnltk import Text
from estnltk.wordnet import wn


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Finding possible hypernyms from co-hyponyms for hyponyms of target word"
    )
    parser.add_argument(
        "inputfiles", nargs="+", help="Files of words for checking, formatted word per line"
    )
    parser.add_argument(
        "--holo_max", nargs=1, type=int, default=[3], help="Maximum number of inherited holonyms"
    )
    parser.add_argument(
        "--mero_max", nargs=1, type=int, default=[3], help="Maximum number of inherited meronyms"
    )
    parser.add_argument(
        "--hyper_max", nargs=1, type=int, default=[3], help="Maximum number of inherited hypernyms"
    )
    parser.add_argument(
        "--hypo_max", nargs=1, type=int, default=[3], help="Maximum number of inherited hyponyms"
    )
    return parser.parse_args()


def read_inputfile(file):
    with open(file, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines()]


def split_bar(str_list):
    separated_words = []
    for wordforms in str_list:
        separated_words.extend(wordforms.split('|'))
    return separated_words


def get_compound_head(lemma, root):
    """
    Leiab liitsõnade põhisõnad, rohkem kui kahest sõnast koosnevatel kõik võimalikud
    'raudteeülesõidukoht' -> ['teeülesõidukoht', 'ülesõidukoht', 'sõidukoht', 'koht']
    """
    compound_heads = []
    replaced = root.replace('=', '')

    if replaced != lemma or '_' in replaced:

        compound_parts = replaced.split('_')
        head_beginning = (sum([len(osa) for osa in compound_parts[:-1]]))
        compound_head = lemma[head_beginning:]
        compound_parts[-1] = compound_head

        for i, word in enumerate(compound_parts[1:], 1):  #
            head = ''.join(compound_parts[i:])
            compound_heads.append(head)

    return compound_heads


def get_keywords(syno, wn_pos):
    """
    Leiab märksõnad vastavalt sõnaliigile
    """
    pos_map = {'a': ['A', 'C', 'G', 'U', 'O'], 'n': ['S', 'P', 'N'], 'b': ['D'], 'v': ['V']}
    gloss = Text(syno.definition())
    gloss.tag_analysis()
    relevant_lemmas = []

    # definitsioonidest märksõnade leidmine
    for word in gloss['words']:
        for analysis in word['analysis']:
            if analysis['partofspeech'] in pos_map[wn_pos]:
                lemma = analysis['lemma']
                root = analysis['root']
                relevant_lemmas.append(lemma)
                relevant_lemmas.extend(get_compound_head(lemma, root))

    # sünonüümidest põhisõnade ja fraasipeade leidmine
    for lemma in get_lemmas([syno]):
        word = Text(lemma)
        word.tag_analysis()

        for analysis in word['words'][-1]['analysis']:  # fraasi pea analüüs
            if analysis['partofspeech'] in pos_map[wn_pos]:
                relevant_lemmas.extend(get_compound_head(analysis['lemma'], analysis['root']))

        # tühikuga fraasid: 'tume õlu' -> ['õlu']
        if ' ' in lemma:
            compound_parts = lemma.split(' ')
            for i, word in enumerate(compound_parts[1:], 1):
                head = ' '.join(compound_parts[i:])
                relevant_lemmas.extend([head])

    return relevant_lemmas


def main(args):
    seen = []  # vaadatud sünohulgad
    target_words = []
    for file in args.inputfiles:
        target_words.extend(read_inputfile(file))

    with open('seotud_taksonoomilised_oed.csv', 'w', encoding='utf-8', newline='') as output:
        csv_writer = csv.writer(output)
        csv_writer.writerow(
            ['sõna', 'sihtsünohulk', 'suhtesoovitused', 'sihtsünohulga definitsioon', 'suhtega seotud soovitused'])

        for word in target_words:
            word_synsets = wn.synsets(word)

            for syns in word_synsets:  # vaatab läbi kõik sagedussõnastiku sõnade sünohulgad
                co_hyponyms_dict = dict()  # taksonoomiliste õdede lemmad kujul {lemma: [syn.1, syn.2]}
                keyword_dict = dict()  # märksõnade lemmad

                if syns not in seen and len(syns.closure("has_hyponym")) > 0:

                    co_hyponyms = syns.closure("has_hyponym", 1)

                    for hypo in co_hyponyms:

                        # koostab sõnastiku, kust otsida soovitusi
                        keywords = get_lemmas([hypo])
                        for lemma in keywords:
                            if lemma in co_hyponyms_dict:
                                co_hyponyms_dict[lemma].append(hypo.name)
                            else:
                                co_hyponyms_dict[lemma] = [hypo.name]

                        # koostab sõnastiku, milles on hüponüümide lemmad ja nende sünohulgad
                        keyword_dict[hypo.name] = get_keywords(hypo, syns.pos)

                    # eemaldab hüperonüümi sisaldavad kirjed syno_sonastikust
                    for syns_lemma in get_lemmas([syns]):
                        if syns_lemma in co_hyponyms_dict.keys():
                            del co_hyponyms_dict[syns_lemma]

                    # leiab, kas märksõnastikus on mõni taksonoomiline õde v selle osa
                    for target_hyponym, keywords in keyword_dict.items():
                        keyword_co_hyponym_intersection = set(co_hyponyms_dict.keys()).intersection(set(keywords))

                        # lisab soovitustesse kõik taks.õdede ja märksõnade ühisosa lemmasid sisaldavad sünohulgad
                        # v.a taksonoomilised õed ise
                        other_relations = []
                        for relation, related_synsets in connected_synsets(wn.synset(target_hyponym),
                                                                           args.holo_max[0], args.mero_max[0],
                                                                           args.hyper_max[0], args.hypo_max[0]).items():
                            if relation != 'taksonoomilised õed':
                                other_relations.extend(related_synsets)

                        recommended_relations = []
                        for lemma in keyword_co_hyponym_intersection:
                            if target_hyponym not in co_hyponyms_dict[lemma]:
                                recommended_relations.extend(
                                    [wn.synset(synset_name) for synset_name in co_hyponyms_dict[lemma]]
                                )

                        if len(recommended_relations) > 0:
                            definition = wn.synset(target_hyponym).definition().replace('\n', ' ')
                            rels_recommendations_intersection = set(other_relations).intersection(
                                set(recommended_relations))
                            csv_writer.writerow(
                                [(word.upper()), target_hyponym, set(recommended_relations), definition,
                                 rels_recommendations_intersection])

                seen.append(syns)  # et kaks korda ei vaataks sama sünohulka


if __name__ == "__main__":
    arguments = parse_arguments()
    main(arguments)
