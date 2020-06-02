import argparse
import gensim
from closest_relations import *
from estnltk.wordnet import wn
import re
import simplejson as json
import numpy


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, numpy.floating):
            return float(obj)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Finding possible missing senses and relations from Estonian Wordnet"
    )
    parser.add_argument(
        "model", nargs=1, help="File of word2vec model"
    )
    parser.add_argument(
        "--targetword_files", nargs="+", help="Files of words for checking, formatted word per line"
    )
    parser.add_argument(
        "--spellcheck_files", nargs="+", help="Files of words used for spellcheck"
    )
    parser.add_argument(
        "--holo_max", nargs=1, type=int, default=[3], help="Maximum number of inherited holonyms, 3 by default"
    )
    parser.add_argument(
        "--mero_max", nargs=1, type=int, default=[3], help="Maximum number of inherited meronyms, 3 by default"
    )
    parser.add_argument(
        "--hyper_max", nargs=1, type=int, default=[3], help="Maximum number of inherited hypernyms, 3 by default"
    )
    parser.add_argument(
        "--hypo_max", nargs=1, type=int, default=[3], help="Maximum number of inherited hyponyms, 3 by default"
    )
    parser.add_argument(
        "--ignored_relations", nargs='+', help="Relations not counting on calculating farthest relation", default=[]
    )
    return parser.parse_args()


def read_inputfile(file):
    with open(file, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines()]


def read_spellcheck_file(file, spellcheck_dict):
    with open(file, 'r', encoding='utf-8') as f:
        for line in f.readlines():
            first_letter = line[0].lower()
            if first_letter not in spellcheck_dict:
                spellcheck_dict[first_letter] = [line.strip().lower()]
            else:
                spellcheck_dict[first_letter].append(line.strip().lower())
    return spellcheck_dict


def sort_distances(vectors, target_word, lemmas):
    """
    :param lemmas: sihtsõnaga wn-is seotud lemmad
    :return: seotud lemmad kasvavas järjestuses koos koosinuskaugusega
    """
    distances = dict()
    for lemma in lemmas:
        try:
            distances[lemma] = vectors.similarity(lemma, target_word)
        except KeyError:
            pass
    return sorted(distances.items(), key=lambda kv: kv[1])


def w2v_similarities(w2v_all_similar, max_distance, correct_words):
    """
    :param w2v_all_similar: w2v most_similar meetodiga saadud sõnad kaugustega (järjestatult)
    :param max_distance: kaugus, millest sarnasemaid lemmasid arvestatakse
    :param correct_words: sõnastik sobivate sõnadega
    :return: similarity järjestuses w2v sõnad, mille skoor on kaugem kui max distance (kaugeima seotud lemma kaugus)
    """
    checked_similarities = []
    for word, distance in w2v_all_similar:
        first_letter = word[0]
        if distance >= max_distance:
            if re.search('[a-zõäöüA-ZÕÄÖÜ]', word) is not None:
                word = word.split("|")  # nt "uhkustanud|uhkustama"
                for alternative in word:
                    try:
                        if (alternative not in checked_similarities) and (alternative in correct_words[first_letter]):
                            # kui sõna on tuntud ja veel sarnaste seas pole
                            checked_similarities.append(alternative)
                        elif '-' in alternative:  # poolitatud sõnad, nt "inter-vjuu", mida sõnastikes pole
                            variant2 = alternative.replace('-', '')
                            if (variant2 not in checked_similarities) and (variant2 in correct_words[first_letter]):
                                checked_similarities.append(variant2)
                    except KeyError:
                        pass
        else:
            break
    return checked_similarities


def w2v_wn_difference(wn_related_lemmas, w2v_similar_lemmas):
    """
    :param wn_related_lemmas: wn'i suhete lemmad
    :param w2v_similar_lemmas: w2v sõnahulk järjestatult suurimast sarnasusest väiksemaks
    :return: w2v sarnased, mida pole wn-i lähisuhetes, järjestatult kahaneva koosinuskauguse järgi
    """
    vahe = set(w2v_similar_lemmas) - set(wn_related_lemmas)
    return [sona for sona in w2v_similar_lemmas if sona in vahe]


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

                    if sorted_distances:
                        output_entry['sünohulgad'][synset.name]['suhted'][relation] = sorted_distances

                        # suurima sarnasuse leidmine
                        if sorted_distances[0][1] < word_min_distance:
                            word_min_distance = sorted_distances[0][1]
                            syns_min_relations = [relation]

                        # kaugeim sõna võib kuuluda mitme suhte alla
                        elif sorted_distances[0][1] == word_min_distance and relation not in syns_min_relations:
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

    with open('wn_w2v_vordlus_2_2.json', 'w', encoding='utf-8') as f:
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
