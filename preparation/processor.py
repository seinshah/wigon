import os
import sys
sys.path.insert(1, '../modules')
from tweet_processor import Preprocessor
from db_interface import DBWrapper

hashtags = ['IranProtests', 'IranPortests', 'IraninaProtests', 'Iranprotets', 
            'IranProtesters', 'iranprotestsِ', 'brexit']

dbw = DBWrapper(root_path='../')
processor = Preprocessor(hashtags_list= hashtags, root_path='../')
counter = 0
ignore_counter = 0

for tweet in dbw.fetch_preprocessing_tweets():
    counter += 1
    new_tweet, ignore = processor.preprocess_tweet(tweet['text'])
    dbw.set_processed_tweet_info(tweet['_id'], ignore, new_tweet)

    if ignore:
        ignore_counter += 1

    if counter % 100 == 0:
        print("{} tweets processed and {} tweets ignored".format(counter, ignore_counter))