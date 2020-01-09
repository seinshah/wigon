import yaml
import os
from os.path import isfile
import json

class Helper:

    def __init__(self, root_path):
        self.root_path = root_path.strip('/') + "/"
        self.config_path = "{}config.yaml".format(self.root_path)

        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as stream:
                self.configs = yaml.safe_load(stream) 
        else:
            raise Exception('Config file not found!')

    def config_item(self, index, default = None):
        output = default

        if type(index) is str:
            indexes = index.split('.')
            last_elem = self.configs
            counter = 0
            
            for conf in indexes:
                counter += 1

                try:
                    if counter == len(indexes):
                        if conf in last_elem:
                            output = last_elem[conf]
                        break
                    else:
                        last_elem = last_elem[conf]
                except IndexError:
                    output = default
                    break
                except KeyError:
                    output = default
                    break

        return output

    def slang_hashmap(self):
        file_path = self.config_item('global.slang_file')
        file_path_complete = "{}{}".format(self.root_path, file_path)
        
        if(file_path and isfile(file_path_complete)):
            hashmap = open(file_path_complete, "r", encoding='utf-8')
            result = json.loads(hashmap.read())
            hashmap.close()

            return result

        return dict()