import sys
sys.path.insert(1, '../')
from modules.helper import Helper
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, WriteError
from os.path import isdir, isfile, join
from os import listdir
import json
import re
from langdetect import detect
from nltk import word_tokenize

class DBI:

    MODE_NOT_CHANGED = 0
    MODE_UPDATED = 1
    MODE_INSERTED = 2

    def __init__(self, root_path = './'):
        self.root_path = root_path.rstrip('/') + '/'
        self.helper = Helper(self.root_path)
        self.conf_name = 'mongodb_config'

        dsn = self.helper.config_item('{}.dsn'.format(self.conf_name))

        if type(dsn) is str and len(dsn) > 0:
            dbh = MongoClient(dsn)
        else:
            dbh = MongoClient(host=self.helper.config_item('{}.host'.format(self.conf_name)), 
                                    port= self.helper.config_item('{}.port'.format(self.conf_name)), 
                                    username= self.helper.config_item('{}.username'.format(self.conf_name)), 
                                    password= self.helper.config_item('{}.password'.format(self.conf_name)))

        self.db = dbh[self.helper.config_item('{}.db_name'.format(self.conf_name))]

    def insert(self, collection, document):
        collection = self.db[collection]

        if type(document) is dict:
            result = collection.insert_one(document)
            many = False
        elif type(document) is list:
            result = collection.insert_many(document)
            many = True
        else:
            result = None

        if result is not None and result.acknowledged is True:
            inserted_ids = result.inserted_ids if many is True else result.inserted_id
        else:
            inserted_ids = None

        status = False if inserted_ids is None else True

        return status, inserted_ids

    def upsert(self, collection, filter, document):
        collection = self.db[collection]
        status = False
        mode = None
        instance_id = None

        try:
            result = collection.replace_one(filter, document, upsert=True)

            if result.acknowledged:
                status = True
                
                if result.matched_count > 0:
                    mode = self.MODE_NOT_CHANGED if result.modified_count == 0 else self.MODE_UPDATED
                    instance_id = result.upserted_id
                else:
                    mode = self.MODE_INSERTED
                    instance_id = result.upserted_id
        except DuplicateKeyError:
            del document['_id']
            return self.upsert(filter, document)
        except WriteError:
            pass

        return status, mode, instance_id

    def row_exists(self, collection, filter):
        collection = self.db[collection]
        result = collection.count_documents(filter)

        return True if result > 0 else False

    def find_all(self, collection, where, custom_fields = None):
        collection = self.db[collection]
        return collection.find(where, custom_fields) if type(custom_fields) is dict else collection.find(where)

    def update_one(self, collection, query, update):
        collection = self.db[collection]
        return collection.update_one(query, update)


class DBWrapper:

    def __init__(self, root_path='./'):
        self.root_path = root_path.rstrip('/') + '/'
        self.dbi = DBI(root_path=root_path)

    def populate_tweets(self, group_name, initial_hashtags = [], flush_output = True, verbosity = True):
        tweets_path = '{}tweets/{}'.format(self.root_path, group_name)

        if not isdir(tweets_path):
            raise Exception("Tweet group does not exist")

        files = [f for f in listdir(tweets_path) if isfile(join(tweets_path, f))]

        if len(files) == 0:
            raise Exception("There is no tweet file in the provided group")

        if flush_output:
            print("Starting to process {} files...\n".format(len(files)))

        files_processed = 0
        tweets_processed = 0
        tweets_stored = 0

        for f in files:
            files_processed += 1
            file_path = join(tweets_path, f)

            if flush_output:
                print("-----------\nProcessing file #{}: {}\n".format(files_processed, f))

            if self.dbi.row_exists('files', {'file_name': f, 'category': group_name}):
                if flush_output:
                    print("\tAlready processed.\n")
                continue

            fh = open(file_path, 'r', encoding='utf-8')
            content = fh.read().split("\n")
            fh.close()

            if flush_output:
                print("\tStarting to process {} tweets...\n".format(len(content)))

            for line in content:
                if len(line) < 10:
                    continue

                tweets_processed += 1

                if flush_output:
                    print("\t***\n\tProcessing tweet #{}...\n".format(tweets_processed))

                tweet = json.loads(line)

                # Replace the tweet with the source if the instnace is only a retweet
                if 'retweeted_status' in tweet and tweet['retweeted_status']:
                    if flush_output and verbosity:
                        print("\t\tRT => Fall back to the source tweet\n")
                    tweet = tweet['retweeted_status']

                if self.__process_tweet(tweet, group_name):
                    tweets_stored += 1

                # Process additional tweet if it matches our input hashtags set
                if 'quoted_status' in tweet:
                    status, new_tweet = self.__validate_quoted_tweet(tweet['quoted_status'], initial_hashtags)
                    if status:
                        tweets_processed += 1
                        if flush_output:
                            print("\t***\n\tProcessing tweet #{}... -- Additional\n".format(tweets_processed))

                        if self.__process_tweet(new_tweet, group_name):
                            tweets_stored += 1

            # Saving file as a processed file
            self.dbi.insert('files', {'file_name': f, 'category': group_name})

        output = {
            'processed_files': files_processed,
            'processed_tweets': tweets_processed,
            'stored_tweets': tweets_stored
        }

        if flush_output:
            print("\nProcess Finished:\n{}\n".format(output))

        return output

    def __process_tweet(self, tweet, group_name, flush_output = True, verbosity = True):
        # Fetch the full text of the tweet
        if 'extended_tweet' in tweet and tweet['extended_tweet']:
            if flush_output and verbosity:
                print("\t\t Extended tweet\n")
            text = tweet['extended_tweet']['full_text']
        else:
            text = tweet['text']

        text = text.encode('utf-16', 'surrogatepass').decode('utf-16')

        # Fetch the tweet source
        pattern = re.compile("(\>)(.+)(\<)")
        source = pattern.search(tweet['source']).group(2)
        if flush_output and verbosity:
            print("\t\tTweeted using {}\n".format(source))

        if tweet['lang']:
            lang = tweet['lang']
            print("\t\tTweet language is {}\n".format(lang))
        else:
            lang = detect(text)
            if flush_output and verbosity:
                print("\t\tLanguage detected as {}\n".format(lang))

        document = {
            '_id': tweet['id_str'],
            'text': text,
            'lang': lang,
            'source': source,
            'category': group_name,
            'quotes': tweet['quote_count'],
            'replies': tweet['reply_count'],
            'faves': tweet['favorite_count'],
            'retweets': tweet['retweet_count'],
            'created_at': tweet['created_at'],
            'quoted_tweet': tweet['quoted_status_id_str'] if 'quoted_status_id_str' in tweet else None,
            'user': {
                '_id': tweet['user']['id_str'],
                'name': tweet['user']['name'],
                'username': tweet['user']['screen_name'],
                'location': tweet['user']['location'],
                'verified': tweet['user']['verified'],
                'followers': tweet['user']['followers_count'],
                'followings': tweet['user']['friends_count'],
                'favourites': tweet['user']['favourites_count'],
                'statuses': tweet['user']['statuses_count']
            }
        }

        if flush_output:
            print("\t\tSaving the tweet... ")

        status, mode, record_id = self.dbi.upsert('tweets', {'_id': tweet['id_str']}, document)

        altered = False

        if status:
            if flush_output:
                print("Done")

            if mode == self.dbi.MODE_INSERTED:
                altered = True
                if flush_output:
                    print(" - Inserted")
            elif mode == self.dbi.MODE_UPDATED:
                altered = True
                if flush_output:
                    print(" - Updated")
            elif mode == self.dbi.MODE_NOT_CHANGED and flush_output:
                print(" - No Change")
        elif flush_output:
            print("Failed")

        if flush_output:
            print("\n")

        return altered

    def __validate_quoted_tweet(self, new_tweet, initial_hashtags):
        if 'retweeted_status' in new_tweet and new_tweet['retweeted_status']:
            new_tweet = new_tweet['retweeted_status']

        if 'extended_tweet' in new_tweet and new_tweet['extended_tweet']:
            tweet_hashtags = new_tweet['extended_tweet']['entities']['hashtags']
        else:
            tweet_hashtags = new_tweet['entities']['hashtags']

        hashtag_matched = False

        # Check initial hashtags in the tweet hashtag entities
        for th in tweet_hashtags:
            for h in initial_hashtags:
                if h.replace('#', '').lower() == th['text'].replace('#', '').lower():
                    hashtag_matched = True
                    break
            
            if hashtag_matched:
                break
        
        # If previous step failed, look for initial hashtags in the plain tweet text
        if not hashtag_matched:
            new_text = new_tweet['extended_tweet']['full_text'] if 'extended_tweet' in new_tweet else new_tweet['text']
            new_text = new_text.encode('utf-16', 'surrogatepass').decode('utf-16').lower()
            for h in initial_hashtags:
                ih = h.replace('#', '').lower()
                if ih in new_text:
                    hashtag_matched = True
                    break

        return hashtag_matched, new_tweet

    def fetch_preprocessing_tweets(self, category = None):
        condition = {
            "lang": "en",
            "$or": [{'preprocessed_text': None}, {'ignored': 1}]
        }

        if category:
            condition['category'] = category

        return self.dbi.find_all('tweets', condition)

    def set_processed_tweet_info(self, id, ignored, processed_text):
        query = {"_id": id}
        update = dict()

        if ignored:
            update["$set"] = {"ignored": 1}
        else:
            update["$set"] = {"preprocessed_text": processed_text}

        return self.dbi.update_one('tweets', query, update)

    def fetch_processed_tweets(self, category = None):
        condition = dict()
        condition['preprocessed_text'] = {'$exists': True}

        if category:
            condition['category'] = category

        result = []
        alt_id = 0
        for tweet in self.dbi.find_all('tweets', condition):
            tweet['alt_id'] = alt_id
            alt_id += 1
            
            result.append(tweet)

        return result