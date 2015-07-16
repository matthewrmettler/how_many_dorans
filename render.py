__author__ = 'Matt'
from api_calls import getItemsBought
from items import static_items_dict
import operator
lol_patch = '5.13.1' #use this for api calls

class Item:
    def __init__(self, id, count, name, url):
        self.id = id
        self.count = count
        self.name = name
        self.url = url
        print("item created! {0} {1} {2} {3}".format(id, count, name, url))

def getImageUrl(item_id):
    return "http://ddragon.leagueoflegends.com/cdn/{0}/img/item/{1}.png".format(lol_patch, item_id)

def createItemSet(summoner_id):
    print("Creating item sets for {0}".format(summoner_id))
    items_array = []
    items_dict = getItemsBought(summoner_id)
    #sort items by most bought
    #print(items_dict)
    sorted_items_dict = sorted(items_dict.items(), key=operator.itemgetter(1), reverse=True) #convert to sorted tuples
    #print(sorted_items_dict)
    for i in sorted_items_dict:
        #print(i[0])
        #print(i[1])
        #print(static_items_dict[i[0]])
        #print(getImageUrl(i[0]))
        items_array.append(Item(i[0], i[1], static_items_dict[i[0]], getImageUrl(i[0])))
    #for i in items_array:
        #print(i)
    return items_array
