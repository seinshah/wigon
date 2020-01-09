import os
import sys
sys.path.insert(1, '../modules')
from embedding import Embedding
from summarization import Summarize
import json

collocations = [{
    'embedding': 'word2vec',
    'community': 'infomap',
    'ignore': False
}, {
    'embedding': 'glove',
    'community': 'infomap',
    'ignore': False
}, {
    'embedding': 'glove',
    'community': 'louvain',
    'ignore': False
}, {
    'embedding': 'word2vec',
    'community': 'louvain',
    'ignore': False
}]

categories = ['IranProtests', 'Brexit']

for category in categories:
    print("====================")
    print("Processing {} category".format(category))

    for collocation in collocations:
        print("----------------")
        print("  Processing {} | {}".format(collocation['embedding'], 
            collocation['community']))

        if collocation['ignore']:
            print("Ignored based on the hard-coded configuration")
            continue

        output_path = "../output/summarization_{}_{}_{}.wo".format(category, 
            collocation['embedding'], collocation['community'])

        if os.path.isfile(output_path):
            print("  Skipped as the output is already generated")
            continue

        calculated_comminity_file = "../temp/community_{}_{}_{}.wct".format(category, 
            collocation['embedding'], collocation['community'])

        if os.path.isfile(calculated_comminity_file):
            print("  Communities loaded from temp file")
            f = open(calculated_comminity_file, 'r', encoding='utf-8')
            tweet_groups = json.loads(f.read())
            f.close()
        else:
            print("  Starting to detect communities")
            em = Embedding(root_path='../', category=category, 
                embedding=collocation['embedding'], community=collocation['community'], verbose=True)
            tweet_groups = em.run()

            f = open(calculated_comminity_file, 'w+', encoding='utf-8')
            f.write(json.dumps(tweet_groups))
            f.close()

        summarizor = Summarize(root_path='../', communities=tweet_groups)
        summarization = summarizor.run()

        f = open(output_path, 'w+', encoding='utf-8')
        f.write(json.dumps(summarization))
        f.close()
        
        print("  Summarization output is stored in the file")
