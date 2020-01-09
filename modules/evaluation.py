import sys
sys.path.insert(1, '../')
from gensim.models import Word2Vec
from modules.db_interface import DBWrapper
from gensim.models import Word2Vec
from scipy.spatial.distance import jensenshannon
from nltk import FreqDist
from numbers import Number

class WordMovers:
    def __init__(self, root_path='./'):
        self.dbw = DBWrapper(root_path=root_path)
        self.category = None
        

    def run(self, summarized, category):
        self.summarized = summarized

        if category != self.category:
            print("New Category")
            self.category = category
            self.tweets = self.dbw.fetch_processed_tweets(category=category)

            sents = [tweet['preprocessed_text'].split() for tweet in self.tweets]

            print("Creating Embedding Model")
            self.embedding = Word2Vec(sentences=sents, min_count=1, size=100)
            self.w2v_vocab = set(self.embedding.wv.index2word)

        print("Calculating Summary Score")
        self.__calculate_summary_score()
        print("")

        return self.scores


    def __calculate_summary_score(self):
        self.scores = dict()
        summaries_score = 0
        summaries_count = 0

        community_counter = 0

        for community in self.summarized:
            community_counter += 1
            summary_counter = 0
            for summary in community:
                summary_counter += 1
                doc_count = 0
                temp_score = 0

                for tweet in self.tweets:
                    if tweet['_id'] != summary['_id']:
                        temp_score += self.embedding.wmdistance(
                            summary['preprocessed_text'], tweet['preprocessed_text']
                        )
                        doc_count += 1

                        print("  Community {}/{} | Summary {}/{} | Checking {}/{} | Summary Avg. Score {}".format(
                            community_counter,
                            len(self.summarized),
                            summary_counter,
                            len(community),
                            doc_count,
                            len(self.tweets),
                            temp_score/doc_count
                        ), end="\r")

                temp_score = 0 if doc_count == 0 else (temp_score / doc_count)
                summaries_count += 1
                summaries_score += temp_score
                self.scores[summary['_id']] = temp_score
        
        summaries_score = 0 if summaries_count == 0 else (summaries_score / summaries_count)
        self.scores['total_score'] = summaries_score

class JensenShannon:
    def __init__(self, root_path='./'):
        self.dbw = DBWrapper(root_path=root_path)
        self.category = None
        self.freqs = dict()
        self.vocabs = 1
        self.scores = dict()

    def run(self, summarized, category):
        if category != self.category:
            print("New Category")
            self.category = category
            self.summarized = summarized
            self.tweets = self.dbw.fetch_processed_tweets(category=category)

            print("Calculate vocabularies and frequencies")
            self.__initiate_frequencies()

        print("Calculate Scores")
        self.__calculate_scores()
        print("")

        return self.scores

    def __initiate_frequencies(self):
        lines = [tweet['preprocessed_text'] for tweet in self.tweets]
        lines = " ".join(lines)

        self.freqs = FreqDist(lines.split())
        self.vocabs = len(self.freqs)

    def __calculate_scores(self):
        community_count = 0
        community_score = 0
        c_counter = 0

        for community in self.summarized:
            c_counter += 1
            s_counter = 0
            for summary in community:
                s_counter += 1
                summary_prob_dist = self.__probabbility_dist(summary['preprocessed_text'])
                summary_score = 0
                summary_count = 0
                t_counter = 0

                for tweet in self.tweets:
                    t_counter += 1
                    if tweet['_id'] != summary['_id']:
                        tweet_prob_dist = self.__probabbility_dist(tweet['preprocessed_text'])
                        summary_prob_dist, tweet_prob_dist = self.__balance_probabilities(
                            summary_prob_dist, tweet_prob_dist
                        )
                        temp_score = jensenshannon(summary_prob_dist, tweet_prob_dist)

                        if isinstance(temp_score, Number):
                            summary_score += temp_score
                            summary_count += 1

                    print("  Community {}/{} | Summary {}/{} | Tweet {}/{}".format(
                        c_counter, len(self.summarized),
                        s_counter, len(community),
                        t_counter, len(self.tweets)
                    ), end="\r")

                if summary_count > 0:
                    self.scores[summary['_id']] = summary_score / summary_count
                    community_score += (summary_score / summary_count)
                    community_count += 1
                else:
                    self.scores[summary['_id']] = 0

        if community_count > 0:
            self.scores['total_score'] = community_score / community_count
        else:
            self.scores['total_score'] = 0



    def __probabbility_dist(self, sentence):
        probability_dist = list()

        for word in sentence.split():
            if word in self.freqs:
                probability_dist.append(self.freqs[word]/self.vocabs)
            else:
                probability_dist.append(0)

        return probability_dist

    def __balance_probabilities(self, summary, tweet):
        summary_len = len(summary)
        tweet_len = len(tweet)

        if summary_len < tweet_len:
            for i in range(summary_len, tweet_len):
                summary.append(0)
        elif tweet_len < summary_len:
            for i in range(tweet_len, summary_len):
                tweet.append(0)

        return summary, tweet