import sys
sys.path.insert(1, '../')
from os import listdir, makedirs
from os.path import isfile, join, exists
from modules.helper import Helper
from TwitterAPI import TwitterAPI, TwitterPager, TwitterRequestError
from urllib import parse
import json
import datetime

class TweetCollector:

    COLLECT_MODE_30DAYS = 'endpoint_30day'
    COLLECT_MODE_ARCHIVE = 'endpoint_archive'

    def __init__(self, group_name, root_path = './', strict_mode = True, collect_mode = COLLECT_MODE_30DAYS):
        self.collect_mode = collect_mode
        self.root_path = root_path.rstrip('/') + '/'
        self.helper = Helper(self.root_path)
        self.strict_mode = strict_mode
        self.group_name = group_name
        self.__initiate_api()

        if not exists('{}tweets'.format(self.root_path)):
            makedirs('{}tweets'.format(self.root_path))

    def initiate_collection(self, hashtags, toDate = None):
        self.hashtags = hashtags
        self.toDate = toDate

        if self.strict_mode:
            tweet_files = "{}tweets/{}".format(self.root_path, self.group_name)

            if not exists(tweet_files):
                makedirs(tweet_files)

            files = [f for f in listdir(tweet_files) if isfile(join(tweet_files, f))]
            
            if len(files) > 0:
                print("You're in strict mode. Either enter non strict mode or delete tweet files under ./tweets/{} directory.".format(self.group_name))
                return

        try:
            self.__collect_tweets()
        except TwitterRequestError as e:
            print("Failed to fetch tweets. Check your API limitation in Twitter dashboard.\n")

    def __initiate_api(self):
        consumer_key = self.helper.config_item('twitter_config.consumer_key')
        consumer_secret = self.helper.config_item('twitter_config.consumer_secret')
        access_token = self.helper.config_item('twitter_config.access_token')
        access_token_secret = self.helper.config_item('twitter_config.access_token_secret')

        self.api = TwitterAPI(consumer_key, consumer_secret, access_token, access_token_secret)

    def __collect_tweets(self):
        self.__prepare_request()

        print("Starting to save tweets...\n")
        count = 0
        temp_repo = ""

        for item in self.pager.get_iterator():
            if 'text' in item:
                temp_repo += json.dumps(item)
                temp_repo += "\n"
                count += 1
                
                if count % 100 == 0:
                    print("{} tweets already stored in file...\n".format(count))
                    
                    dt = datetime.datetime.now()
                    file_name = '{}tweets/{}/{}{}_{}{}{}.wtr'.format(self.root_path, 
                        self.group_name, dt.strftime('%b'), dt.strftime('%d'), 
                        dt.strftime('%H'), dt.strftime('%M'), dt.strftime('%S'))

                    f = open(file_name, "a+")
                    f.write(temp_repo)
                    f.close()
                    temp_repo = ""
            elif 'message' in item:
                print("Process Stoped:\n")
                print("{}: {}".format(item['code'], item['message']))
                break
            else:
                print("No Text Entry Detected:\n")
                print(item)
                break

        if len(temp_repo) > 0:
            print("{} tweets already stored in file...\n".format(count))
                    
            dt = datetime.datetime.now()
            file_name = '{}tweets/{}/{}{}_{}{}{}.wtr'.format(self.root_path, 
                self.group_name, dt.strftime('%b'), dt.strftime('%d'), 
                dt.strftime('%H'), dt.strftime('%M'), dt.strftime('%S'))

            f = open(file_name, "a+")
            f.write(temp_repo)
            f.close()

    def __prepare_request(self):
        hash_combine = self.hashtags if(type(self.hashtags) is str) else " OR ".join(self.hashtags)
        query = "({}) lang:en".format(hash_combine)
        endpoint = self.helper.config_item('twitter_config.{}'.format(self.collect_mode))

        request_config = {
            'query': query,
            'maxResults': 100
        }

        if self.toDate != None:
            if not self.__validate_parameter(self.toDate, 'toDate'):
                raise Exception(self.validation_error)
            else:
                request_config['toDate'] = self.toDate
         
        self.pager = TwitterPager(self.api, endpoint, request_config)
    
    def __validate_parameter(self, value, category):
        output = False

        if category == 'toDate' or category == 'fromDate':
            if type(value) is not str:
                self.validation_error = 'toDate must be in string format'
            elif len(value) != 12:
                self.validation_error = 'toDate must be in yyyyMMddHHmm format'
            else:
                output = True
        else:
            self.validation_error = 'Provided parameter is not supported'

        return output