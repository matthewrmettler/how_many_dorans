"""
api_calls.py
By Matthew Mettler (2015)

This python file contains all the necessary functions needed to make calls to the Riot Games API.
"""
from gevent.pool import Pool
from gevent import monkey; monkey.patch_all() # patches stdlib

import requests
import grequests

from time import sleep
from datetime import datetime, timedelta
from timeit import default_timer as timer

import logging
from key import key
__author__ = 'Matt'

max_time = 27
timeout_length = 5.0
info = logging.getLogger().info

def call_api(url, id, param, start_time, attempt_no=0):
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
    print(u"call_api: {req}".format(req = r))
    attempt_no += 1
    try:
        call = requests.get(r, timeout=timeout_length)
    except requests.exceptions.Timeout as e:
        # Try again
        print(e)
        return call_api(url, id, param, start_time, attempt_no)
    except requests.exceptions.TooManyRedirects as e:
        # Tell the user their URL was bad and try a different one
        print(e)
        return 400
    except requests.exceptions.RequestException as e:
        # catastrophic error. bail.
        print(e)
        return 400

    if (time_since > timedelta(seconds=max_time)):
        #Heroku is going to crash soon, just end.
        print("Times up!")
        return 400

    if not hasattr(call, 'status_code'): return call_api(url, id, param, start_time, attempt_no)

    if call.status_code == 200:  # Everything's fine!
        return call
    else:
        print(call.status_code)
        print(call.headers)
        if attempt_no >= 5:   # If it doesn't work after 5 attempts, give up.
            return call
        if call.status_code == 400:  # Bad request -- something is wrong with my code
            return 400
        if call.status_code == 401:  # Unauthorized -- my api key isn't valid
            return 401
        if call.status_code == 404:  # Item not found
            return 404
        if call.status_code == 429:  # Rate limit exceeded -- wait a few seconds
            if 'Retry-After' in call.headers:
                print("retry-after: {rt} ".format(rt=call.headers['Retry-After'] ))
                sleep(float(call.headers['Retry-After']))
            else:
                sleep(1.2)
            return call_api(url, id, param, start_time, attempt_no)
        if call.status_code == 500:  #Internal server error -- something wrong on riot's end -- wait?
            sleep(1.2)
            return call_api(url, id, param, start_time, attempt_no)
        if call.status_code == 503: #service unavailable -- something wrong on riot's end
            sleep(1.2)
            return call_api(url, id, param, start_time, attempt_no)


def gevent_match_call(url):
    info("connecting %s" % url)
    try: call = requests.get(url, timeout=timeout_length)
    except IOError, e:
        info("error %s reason: %s" % (url, e))
    else:
        if call.status_code == 200:
            info("received match %s" % url)
            return call.json()
        else:
            info("error processing match %s" % url)
            return 404


def make_gevent_match_urls(match_list):
    m_urls = []
    for match_id in match_list[:100]:
        match_url = u"https://na.api.pvp.net/{0}{1}{2}{3}{4}".format("api/lol/na/v2.2/match/", match_id,
                                                                     "?includeTimeline=true&", "api_key=", key)
        m_urls.append(match_url)

    return m_urls


def user_exists(username, start_time):
    """
    Check whether or not what the user typed in is an actual League of Legends player.
    :param username: What the user types into our form.
    :param start_time: The time at which the user asked to see his info. Used to track length of calls.
    :return: True if this is an actual League of Legends account.
    """
    print(u"".format(username))
    return get_summoner_id_by_name(username, start_time)


def get_summoner_id_by_name(summoner_name, start_time):
    """
    When the user made their League of Legends account, they chose a username. Riot Games then assigned them a
    'Summoner ID', which is an integer associated with that user. This method gets that ID.
    :param summoner_name: The username of the user in League of Legends.
    :param start_time: The time at which the user asked to see his info. Used to track length of calls.
    :return: An integer associated with the user, for use in every API call going forward.
    """
    result = call_api("api/lol/na/v1.4/summoner/by-name/", summoner_name, "?", start_time)

    # error checking
    if isinstance(result, int):
        return result

    summoner_name = result.json().keys()[0]
    summoner_id = result.json()[summoner_name]["id"]
    print(u"Summoner ID: {0}".format(summoner_id))
    return str(summoner_id)


def get_items_bought(summoner_id, start_time):
    """
    The main method that gets the list of items that the user bought.
    :param summoner_id: ID identifying the user (assigned by Riot Games)
    :param start_time: The time at which the user asked to see his info. Used to track length of calls.
    :return: Dictionary file that contains what items the user bought.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(msg)s")
    info(u"Getting items bought for {0}".format(summoner_id))
    summoner_items = {}
    result = get_list_of_match_ids(summoner_id, start_time)

    # error checking
    if isinstance(result, int):
        return result
    matches = result[0:25]  # shorten the list so its more manageable with lower API
    count = 0

    # gevent
    match_results = []
    m_urls = make_gevent_match_urls(matches)
    pool = Pool(50)
    start = timer()

    for res in pool.imap(gevent_match_call, m_urls):
        match_results.append(res)
        count += 1
    info("%d matches took us %.2g seconds" % (len(m_urls), timer() - start))

    for m in match_results:
        if isinstance(m, int):
            continue
        get_match_items(m, summoner_id, summoner_items)

    return [summoner_items, count]


def get_list_of_match_ids(summoner_id, start_time, include_season_4=False, include_season_3=False):
    """
    Get the match IDs for matches played by the user.
    :param summoner_id: ID identifying the user (assigned by Riot Games)
    :param start_time: The time at which the user asked to see his info. Used to track length of calls.
    :param include_season_4: Include matches from Season 4 (Games played in 2014)
    :param include_season_3: Include matches from Season 3 (Games played in 2013)
    :return: An array of the match IDs under the specific parameters
    """
    result = get_match_list(summoner_id, start_time)

    matches = []
    if isinstance(result, int):
        return result

    for match in result["matches"]:
        if ((match["season"] == "SEASON2015") or (match["season"] == "PRESEASON2015") or
            ((match["season"] == "SEASON2014") and include_season_4 == True) or
            ((match["season"] == "PRESEASON2014") and include_season_4 == True) or
            ((match["season"] == "SEASON2013") and include_season_3 == True)):
            matches.append(match["matchId"])
        else:
            break
    return matches


def get_match_list(summoner_id, start_time, just_solo=True):
    """
    Riot introduced a new match history endpoint recently, called the match list. Match list has significantly
    more matches than the match history endpoint, but it has less data. Since this app must make individual calls
    on each match regardless (in order to see purchases), this new endpoint is much more useful than the old one.
    I will be using this from now on, but will keep the match history code below until it is deprecated September 2015.
    :param summoner_id: ID identifying the user (assigned by Riot Games)
    :param start_time: The time at which the user asked to see his info. Used to track length of calls.
    :param just_solo: Whether or not to include games where the player queued solo, or with a team.
    :return: API call for the match history.
    """
    pass
    param = "{0}".format(("?rankedQueues=RANKED_SOLO_5x5&" if just_solo else "?"))
    result = call_api("api/lol/na/v2.2/matchlist/by-summoner/", summoner_id, param, start_time)

    if isinstance(result, int):
        return result
    if not result:
        return 400

    result = result.json()
    if "matches" not in result:
        return 400
    return result


def get_match_by_id(match_id, start_time):
    """
    Load a specific match with its map ID.
    :param match_id: The ID identifying the specific match we're trying to look at.
    :param start_time: The time at which the user asked to see his info. Used to track length of calls.
    :return: A JSON object representing the match, or an error code representing that it wasn't found.
    """
    match_call = call_api("api/lol/na/v2.2/match/", match_id, "?includeTimeline=true&", start_time)
    if isinstance(match_call, int):
        return match_call
    return match_call.json()


def get_match_items(match, summoner_id, summoner_items):
    """
    Get the items that the user purchased during the course of the game.
    :param match: The JSON file for our match.
    :param summoner_id: ID identifying the user (assigned by Riot Games)
    :param summoner_items: The dictionary that we update for each match, containing the number of items the user bought.
    :return:
    """
    p_id = get_participant_id(match, summoner_id)
    timeline_frames = match["timeline"]["frames"]

    for frame in timeline_frames:
        if "events" in frame:
            for event in frame["events"]:
                if (event["eventType"] == "ITEM_PURCHASED") and (event["participantId"] == p_id):
                    item = event["itemId"]
                    if item in summoner_items:
                        summoner_items[item] += 1
                    else:
                        summoner_items[item] = 1
    return False


def get_participant_id(match, summoner_id):
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
