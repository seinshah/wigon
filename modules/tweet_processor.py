import sys
sys.path.insert(1, '../')
from modules.helper import Helper
import re
from string import punctuation
import spacy
from spellchecker import SpellChecker
from nltk import word_tokenize

class Preprocessor:

    def __init__(self, hashtags_list, root_path = './'):
        self.spell = SpellChecker()
        self.helper = Helper(root_path)
        self.slangs = self.helper.slang_hashmap()
        self.hashtags = [ht.strip().lower().replace('#', '') for ht in hashtags_list]

    def preprocess_tweet(self, input):
        self.tweet = input
        self.__remove_urls()
        self.__remove_usernames()
        self.__remove_non_latin()
        self.__remove_stopwords()
        self.__prune_slang_dictation()
        self.__remove_stopwords()
        self.__remove_special_chars()
        self.__final_prunning()

        return self.tweet.lower(), self.__ignore_tweet()
    
    def __remove_usernames(self):
        self.tweet = re.sub(r"(?=[^\w])\@\w+(?=[^\w]|$)", r"", self.tweet)

    def __remove_non_latin(self):
        emoji_pattern = re.compile("["
                        u"\U0001F600-\U0001F64F"  # emoticons
                        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                        u"\U0001F680-\U0001F6FF"  # transport & map symbols
                        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                        u"\U00002702-\U000027B0"
                        u"\U000024C2-\U0001F251"
                        "]+", flags=re.UNICODE)
        self.tweet = emoji_pattern.sub(r"", self.tweet)
        self.tweet = self.tweet.encode('ascii', 'ignore').decode('ascii')
        self.tweet = self.tweet.replace("&amp;", "&")
    
    def __remove_special_chars(self):
        self.tweet = self.tweet.replace('\n', ' ').replace('\r', '')
        self.tweet = re.sub(r"[^\w\s]", r"", self.tweet)

    def __remove_urls(self):
        self.tweet = re.sub(r"https://t.co/\w*", r"", self.tweet)

    def __remove_stopwords(self):
        nlp = spacy.load("en_core_web_sm")
        self.tweet = " ".join([token.text for token in nlp(self.tweet) if not token.is_stop])

    def __prune_slang_dictation(self):
        words = word_tokenize(self.tweet)
        new_words = []

        for word in words:
            change = ''
            if self.__should_be_chacked_for_slang(word) and word.upper() in self.slangs:
                change = "Abbr: {} => {}".format(word, self.slangs[word.upper()])
                new_words.append(self.slangs[word.upper()])
            elif self.__should_be_chacked_for_correction(word):
                correct_word = self.spell.correction(word)

                if not word == correct_word:
                    if correct_word.upper() in self.slangs:
                        change = "Abbr Correction: {} => {}".format(word, self.slangs[correct_word.upper()])
                        new_words.append(self.slangs[correct_word.upper()])
                    else:
                        change = "Correction: {} => {}".format(word, correct_word)
                        new_words.append(correct_word)
                else:
                    new_words.append(word)
            else:
                new_words.append(word)

        self.tweet = " ".join(new_words)

    def __ignore_tweet(self):
        words_threshold = self.helper.config_item('global.words_threshold')
        words = word_tokenize(re.sub(r"[^\w\s]", r"", self.tweet))

        return True if len(words) < words_threshold else False

    def __should_be_chacked_for_slang(self, word):
        result = True

        exceptions = self.helper.config_item('global.abbr_exceptions')
        exceptions = [ex.strip().lower() for ex in exceptions.split(',')]

        if word.lower() in exceptions:
            result = False
        elif word.lower() in self.hashtags:
            result = False
        #Possibly a name
        elif word[0].isupper and word[1:].islower():
            result = False
        elif len(word) < 2:
            result = False

        return result

    def __should_be_chacked_for_correction(self, word):
        result = True

        exceptions = self.helper.config_item('global.correction_exceptions')
        exceptions = [ex.strip().lower() for ex in exceptions.split(',')]
        uppercase_chars = [ch for ch in word if ch.isupper()]

        #Ignore words that has other than A to Z characters
        if not re.match(r"^[A-Za-z]$", word):
            result = False
        elif word.lower() in exceptions:
            result = False
        elif word.lower() in self.hashtags:
            result = False
        #Possibly a name
        elif word[0].isupper and word[1:].islower():
            result = False
        #Ignore word if it has more than 1 uppercase letter
        elif len(uppercase_chars) > 1:
            result = False

        return result

    def __final_prunning(self):
        self.tweet = re.sub(r"\b[0-9]+\b", r"", self.tweet)
        self.tweet = re.sub(r"\s+", r" ", self.tweet.strip().lower())