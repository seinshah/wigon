import os
import sys
sys.path.insert(1, '../modules')
from tweet_collector import TweetCollector
from db_interface import DBWrapper

'''
Fetch almost 24K tweets published about IranProtests using sandbox 30day API
These records include original tweets, retweets, and replies due to the sandbox API limitation
It also includes tweets from any languages and not a specific language
These ~24K tweets are published from Dec 2, 12:27 to Dec 03, 13:51
'''
hashtags = ['#IranProtests', '#IranPortests', '#IraninaProtests', '#Iranprotets', 
            '#IranProtesters', '#iranprotestsِ']
collector = TweetCollector(group_name='IranProtests', root_path='../')
collector.initiate_collection(hashtags)

'''
Fetch almost 5K tweets published about brexit using sandbox fullarchive API
These records include original tweets, retweets, and replies due to the sandbox API limitation
It also includes tweets from any languages and not a specific language
These ~5K tweets are published from Dec 4, 10:04 to Dec 04, 14:42
'''
hashtags2 = ['#brexit']
collector2 = TweetCollector(group_name='Brexit', root_path='../', collect_mode='endpoint_archive')
collector2.initiate_collection(hashtags2)

'''
Fetch almost 25K tweets published about brexit using sandbox 30day API
These records include original tweets, retweets, and replies due to the sandbox API limitation
It also includes tweets from any languages and not a specific language
These ~25K tweets are published from Dec 2, 23:07 to Dec 03, 10:03
'''
collector3 = TweetCollector(group_name='Brexit', root_path='../', strict_mode=False)
collector3.initiate_collection(hashtags2, toDate='201912041004')


'''
Using our DBWRapper to handle fetched tweets and store them in database
'''
dw = DBWrapper(root_path='../')
dw.populate_tweets(group_name='Brexit', initial_hashtags=hashtags2, verbosity=False)
dw.populate_tweets(group_name='IranProtests', initial_hashtags=hashtags, verbosity=False)