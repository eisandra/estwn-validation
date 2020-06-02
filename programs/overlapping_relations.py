from estnltk.wordnet import wn
from closest_relations import connected_synsets
import csv
import argparse

TWO_WAY_RELS = ['hüperonüümid', 'hüponüümid', 'fuzzynym', 'near_synonym', 'near_antonym', 'xpos_fuzzynym',
                'xpos_near_antonym', 'xpos_near_synonym', 'has_xpos_hyperonym', 'has_xpos_hyponym', 'antonym']


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Finding overlapping relations amongst given words' synsets' from Estonian Wordnet"
    )
    parser.add_argument(
        "inputfiles", nargs="+", help="Files of words for checking, formatted word per line"
    )
    parser.add_argument(
        "--holo_max", nargs=1, type=int, default=[100], help="Maximum number of inherited holonyms"
    )
    parser.add_argument(
        "--mero_max", nargs=1, type=int, default=[100], help="Maximum number of inherited meronyms"
    )
    parser.add_argument(
        "--hyper_max", nargs=1, type=int, default=[100], help="Maximum number of inherited hypernyms"
    )
    parser.add_argument(
        "--hypo_max", nargs=1, type=int, default=[100], help="Maximum number of inherited hyponyms"
    )
    return parser.parse_args()


def read_inputfile(file):
    with open(file, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines()]


def main(args):
    words = []
    for file in args.inputfiles:
        words.extend(read_inputfile(file))

    with open('korduvad_suhted.csv', 'w', encoding='utf-8', newline='') as output:
        seen_synsets = []
        csv_writer = csv.writer(output)

        for word in words:
            for synset in wn.synsets(word):
                # mitu sõna võivad viia sama sünohulgani, teist korda neid vaadata ei taha
                if synset not in seen_synsets:
                    seen_synsets.append(synset)
                    related_synsets = connected_synsets(synset, args.holo_max[0], args.mero_max[0], args.hyper_max[0],
                                                        args.hypo_max[0])
                    related_synsets['sünonüüm'] = [synset]  # suhe võib kaudselt olla ka iseendaga
                    try:
                        del related_synsets['taksonoomilised õed']  # neid pole vaja vaadata
                    except KeyError:
                        pass

                    relation_names = list(related_synsets.keys())
                    # suhete läbivaatamine
                    for i, relation in enumerate(relation_names, 0):
                        for compared_relation in relation_names[i + 1:]:
                            # samad sünohulgad seotud mitme suhtega
                            rels_intersection = set(related_synsets[relation]).intersection(
                                set(related_synsets[compared_relation]))
                            # kui mõlemad CLOSE_RELS on kahepoolsed, siis võivad need varasemast kirjas olla
                            if rels_intersection and (relation in TWO_WAY_RELS) and (compared_relation in TWO_WAY_RELS):
                                rels_intersection = [syns for syns in rels_intersection if syns not in seen_synsets]
                            if rels_intersection:
                                intersection_synsets = [el.name for el in rels_intersection]
                                csv_writer.writerow(
                                    [synset.name, relation, compared_relation, str(intersection_synsets)])


if __name__ == "__main__":
    arguments = parse_arguments()
    main(arguments)
