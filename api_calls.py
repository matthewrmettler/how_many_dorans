"""
api_calls.py
By Matthew Mettler (2015)

This python file contains all the necessary functions needed to make calls to the Riot Games API.
"""
import requests
from time import sleep
from datetime import datetime, timedelta
from api_key import key
__author__ = 'Matt'

max_time = 27
def callAPI(url, id, param, start_time, attemptNo=0):
    """
    For ease of use, simpler API calls use this method.
    :param url: The specific type of API call being made
    :param param: Additional parameters, such as summoner ID.
    :param start_time: The time at which the user asked to see his info. Used to track length of calls.
    :return: The requests response from the API call.
    """
    print(u"CallAPI: {0}|{1}|{2}|{3}|{4}".format(url, id, param, attemptNo, key))

    current_time = datetime.utcnow()
    time_since = current_time - start_time
    #print(time_since)

    r = u"https://na.api.pvp.net/{0}{1}{2}{3}{4}".format(url, id, param, "api_key=", key)
    call = requests.get(r)

    if (time_since > timedelta(seconds=max_time)):
        #heroku is going to crash soon, just end
        print("Times up!")
        print(call)
        print(call.status_code)
        call.status_code = 429
        print(call.status_code)
        return call

    if call.status_code == 200: #everything's fine
        return call
    else:
        #print(call.status_code)
        attemptNo += 1
        if attemptNo >= 8: #if it doesnt work after 8 tries, give up
            return call
        if call.status_code == 400: #Bad request -- something is wrong with my code, show an error, DO NOT keep making calls
            return call
        if call.status_code == 401: #Unauthorized -- my api key isn't valid, show a page for this
            return call
        if call.status_code == 404: #item not found -- do something about this
            return call
        if call.status_code == 429: #Rate limit exceeded -- wait a few seconds
            sleep(1.2)
            return callAPI(url, id, param, start_time, attemptNo)
        if call.status_code == 500: #Internal server error -- something wrong on riot's end -- wait?
            sleep(5.0)
            return callAPI(url, id, param, start_time, attemptNo)
        if call.status_code == 503: #service unavailable -- something wrong on riot's end
            sleep(5.0)
            return callAPI(url, id, param, start_time, attemptNo)

def userExists(username, start_time):
    """
    Check whether or not what the user typed in is an actual League of Legends player.
    :param username: What the user types into our form.
    :param start_time: The time at which the user asked to see his info. Used to track length of calls.
    :return: True if this is an actual League of Legends account.
    """
    print(u"".format(username))
    return getSummonerIDByName(username, start_time)

def getSummonerIDByName(summoner_name, start_time):
    """
    When the user made their League of Legends account, they chose a username. Riot Games then assigned them a
    'Summoner ID', which is an integer associated with that user. This method gets that ID.
    :param summoner_name: The username of the user in League of Legends.
    :param start_time: The time at which the user asked to see his info. Used to track length of calls.
    :return: An integer associated with the user, for use in every API call going forward.
    """
    summoner_data = callAPI("api/lol/na/v1.4/summoner/by-name/", summoner_name, "?", start_time)
    if summoner_data.status_code == 200:
        summoner_name = summoner_data.json().keys()[0]
        summoner_id = summoner_data.json()[summoner_name]["id"]
        print(u"Summoner ID: {0}".format(summoner_id))
        return summoner_id
    else:
        return summoner_data

def getItemsBought(summoner_id, start_time):
    """
    The main method that gets the list of items that the user bought.
    :param summoner_id: ID identifying the user (assigned by Riot Games)
    :param start_time: The time at which the user asked to see his info. Used to track length of calls.
    :return: Dictionary file that contains what items the user bought.
    """
    print(u"Getting items bought for {0}".format(summoner_id))
    summoner_items = {}
    matches = getMatches(summoner_id, start_time)
    if hasattr(matches, 'status_code'): return matches #error check
    matches = matches[:-5] #shorten the list so its more manageable with lower API
    count = 0
    for matchID in matches:
        m = getMatch(matchID, start_time)
        if not hasattr(m, 'status_code'):
            getMatchItems(m, summoner_id, summoner_items)
            count += 1
        else:
            return m
    print(summoner_items)
    return [summoner_items, count]

def getMatches(summoner_id, start_time, includeSeason4=False, includeSeason3=False, maxIndex=15):
    """
    Get the match IDs for matches played by the user.
    :param summoner_id: ID identifying the user (assigned by Riot Games)
    :param start_time: The time at which the user asked to see his info. Used to track length of calls.
    :param includeSeason4: Include matches from Season 4 (Games played in 2014)
    :param includeSeason3: Include matches from Season 3 (Games played in 2013)
    :param maxIndex: The maximum number of games to go back (Will always pull in multiples of 15)
    :return: An array of the match IDs under the specific parameters
    """
    pullData = True
    index = 0
    matches = []
    while(pullData):
        match_json = getMatchHistory(summoner_id, index, start_time).json()
        if 'status' in match_json:
            if 'status_code' in match_json['status']:
                return match_json #error check
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
    return matches

def getMatchHistory(summoner_id, beginIndex, start_time, justSolo=True):
    """
    Calls the API endpoint for the match history beginning and ending at these indices
    Can only return 15 matches at a time.
    :param summoner_id: ID identifying the user (assigned by Riot Games)
    :param beginIndex: Index starting point for this specific call of this method.
    :param start_time: The time at which the user asked to see his info. Used to track length of calls.
    :param justSolo: Whether or not to include games where the player queued solo, or with a team.
    :return: API call for the match history.
    """
    print("Getting match history for {0} at index {1}".format(summoner_id, beginIndex))
    global key

    param = "{0}beginIndex={1}&".format(("?rankedQueues=RANKED_SOLO_5x5&" if justSolo else "?"), beginIndex)
    matches_call = callAPI("api/lol/na/v2.2/matchhistory/",summoner_id, param, start_time)
    return matches_call

def getMatch(match_id, start_time):
    """
    Load a specific match with its map ID.
    :param match_id: The ID identifying the specific match we're trying to look at.
    :param start_time: The time at which the user asked to see his info. Used to track length of calls.
    :return: A JSON object representing the match, or an error code representing that it wasn't found.
    """
    match_call = callAPI("api/lol/na/v2.2/match/", match_id, "?includeTimeline=true&", start_time)
    #print(match_call.status_code)
    if int(match_call.status_code) == 200: return match_call.json()
    return match_call

def getMatchItems(match, summoner_id, summoner_items):
    """
    Get the items that the user purchased during the course of the game.
    :param match: The JSON file for our match.
    :param summoner_id: ID identifying the user (assigned by Riot Games)
    :param summoner_items: The dictionary that we update for each match, containing the number of items the user bought.
    :return:
    """
    pID = getParticipantId(match, summoner_id)
    timeline_frames = match["timeline"]["frames"]

    for frame in timeline_frames:
        if "events" in frame:
            for event in frame["events"]:
                if (event["eventType"] == "ITEM_PURCHASED") and event["participantId"] == pID:
                    item = event["itemId"]
                    if item in summoner_items:
                        summoner_items[item] += 1
                    else:
                        summoner_items[item] = 1
    return False

def getParticipantId(match, summoner_id):
    """
    In each match, each player is given a participant ID. For all intents and purposes, it's random, and we need to get
    the summoner ID for our actual user. This function does that by comparing the summoner IDs of each participant with
    our user's summoner ID.
    :param match: The JSON file for our match.
    :param summoner_id: ID identifying the user (assigned by Riot Games)
    :return: An integer associated with our user, for use in other methods.
    """
    participants = match["participantIdentities"]
    for p in participants:
        if p["player"]["summonerId"] == summoner_id:
            return p["participantId"]
