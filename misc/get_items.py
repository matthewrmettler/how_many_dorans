__author__ = 'Matt'
"""
Run to get a pretty dictionary file for item names.
"""
from urllib2 import urlopen
from json import load
import collections
import pprint

def getStaticItems():
	weps = {}

	response = urlopen('http://ddragon.leagueoflegends.com/cdn/5.13.1/data/en_US/item.json')
	json = load(response)
	data = json["data"]
	for i in data:
		weps[int(i)] = data[i]["name"]

	pp = pprint.PrettyPrinter(indent=4)
	pp.pprint(weps)

getStaticItems()
