# EstWNi kontrollimise meetodid

Programmide jooksutamiseks on vaja teeke Gensim ja EstNLTK 1.4.
Kõik programmid kasutavad meetode moodulist closest_relations. Wn_w2v_comparison_3 ja wn_w2v_comparison_4 kasutavad ka meetodeid moodulist wn_w2v_comparison.

## EstWNi sünohulkade suhetest puuduvate lemmade leidmine _word2vec_’i abil

Katsete väljunid failides _wn_vordlus_1.zip_, _wn_vordlus_2_1.zip_, _wn_vordlus_2_2.zip_, _wn_vordlus_3.zip_.
EstWNis sisalduvad sagedussõnastiku sõnad on failis  _wn_olemas_sagedad.txt_. Kirjakeelekontrolliks on kasutusel EstWN 2.3.3 lemmad failis _estwn-et-2.3.2_lemmad.txt_ ja EstWNist puudunud sagedussõnastiku lemmad failis _wn_puuduvad_sagedad.txt_.

Word2veci mudel _lemmas.sg.s200.w2v.bin_ [entu.keeleressursid.ee](https://entu.keeleressursid.ee/shared/7540/I7G5aC1YgdInohMJjUhi1d5e4jLdhQerZ4ikezz1JEv3B9yuJt9KiPl9lrS87Yz0) lehel.



### Katse 1

python wn_w2v_comparison.py tee/lemmas.sg.s200.w2v.bin --targetword_files wn_olemas_sagedad.txt --spellcheck_files estwn-et-2.3.2_lemmad.txt wn_puuduvad_sagedad.txt

### Katse 2

python wn_w2v_comparison.py tee/lemmas.sg.s200.w2v.bin --targetword_files wn_olemas_sagedad.txt --spellcheck_files estwn-et-2.3.2_lemmad.txt wn_puuduvad_sagedad.txt --ignored_relations "taksonoomilised õed" --hyper_max 2

Katse 2.2 puhul --hyper_max 1

### Katse 3
python wn_w2v_comparison_3.py tee/lemmas.sg.s200.w2v.bin --targetword_files wn_olemas_sagedad.txt --spellcheck_files estwn-et-2.3.2_lemmad.txt wn_puuduvad_sagedad.txt 

### Katse 4
python wn_w2v_comparison_4.py tee/lemmas.sg.s200.w2v.bin --targetword_files wn_olemas_sagedad.txt --spellcheck_files estwn-et-2.3.2_lemmad.txt wn_puuduvad_sagedad.txt

##  Sama sünohulgaga mitme suhte kaudu seotud sünohulkade eraldamine

python overlapping_relations.py wn_olemas_sagedad.txt

Väljund failis _korduvad_suhted.csv_.

##  Hüperonüümia korrastamine taksonoomiliste õdede definitsioonide abil

python hypernym_extraction.py wn_olemas_sagedad.txt

Väljund failis _seotud_taksonoomilised_oed.csv_.
