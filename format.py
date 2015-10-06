__author__ = 'Matt'
from api_calls import get_items_bought
from items import static_items_dict, item_id_adjust
import urllib2
import json
import operator
lol_patch = '5.18.1'  # use this for api calls


class Item:
    def __init__(self, item_id, count, name, url):
        self.id = item_id
        self.count = count
        self.name = name
        self.url = url
        self.type = -1

    def __repr__(self):
        return "{0} (ID {1}, Count {2}, Type {3})".format(self.name, self.id, self.count, self.type)

    def __str__(self):
        return "{0} (ID {1}, Count {2}, Type {3})".format(self.name, self.id, self.count, self.type)


def get_image_url(item_id):
    return "http://ddragon.leagueoflegends.com/cdn/{0}/img/item/{1}.png".format(lol_patch, item_id)


def create_item_set(summoner_id, start_time):
    items_array = []
    api_call = get_items_bought(summoner_id, start_time)

    # error check
    if isinstance(api_call, int):
        return api_call

    items_dict = api_call[0]
    match_no = api_call[1]

    sorted_items_dict = sorted(items_dict.items(), key=operator.itemgetter(1), reverse=True)  # convert to sorted tuples

    for i in sorted_items_dict:
        v_id = verify_id(i[0])
        if v_id:
            items_array.append(Item(v_id, i[1], get_name(v_id), get_image_url(v_id)))
        else:
            continue

    final_array = categorize(items_array)
    return [final_array, match_no]


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
        item_id = str(item.id)
        if item_id in data:
            if "tags" in data[item_id]:
                if "Consumable" in data[item_id]["tags"]:
                    item.type = 1
                    continue
            if "from" in data[item_id]:
                if "into" in data[item_id]:
                    if len(data[item_id]["into"]) > 0:  # botrk has empty into, so i need to check
                        item.type = 3
                    else:
                        item.type = 4
            else:  # nothing builds into this item, so it's a basic item
                # check for biscuit
                if (int(item_id) == 2009) or (int(item_id) == 2010):
                    item.type = 1
                else:
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
    temp = [[], [], [], []]

    for item in item_set:
            temp[4-item.type].append(item)  # want type 4 in index 0

    max_length = max(len(temp[0]), len(temp[1]), len(temp[2]), len(temp[3]))
    for item_type in temp:
        while len(item_type) < max_length:
            # Fill empty slots with blank items
            item_type.append(Item("", "", "", "http://ddragon.leagueoflegends.com/cdn/5.2.1/img/ui/items.png"))
    result = zip(temp[0], temp[1], temp[2], temp[3])
    return result


def verify_id(item_id):
    """Checks to see if this is a valid item. Checks current match, and then checks past item ids."""
    if item_id in static_items_dict:
        return item_id
    elif item_id in item_id_adjust:
        return item_id_adjust[item_id]
    else:
        return False


def get_name(item_id):
    return static_items_dict[item_id]