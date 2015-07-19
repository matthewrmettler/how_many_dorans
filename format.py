__author__ = 'Matt'
from api_calls import getItemsBought
from items import static_items_dict, item_id_adjust
import urllib2
import json

import operator
lol_patch = '5.13.1' #use this for api calls

class Item:
    def __init__(self, id, count, name, url):
        self.id = id
        self.count = count
        self.name = name
        self.url = url
        self.type = -1
        #print(self)

    def __repr__(self):
        return "{0} (ID {1}, Count {2}, Type {3})".format(self.name, self.id, self.count, self.type)

    def __str__(self):
        return "{0} (ID {1}, Count {2}, Type {3})".format(self.name, self.id, self.count, self.type)

def getImageUrl(item_id):
    return "http://ddragon.leagueoflegends.com/cdn/{0}/img/item/{1}.png".format(lol_patch, item_id)

def createItemSet(summoner_id, start_time):
    #print(u"{0} --- Creating item sets for {1}".format(format(start_time), summoner_id))
    items_array = []
    api_call = getItemsBought(summoner_id, start_time)
    if hasattr(api_call, 'status_code'): return api_call #error check
    #print("getItemsBought finished")
    items_dict = api_call[0]
    matchNo = api_call[1]
    #print(matchNo)
    sorted_items_dict = sorted(items_dict.items(), key=operator.itemgetter(1), reverse=True) #convert to sorted tuples
    #print(sorted_items_dict)
    for i in sorted_items_dict:
        vID = verify_id(i[0])
        if (vID):
            items_array.append(Item(vID, i[1], getName(vID), getImageUrl(vID)))
        else:
            continue
    final_array = categorize(items_array)
    #print("{0} --- item sets made".format(datetime.utcnow()))
    return [final_array, matchNo]

def categorize(item_set):
    """
    Categorize items into four sections: Final, intermediate, basic, and consumable items.
    Type 1-4 (consumable is type 1, final is type 4)
    :param item_set:
    :return:
    """
    response = urllib2.urlopen('http://ddragon.leagueoflegends.com/cdn/5.13.1/data/en_US/item.json')
    json_result = json.load(response)
    data = json_result["data"]
    for item in item_set:
        id = str(item.id)
        if id in data:
            if "tags" in data[id]:
                if "Consumable" in data[id]["tags"]:
                    item.type = 1
                    continue
            if "from" in data[id]:
                if "into" in data[id]:
                    if len(data[id]["into"]) > 0: #botrk has empty into, so i need to check
                        item.type = 3
                    else:
                        item.type = 4
            else: #nothing builds into this item, so it's a basic item
                item.type = 2
    new_item_set = zip_item_set(item_set)
    return new_item_set

def zip_item_set(item_set):
    """
    Since we'll be displaying the 4 categories as columns, but using tables with jinja, we need a list of lists, where
    each inner list is [1_x, 2_x, 3_x, 4_x], where x is the xth largest item for type 1..4. So we group the types
    together into 4 lists, one for each type, pad the lists with empty items such that they're all the same length, then
    zip them such that we have a convenient data structure to use for jinja templating.
    :param item_set: The item set to be zipped
    :return: A zipped list of tuples
    """
    #print("Zipping item set.")
    temp = [[],[],[],[]]

    max_length = max(len(temp[0]), len(temp[1]), len(temp[2]), len(temp[3]))
    for type in temp:
        while (len(type) < max_length):
            type.append(Item("","","","http://ddragon.leagueoflegends.com/cdn/5.2.1/img/ui/items.png"))
    result = zip(temp[0], temp[1], temp[2], temp[3])
    return result

def verify_id(item_id):
    if item_id in static_items_dict:
        return item_id
    elif item_id in item_id_adjust:
        #print("Changed id {0} to {1}".format(item_id, item_id_adjust[item_id]))
        return item_id_adjust[item_id]
    else:
        #print("{0} not found, skipping".format(item_id))
        return False

def getName(item_id):
    return static_items_dict[item_id]