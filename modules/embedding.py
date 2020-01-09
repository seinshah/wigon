import sys
sys.path.insert(1, '../')
from gensim.models import Word2Vec
from scipy import spatial
import numpy
from modules.db_interface import DBWrapper
from infomap import Infomap
import networkx as nx
import community
from glove import Glove
from glove import Corpus

class Embedding:
    def __init__(self, root_path = './', embedding = 'word2vec', community = 'infomap', 
        category = None, verbose = False):
        self.verbose = verbose
        self.dbw = DBWrapper(root_path=root_path)
        self.tweets = numpy.array(self.dbw.fetch_processed_tweets(category=category))
        self.communities = dict()

        if self.verbose:
            print("    -{} tweet have been fetched & are processing".format(self.tweets.shape[0]))

        if embedding.lower() == 'word2vec':
            self.embedding_handler = MyWord2Vec()
        elif embedding.lower() == 'glove':
            self.embedding_handler = MyGloVe()
        else:
            raise Exception("Embedding method is not supported. Either use word2vec or glove")

        if community.lower() == 'infomap':
            self.community_handler = MyInfomap()
        elif community.lower() == 'louvain':
            self.community_handler = MyLouvain(self.tweets.shape[0])
        else:
            raise Exception("Community method is not supported. Either use infomap or louvain")

    def run(self):
        if self.verbose:
            print("    -Initiating embeding model")
        self.embedding_handler.initiate_model(self.__prepare_model_corpus())

        if self.verbose:
            print("    -Preparing data for community check")
        self.__prepare_community_data()

        if self.verbose:
            print("    -Detecting communities")
        communities = self.community_handler.detect_communities()
        
        if self.verbose:
            print("    -Preparing the output")
        self.__prepare_output_communities(communities)
        
        if self.verbose:
            print("    -{} communities detected".format(len(self.communities)))
        return self.communities

    def __prepare_model_corpus(self):
        corpus = []

        for tweet in self.tweets:
            corpus.append(tweet['preprocessed_text'].split())
        
        return corpus

    def __prepare_community_data(self):
        counter = 0
        
        for first_key in range(self.tweets.shape[0] - 1):
            counter += 1
            second_counter = 0

            for second_key in range(first_key + 1, self.tweets.shape[0]):
                weight = self.embedding_handler.cosine_similarity(
                    self.tweets[first_key]['preprocessed_text'], 
                    self.tweets[second_key]['preprocessed_text'])

                if(weight > 0.75):
                    self.community_handler.add_network_edge(first_key, second_key, weight)

                second_counter += 1
                if self.verbose:
                    edges_left = self.tweets.shape[0] - 1 - first_key - second_counter
                    print("        -Tweet {}/{}: {} edges left to add".format(counter, 
                        self.tweets.shape[0] - 1, edges_left), 
                        end="\n" if counter == self.tweets.shape[0] - 1 else "\r")

    def __prepare_output_communities(self, communities):
        for community in communities:
            for index in communities[community]:
                if community in self.communities:
                    self.communities[community].append(self.tweets[index])
                else:
                    self.communities[community] = [self.tweets[index]]

class MyWord2Vec:

    def initiate_model(self, input_corpus):
        self.model = Word2Vec(sentences=input_corpus, min_count=1, size=100)
        self.word_indexes = set(self.model.wv.index2word)

    def cosine_similarity(self, first_text, second_text):
        first = self.__average_feature_vector(first_text)
        second = self.__average_feature_vector(second_text)

        return 1 - spatial.distance.cosine(first, second)

    def __average_feature_vector(self, text):
        words = text.split()
        words_no = 0
        feature_vector = numpy.zeros((100, ), dtype="float32")

        for word in words:
            if word in self.word_indexes:
                words_no += 1
                feature_vector = numpy.add(feature_vector, self.model[word])
            
        if words_no > 0:
            feature_vector = numpy.divide(feature_vector, words_no)

        return feature_vector

class MyGloVe:
    def initiate_model(self, input_corpus):
        self.corpus_model = Corpus()
        self.corpus_model.fit(self.__read_corpus(input_corpus), window=10)

        self.glove = Glove(no_components=100, learning_rate=0.05)
        self.glove.fit(self.corpus_model.matrix, epochs=200)
        self.glove.add_dictionary(self.corpus_model.dictionary)

    def cosine_similarity(self, first_text, second_text):
        first = self.__average_feature_vector(first_text)
        second = self.__average_feature_vector(second_text)

        return 1 - spatial.distance.cosine(first, second)

    def __read_corpus(self, input_corpus):
        for line in input_corpus:
            yield line

    def __average_feature_vector(self, text):
        words = text.split()
        words_no = 0
        feature_vector = numpy.zeros((100, ), dtype="float32")

        for word in words:
            if word in self.glove.dictionary:
                word_idx = self.glove.dictionary[word]
                words_no += 1
                feature_vector = numpy.add(feature_vector, self.glove.word_vectors[word_idx])
            
        if words_no > 0:
            feature_vector = numpy.divide(feature_vector, words_no)

        return feature_vector

class MyInfomap:
    def __init__(self):
        self.handler = Infomap("--two-level")

    def add_network_edge(self, first_id, second_id, weight = 1.00):
        self.handler.addLink(first_id, second_id, weight)

    def detect_communities(self):
        self.handler.run()
        communities = {}

        for node in self.handler.iterTree():
            if node.isLeaf():
                if node.moduleIndex() in communities:
                    communities[node.moduleIndex()].append(node.physicalId)
                else:
                    communities[node.moduleIndex()] = [node.physicalId]

        return communities

class MyLouvain:
    def __init__(self, nodes_count):
        self.graph = nx.Graph()
        self.graph.add_nodes_from([n for n in range(nodes_count)])

    def add_network_edge(self, first_node, second_node, weight = None):
        self.graph.add_edge(first_node, second_node)

    def detect_communities(self):
        partition = community.best_partition(self.graph)
        communities = dict()

        for node in partition:
            group = partition[node]
            
            if group in communities:
                communities[group].append(node)
            else:
                communities[group] = [node]
        
        return communities