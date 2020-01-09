import sys
sys.path.insert(1, '../')
from sklearn.feature_extraction.text import TfidfVectorizer
from modules.helper import Helper
from math import ceil

class Summarize:
    def __init__(self, communities, root_path = './'):
        self.helper = Helper(root_path)
        self.communities = communities
        self.summarized = []

    def run(self):
        for community in self.communities:
            sentences = [tweet['preprocessed_text'] for tweet in self.communities[community]]
            vectorize = TfidfVectorizer()
            tfidfs = vectorize.fit_transform(sentences)
            aggregate_tfidf = self.__populate_tweet_tfidf(tfidfs, len(sentences), self.communities[community])
            self.__select_most_representative(aggregate_tfidf, self.communities[community])
        return self.summarized

    def __populate_tweet_tfidf(self, tfidfs, doc_length, tweets):
        result = dict()

        for doc in range(doc_length):
            score = 0
            feature_index = tfidfs[doc,:].nonzero()[1]
            tfidf_scores = zip(feature_index, [tfidfs[doc, x] for x in feature_index])
            for s in [s for (i, s) in tfidf_scores]:
                score += s

            score += self.__compute_tweet_additional_score(tweets[doc])
            
            result[doc] = score
        
        result = {key: val for key, val in sorted(result.items(), key=lambda item: item[1], reverse=True)}
        return result

    def __compute_tweet_additional_score(self, tweet):
        score = self.helper.config_item('scoring.verified', 1) if tweet['user']['verified'] else 0

        faves = tweet['faves']
        rt = tweet['retweets']
        fave_rt_const = self.helper.config_item('scoring.faves_rt_constant', 0.0005)
        followings = tweet['user']['followings'] if tweet['user']['followings'] > 0 else 1
        followers = tweet['user']['followers']
        popularity_const = self.helper.config_item('scoring.popularity_constant', 0.001)
        word_count = len(tweet['preprocessed_text'].split())
        word_count_constant = self.helper.config_item('scoring.tweet_length_constant', 0.001)
        
        score += (faves + rt) * fave_rt_const
        score += (followers - followings) * popularity_const
        score += word_count * word_count_constant

        return score

    def __select_most_representative(self, scores, tweets):
        community_representatives = []
        selection_share = self.helper.config_item('global.representative_share', 0.001)
        selection_threshold = ceil(len(tweets) * selection_share)
        counter = 0

        print("    -Selecting {} tweet from community".format(selection_threshold))

        for chosen_index in scores:
            counter += 1
            community_representatives.append(tweets[chosen_index])

            if counter > selection_threshold:
                break

        self.summarized.append(community_representatives)