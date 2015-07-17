"""
api_calls.py
By Matthew Mettler (2015)

This python file contains all the necessary functions needed to make calls to the Riot Games API.
"""
import requests
from time import sleep
__author__ = 'Matt'
"""Please don't deploy like this you dummy"""
key = "efaea909-5db0-45b4-aed3-325fe5c1f4eb"

def user_exists(username):
    """
    Check whether or not what the user typed in is an actual League of Legends player.
    :param username: What the user types into our form.
    :return: True if this is an actual League of Legends account.
    """
    return getSummonerIDByName(username)

def getItemsBought(summoner_id):
    """
    The main method that gets the list of items that the user bought.
    :param summoner_id: ID identifying the user (assigned by Riot Games)
    :return: Dictionary file that contains what items the user bought.
    """
    print("Getting items bought for {0}".format(summoner_id))
    sleep(2.0)
    summoner_items = {}
    matches = getMatches(summoner_id)
    #print(matches)
    #for matchID in matches:
        #getMatchItems(getMatch(matchID), summoner_id, summoner_items)
    getMatchItems(getMatch(matches[0]), summoner_id, summoner_items)
    #print(len(matches))
    return [summoner_items, len(matches)]

def getMatch(match_id):
    """Load the match with a Riot API call"""
    match_call = requests.get("https://na.api.pvp.net/api/lol/na/v2.2/match/{0}?includeTimeline=true&api_key={1}".format(match_id, key))
    #print(match_call.status_code)
    if int(match_call.status_code) == 200: return match_call.json()
    return False

def callAPI(url, param):
    """
    For ease of use, simpler API calls use this method.
    :param url: The specific type of API call being made
    :param param: Additional parameters, such as summoner ID.
    :return: The requests response from the API call.
    """
    sleep(1.0)
    return requests.get("https://na.api.pvp.net/{0}{1}{2}{3}".format(url, param, "?api_key=", key))

def getSummonerIDByName(summoner_name):
    """
    When the user made their League of Legends account, they chose a username. Riot Games then assigned them a
    'Summoner ID', which is an integer associated with that user. This method gets that ID.
    :param summoner_name: The username of the user in League of Legends.
    :return: An integer associated with the user, for use in every API call going forward.
    """
    summoner_data = callAPI("api/lol/na/v1.4/summoner/by-name/", summoner_name)
    if summoner_data.status_code != 200: return False
    summoner_name = summoner_data.json().keys()[0]
    summoner_id = summoner_data.json()[summoner_name]["id"]
    print("Summoner ID: {0}".format(summoner_id))
    return summoner_id

def getMatchHistory(summoner_id, beginIndex, justSolo=True):
    """
    Calls the API endpoint for the match history beginning and ending at these indices
    Can only return 15 matches at a time.
    :param summoner_id: ID identifying the user (assigned by Riot Games)
    :param beginIndex: Index starting point for this specific call of this method.
    :param justSolo: Whether or not to include games where the player queued solo, or with a team.
    :return: API call for the match history.
    """
    print("Getting match history for {0} at index {1}".format(summoner_id, beginIndex))
    global key

    sleep(1.0)
    matches_call = requests.get("https://na.api.pvp.net/api/lol/na/v2.2/matchhistory/{0}?{1}beginIndex={2}&api_key={3}".format(summoner_id, "rankedQueues=RANKED_SOLO_5x5&" if justSolo else "", beginIndex, key))
    #print(matches_call.status_code)
    if matches_call.status_code != 200: return False
    return matches_call

def getMatches(summoner_id, includeSeason4=False, includeSeason3=False, maxIndex=15):
    """
    Get the match IDs for matches played by the user.
    :param summoner_id: ID identifying the user (assigned by Riot Games)
    :param includeSeason4: Include matches from Season 4 (Games played in 2014)
    :param includeSeason3: Include matches from Season 3 (Games played in 2013)
    :param maxIndex: The maximum number of games to go back (Will always pull in multiples of 15)
    :return: An array of the match IDs under the specific parameters
    """
    pullData = True
    index = 0
    matches = []
    while(pullData):
        match_json = getMatchHistory(summoner_id, index).json()
        if not match_json: break
        if not "matches" in match_json: break
        for match in match_json["matches"][::-1]: #reverse array to get more recent games first
            #print([(match["season"] == "SEASON2015"), match["season"] == "SEASON2014", includeSeason4 == True, ((match["season"] == "SEASON2014") and includeSeason4 == True)])
            if ( (match["season"] == "SEASON2015") or (match["season"] == "PRESEASON2015") or ((match["season"] == "SEASON2014") and includeSeason4 == True) or ((match["season"] == "PRESEASON2014") and includeSeason4 == True) or ((match["season"] == "SEASON2013") and includeSeason3 == True)):
                matches.append(match["matchId"])
            else:
                #print("found an old game, breaking...{0}".format(len(matches)))
                pullData = False
                break
        index += 15
        if index >= maxIndex: break
        #sleep(1.2) #sleep for rito
    return matches

def getParticipantId(match, summoner_id):
    """
    In each match, each player is given a participant ID. For all intents and purposes, it's random, and we need to get
    the summoner ID for our actual user. This function does that by comparing the summoner IDs of each participant with
    our user's summoner ID.
    :param match: The JSON file for our match.
    :param summoner_id: ID identifying the user (assigned by Riot Games)
    :return: An integer associated with our user, for use in other methods.
    """
    print("Checking match {0} for summoner's participant ID...".format(str(match["matchId"])))
    participants = match["participantIdentities"]
    for p in participants:
        if p["player"]["summonerId"] == summoner_id:
            #print("Participant id is {0}".format(p["participantId"]))
            return p["participantId"]

def getMatchItems(match, summoner_id, summoner_items):
    """
    Get the items that the user purchased during the course of the game.
    :param match: The JSON file for our match.
    :param summoner_id: ID identifying the user (assigned by Riot Games)
    :param summoner_items: The dictionary that we update for each match, containing the number of items the user bought.
    :return:
    """
    print("Checking match {0} for items...".format(str(match["matchId"])))
    pID = getParticipantId(match, summoner_id)
    timeline_frames = match["timeline"]["frames"]
    #print(len(timeline_frames))
    for frame in timeline_frames:
        if "events" in frame:
            for event in frame["events"]:
                if (event["eventType"] == "ITEM_PURCHASED") and event["participantId"] == pID:
                    item = event["itemId"]
                    #print("Item {0} purchased!".format(item))
                    if item in summoner_items:
                        summoner_items[item] += 1
                    else:
                        summoner_items[item] = 1
    return False


