"""
api_calls.py
By Matthew Mettler (2015)

This python file contains all the necessary functions needed to make calls to the Riot Games API.
"""
import requests
import grequests
from time import sleep
from datetime import datetime, timedelta
from key import key
__author__ = 'Matt'

max_time = 27
timeout_length = 5.0

def callAPI(url, id, param, start_time, attemptNo=0):
    """
    For ease of use, simpler API calls use this method.
    :param url: The specific type of API call being made
    :param param: Additional parameters, such as summoner ID.
    :param start_time: The time at which the user asked to see his info. Used to track length of calls.
    :return: The requests response from the API call.
    """
    current_time = datetime.utcnow()
    time_since = current_time - start_time
    #print(time_since)

    r = u"https://na.api.pvp.net/{0}{1}{2}{3}{4}".format(url, id, param, "api_key=", key)
    print(u"CallAPI: {req}".format(req = r))
    call = ""
    attemptNo += 1
    try:
        call = requests.get(r, timeout=timeout_length)
    except requests.exceptions.Timeout as e:
        # Try again
        print(e)
        return callAPI(url, id, param, start_time, attemptNo)
    except requests.exceptions.TooManyRedirects as e:
        # Tell the user their URL was bad and try a different one
        print(e)
        return 400
    except requests.exceptions.RequestException as e:
        # catastrophic error. bail.
        print(e)
        return 400

    if (time_since > timedelta(seconds=max_time)):
        #heroku is going to crash soon, just end
        print("Times up!")
        return 400

    if not hasattr(call, 'status_code'): return callAPI(url, id, param, start_time, attemptNo)

    if call.status_code == 200: #everything's fine
        return call
    else:
        print(call.status_code)
        print(call.headers)
        if attemptNo >= 8: #if it doesnt work after 8 tries, give up
            return call
        if call.status_code == 400: #Bad request -- something is wrong with my code, show an error, DO NOT keep making calls
            return 400
        if call.status_code == 401: #Unauthorized -- my api key isn't valid, show a page for this
            return 401
        if call.status_code == 404: #item not found -- do something about this
            return 404
        if call.status_code == 429: #Rate limit exceeded -- wait a few seconds
            if 'Retry-After' in call.headers:
                print("retry-after: {rt} ".format(rt=call.headers['Retry-After'] ))
                sleep(float(call.headers['Retry-After']))
            else:
                sleep(1.2)
            return callAPI(url, id, param, start_time, attemptNo)
        if call.status_code == 500: #Internal server error -- something wrong on riot's end -- wait?
            sleep(1.2)
            return callAPI(url, id, param, start_time, attemptNo)
        if call.status_code == 503: #service unavailable -- something wrong on riot's end
            sleep(1.2)
            return callAPI(url, id, param, start_time, attemptNo)

def greq_match_call(match_urls):
    print("{0}: greq_match_calls".format(datetime.now()))
    rs = (grequests.get(r) for r in match_urls)
    res = grequests.map(rs)
    print(res)
    print("{0}: greq_match_calls complete".format(datetime.now()))
    res = [x.json() for x in res]
    return res

def make_greq_match_urls(match_list):
    m_urls = []
    for match_id in match_list[:100]:
        match_url = u"https://na.api.pvp.net/{0}{1}{2}{3}{4}".format("api/lol/na/v2.2/match/", match_id, "?includeTimeline=true&", "api_key=", key)
        m_urls.append(match_url)

    return m_urls

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
    result = callAPI("api/lol/na/v1.4/summoner/by-name/", summoner_name, "?", start_time)

    #error checking
    if isinstance(result, int): return result

    summoner_name = result.json().keys()[0]
    summoner_id = result.json()[summoner_name]["id"]
    print(u"Summoner ID: {0}".format(summoner_id))
    return str(summoner_id)

def getItemsBought(summoner_id, start_time):
    """
    The main method that gets the list of items that the user bought.
    :param summoner_id: ID identifying the user (assigned by Riot Games)
    :param start_time: The time at which the user asked to see his info. Used to track length of calls.
    :return: Dictionary file that contains what items the user bought.
    """
    print(u"Getting items bought for {0}".format(summoner_id))
    summoner_items = {}
    result = getMatches(summoner_id, start_time)

    #error checking
    if isinstance(result, int): return result
    matches = result[0:50] #shorten the list so its more manageable with lower API
    count = 0

    #try chunking up the match results
    #match_chunked = [ result[0:10], result[10:20], result[20:30], result[30:40], result[40:50] ]
    match_results = []
    #for matches in match_chunked:
    m_urls = make_greq_match_urls(matches)
    match_results += greq_match_call(m_urls)
    for m in match_results:
        if isinstance(m, int):
            print("Getting match {0} failed".format(m))
            continue
        getMatchItems(m, summoner_id, summoner_items)
        count += 1

    #Old synchrous code, let's try greq above
    """
    for matchID in matches:
        m = getMatch(matchID, start_time)
        #error checking, skip broken matches
        if isinstance(m, int):
            print("Getting match {0} failed".format(matchID))
            continue
        getMatchItems(m, summoner_id, summoner_items)
        count += 1

    print(summoner_items)
    """
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

        #result = getMatchHistory(summoner_id, index, start_time).json()
        result = getMatchList(summoner_id, start_time)

        if isinstance(result, int):
            return result
        #everything should be good
        for match in result["matches"]:
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

def getMatchList(summoner_id, start_time, justSolo=True, includeSeason4=False, includeSeason3=False):
    """
    Riot introduced a new match history endpoint recently, called the match list. Match list has significantly
    more matches than the match history endpoint, but it has less data. Since this app must make individual calls
    on each match regardless (in order to see purchases), this new endpoint is much more useful than the old one.
    I will be using this from now on, but will keep the match history code below until it is deprecated September 2015.
    :param summoner_id: ID identifying the user (assigned by Riot Games)
    :param start_time: The time at which the user asked to see his info. Used to track length of calls.
    :param justSolo: Whether or not to include games where the player queued solo, or with a team.
    :param includeSeason4: Include matches from Season 4 (Games played in 2014)
    :param includeSeason3: Include matches from Season 3 (Games played in 2013)
    :return: API call for the match history.
    """
    pass
    param = "{0}".format(("?rankedQueues=RANKED_SOLO_5x5&" if justSolo else "?"))
    result = callAPI("api/lol/na/v2.2/matchlist/by-summoner/", summoner_id, param, start_time)
    #print(result)
    #print(type(result))
    #error checking
    if isinstance(result, int):
        return result
    if not result:
        return 400

    result = result.json()

    if not "matches" in result:
        return 400

    return result

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
    matches_call = callAPI("api/lol/na/v2.2/matchhistory/", summoner_id, param, start_time)
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
    if isinstance(match_call, int):
        return match_call
    return match_call.json()

def getMatchItems(match, summoner_id, summoner_items):
    """
    Get the items that the user purchased during the course of the game.
    :param match: The JSON file for our match.
    :param summoner_id: ID identifying the user (assigned by Riot Games)
    :param summoner_items: The dictionary that we update for each match, containing the number of items the user bought.
    :return:
    """
    print("getMatchItems")
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
        if p["player"]["summonerId"] == int(summoner_id):
            return p["participantId"]
