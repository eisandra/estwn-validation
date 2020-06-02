import gensim
import simplejson as json
from wn_w2v_comparison import w2v_wn_difference, parse_arguments, read_inputfile, \
    MyEncoder, sort_distances
from closest_relations import connected_lemmas
from estnltk.wordnet import wn
import numpy as np


# https://stackoverflow.com/questions/50914729/gensim-word2vec-select-minor-set-of-word-vectors-from-pretrained-model/55725093#55725093
def restrict_w2v(w2v, restricted_word_set):
    """mudeli muutmine, nii et see sisaldaks vaid valitud sõnu"""
    new_vectors = []
    new_vocab = {}
    new_index2entity = []
    new_vectors_norm = []

    for i in range(len(w2v.vocab)):
        word = w2v.index2entity[i]
        vec = w2v.vectors[i]
        vocab = w2v.vocab[word]
        vec_norm = w2v.vectors_norm[i]
        word_parts = word.split('|')
        words = []
        for variant in word_parts:
            words.append(variant)
            if '-' in variant:
                words.append(variant.replace('-', ''))
        # kui vähemalt üks lemmadest esineb wni-sõnastikus
        if len(set(words).intersection(restricted_word_set)) > 0:
            vocab.index = len(new_index2entity)
            new_index2entity.append(word)
            new_vocab[word] = vocab
            new_vectors.append(vec)
            new_vectors_norm.append(vec_norm)

    w2v.vocab = new_vocab
    w2v.vectors = np.array(new_vectors)
    w2v.index2entity = np.array(new_index2entity)
    w2v.index2word = np.array(new_index2entity)
    w2v.vectors_norm = np.array(new_vectors_norm)


def read_spellcheck_file(file):
    with open(file, 'r', encoding='utf-8') as f:
        return [line.strip().lower() for line in f.readlines()]


def w2v_similarities(w2v_all_similar, max_distance):
    """
    leiab kõik w2v sõnad, mille skoor on suurem kui kaugeima seotud lemma oma
    """
    checked_similarities = []

    for word, distance in w2v_all_similar:
        if distance >= max_distance:
            checked_similarities.append(word)
        else:
            break
    return checked_similarities


def compare_wn_w2v(vectors, target_word, ignore, holo_max=3, mero_max=3, hyper_max=3, hypo_max=3, topn=1000):
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
    w2v_lemmas = w2v_similarities(w2v_1000, least_similar_lemma)
    output_entry['w2v'] = w2v_wn_difference(wn_lemmas, w2v_lemmas)
    output_entry["w2v_1000_kaugeim"] = w2v_1000[-1]

    return output_entry


def main(args):
    targetwords = []
    for file in args.targetword_files:
        targetwords.extend(read_inputfile(file))

    spellcheck_words = []
    for file in args.spellcheck_files:
        spellcheck_words.extend(read_spellcheck_file(file))

    vectors = gensim.models.KeyedVectors.load_word2vec_format(args.model[0], binary=True)
    vectors.most_similar('kadunud')
    restrict_w2v(vectors, set(spellcheck_words))

    with open('wn_w2v_vordlus_4.json', 'w', encoding='utf-8') as f:
        data = dict()
        for i, word in enumerate(targetwords, 1):
            print(i)
            data[word] =compare_wn_w2v(vectors, word, args.ignored_relations,
                           hyper_max=args.hyper_max[0], hypo_max=args.hypo_max[0],
                           holo_max=args.holo_max[0], mero_max=args.mero_max[0])
        json.dump(data, f, cls=MyEncoder)


if __name__ == '__main__':
    wn.all_synsets()
    arguments = parse_arguments()
    main(arguments)
