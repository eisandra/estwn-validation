import gensim
from gensim.test.utils import datapath
import simplejson as json
from wn_w2v_comparison import w2v_wn_difference, parse_arguments, read_inputfile, read_spellcheck_file, \
    w2v_similarities, MyEncoder, sort_distances
from closest_relations import connected_lemmas
from estnltk.wordnet import wn


def compare_wn_w2v(vectors, target_word, spellcheck_dict, ignore, holo_max=3, mero_max=3, hyper_max=3, hypo_max=3, topn=1000):
    try:
        w2v_1000 = vectors.most_similar(target_word, topn=topn)
    except KeyError:
        return None

    output_entry = dict()
    synsets = wn.synsets(target_word)

    if synsets:

        wn_lemmas = list()  # kõik sõnaga seotud lemmad,  w2v vahe leidmiseks
        output_entry['sünohulgad'] = dict()

        for synset in synsets:
            word_min_distance = 1.0
            syns_min_relations = ['sünonüümid']

            # sünohulgal on kaugeim element ja suhted. Suhted on eraldi sõnastik, kus võtmeks suhte nimi
            # väärtuseks suhte alla kuuluvad lemmad ja nende similarity sihtsõnale

            output_entry['sünohulgad'][synset.name] = dict()
            output_entry['sünohulgad'][synset.name]['suhted'] = dict()

            synset_lemmas = connected_lemmas(synset, holo_max=holo_max, mero_max=mero_max,
                                             hypero_max=hyper_max, hypo_max=hypo_max)  # lemmad suhete järgi sõnastikus
            for relation, related_lemmas in synset_lemmas.items():
                wn_lemmas.extend(related_lemmas)

                if relation not in ignore:

                    sorted_distances = sort_distances(vectors, target_word, related_lemmas)

                    if relation == 'sünonüümid':
                        sorted_distances = sorted_distances[:-1]  # sõna ise ei lähe arvesse

                    if sorted_distances:
                        output_entry['sünohulgad'][synset.name]['suhted'][relation] = sorted_distances

                        # suurima sarnasuse leidmine
                        if sorted_distances[-1][1] < word_min_distance:
                            word_min_distance = sorted_distances[-1][1]
                            syns_min_relations = [relation]

                        # kaugeim sõna võib kuuluda mitme suhte alla
                        elif sorted_distances[-1][1] == word_min_distance and relation not in syns_min_relations:
                            syns_min_relations.append(relation)

            output_entry['sünohulgad'][synset.name]['kaugeim'] = (word_min_distance, syns_min_relations)

    # leiab sõna kõigi sünohulkade vähimate kauguste peale kõige väiksemad
    least_similar_lemma = min(
        [synset_information['kaugeim'][0] for _, synset_information in output_entry['sünohulgad'].items()])
    w2v_lemmas = w2v_similarities(w2v_1000, least_similar_lemma, spellcheck_dict)
    output_entry['w2v'] = w2v_wn_difference(wn_lemmas, w2v_lemmas)
    output_entry["w2v_1000_kaugeim"] = w2v_1000[-1]

    return output_entry


def main(args):
    vectors = gensim.models.KeyedVectors.load_word2vec_format(
        args.model[0], binary=True)
    targetwords = []
    for file in args.targetword_files:
        targetwords.extend(read_inputfile(file))

    spellcheck_dict = dict()
    for file in args.spellcheck_files:
        spellcheck_dict = read_spellcheck_file(file, spellcheck_dict)

    with open('wn_w2v_vordlus_3.json', 'w', encoding='utf-8') as f:
        data = dict()
        for i, word in enumerate(targetwords, 1):
            print(i)
            data[word] = compare_wn_w2v(vectors, word, spellcheck_dict, args.ignored_relations,
                                        hyper_max=args.hyper_max[0], hypo_max=args.hypo_max[0],
                                        holo_max=args.holo_max[0], mero_max=args.mero_max[0])
        json.dump(data, f, cls=MyEncoder)


if __name__ == '__main__':
    wn.all_synsets()
    arguments = parse_arguments()
    main(arguments)

