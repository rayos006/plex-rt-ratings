# -*- coding: utf-8 -*-

#------------------------------------------------------------------------------
#                 Plex rotten tomatoes script by rayos006
#                               CODE TAKEN FROM:
#                 Plex movie ratings script by /u/SwiftPanda16
#         https://gist.github.com/JonnyWong16/d0972e1913941790670708dd99eecf65
#
#                         *** Use at your own risk! ***
#   *** I am not responsible for damages to your Plex server or libraries. ***
#
#------------------------------------------------------------------------------

# Requires: plexapi, rotten_tomatoes_client, beautifulsoup4, requests

import re
from plexapi.server import PlexServer
from rotten_tomatoes_client import RottenTomatoesClient
import requests
from bs4 import BeautifulSoup
import subprocess
import os


### EDIT SETTINGS ###

PLEX_URL = os.environ['PLEX_ADDRESS']
PLEX_TOKEN = os.environ['PLEX_TOKEN']
TV_LIBRARY_NAME = os.environ['PLEX_TV_LIBRARY']
MOVIE_LIBRARY_NAME = os.environ['PLEX_MOVIE_LIBRARY']
PLEX_DB_LOCATION = os.environ['PLEX_DB_LOCATION']
PLEX_DB_NAME = os.environ['PLEX_DB_NAME']

RT_MATCH_YEAR = True  # Match the movie by year on Rotten Tomatoes (True or False)

DRY_RUN = os.environ['DRY_RUN']  # Dry run without modifying the database (True or False)
MOVIES = os.environ['MOVIES']
TV = os.environ['TV']


def main():
    # Connect to the Plex server
    print("Connecting to the Plex server at '{base_url}'...".format(base_url=PLEX_URL))
    try:
        plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    except:
        print("No Plex server found at: {base_url}".format(base_url=PLEX_URL))
        print("Exiting script.")
        return

    # Get lists of media from the Plex server
    
    try:
        print("Retrieving a list of movies from the '{library}' library in Plex...".format(library=MOVIE_LIBRARY_NAME))
        movie_library = plex.library.section(MOVIE_LIBRARY_NAME)
    except:
        print("The '{library}' library does not exist in Plex.".format(library=MOVIE_LIBRARY_NAME))
        print("Exiting script.")
        return

    try:
        print("Retrieving a list of TV Shows from the '{library}' library in Plex...".format(library=TV_LIBRARY_NAME))
        tv_library = plex.library.section(TV_LIBRARY_NAME)
    except:
        print("The '{library}' library does not exist in Plex.".format(library=TV_LIBRARY_NAME))
        print("Exiting script.")
        return
    
    print("Using Rotten Tomatoes critic ratings.")

### MOVIES ###
    if MOVIES:
        print('\n******** MOVIES ********')
        for plex_movie in movie_library.recentlyAdded():

            if 'imdb://' in plex_movie.guid:
                imdb_id = plex_movie.guid.split('imdb://')[1].split('?')[0]
            else:
                imdb_id = None
            if not imdb_id:
                print("Missing IMDB ID. Skipping movie '{pm.title}'.".format(pm=plex_movie))
                continue
            # Get Critic rating
            try:
                rt_client_result = RottenTomatoesClient.search(term=plex_movie.title, limit=5)
            except requests.exceptions.RequestException as e:
                print(e)
                continue
            if RT_MATCH_YEAR:
                rt_movie = next((m for m in rt_client_result['movies'] if m['year'] == plex_movie.year), None)
            else:
                rt_movie = next((m for m in rt_client_result['movies']), None)

            
            if rt_movie is None:
                print("Movie not found on RottenTomatoes. Skipping movie '{pm.title} ({imdb_id})'.".format(pm=plex_movie, imdb_id=imdb_id))
                continue

            # Get Audience
            html = requests.get('https://www.rottentomatoes.com' + rt_movie['url'])

            soup = BeautifulSoup(html.content, 'html.parser')

            if soup.select('score-board.scoreboard'):
                audience_rating = soup.select('score-board.scoreboard')[0].get('audiencescore')
            else:
                audience_rating = []


            if len(audience_rating) == 2:
                rt_audience_rating = int(audience_rating) / 10.0
                popcorn = 'upright' if rt_audience_rating >= 6 else 'spilled'
            else:
                rt_audience_rating = None
                popcorn = None

            if 'meterScore' in rt_movie:
                rt_rating = rt_movie['meterScore'] / 10.0
                tomato = 'ripe' if rt_rating >= 6 else 'rotten'
            else:
                rt_rating = None
            
            print('Critic\tAudience')
            print("{rt_rating}\t{rt_audience_rating}\t{pm.title}".format(pm=plex_movie, rt_rating=rt_rating, rt_audience_rating=rt_audience_rating))
            
            if not DRY_RUN:
                data = {}
                if rt_rating is not None:
                    ### Update Critic Rating ###
                    data['rating.value'] = rt_rating
                    data['rating.locked'] = 1
                
                if rt_audience_rating is not None:
                    ### Update Audience Rating ###
                    data['audienceRating.value'] = rt_audience_rating
                    data['audienceRating.locked'] = 1
                ### Update Images ###
                
                old_image_data = db_execute("SELECT extra_data FROM metadata_items WHERE id = \'{}\'".format(plex_movie.ratingKey))
                if old_image_data:
                    if re.search(r"at%3AratingImage=.+?&",old_image_data) is not None:
                        new_image_data = re.sub(r"at%3AratingImage=.+?&", 'at%3AratingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}&'.format(tomato), old_image_data)
                    else:
                        if rt_rating is not None:
                            new_image_data = 'at%3AratingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}&'.format(tomato) + old_image_data
                    if re.search(r"at%3AaudienceRatingImage=.+?&",old_image_data) is not None:
                        new_image_data = re.sub(r"at%3AaudienceRatingImage=.+?&", 'at%3AaudienceRatingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}&'.format(popcorn), new_image_data)
                    else:
                        if rt_audience_rating is not None:
                            if rt_rating is not None:
                                new_image_data = 'at%3AaudienceRatingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}&'.format(popcorn) + new_image_data
                            else:
                                new_image_data = 'at%3AaudienceRatingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}&'.format(popcorn) + old_image_data
                else:
                    if rt_rating is None and rt_audience_rating is None:
                        new_image_data = None
                    elif rt_rating is None and rt_audience_rating is not None:
                        new_image_data = 'at%3AaudienceRatingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}'.format(popcorn)
                    elif rt_rating is not None and rt_audience_rating is None:
                        new_image_data = 'at%3AratingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}'.format(tomato)
                    else:
                        new_image_data = 'at%3AaudienceRatingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}&at%3AratingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}'.format(popcorn,tomato)
                if new_image_data is not None:
                    db_execute("UPDATE metadata_items SET extra_data = \'{}\' WHERE id = \'{}\'".format(new_image_data, plex_movie.ratingKey))

                if data:
                    plex_movie.edit(**data)

### TV SHOWS ###
    if TV:
        print('\n******** TV SHOWS ********')
        for plex_tv in tv_library.all():
            try:
                rt_client_result = RottenTomatoesClient.search(term=plex_tv.title, limit=5)
            except requests.exceptions.RequestException as e:
                print(e)
                continue
            if RT_MATCH_YEAR:
                rt_show = next((s for s in rt_client_result['tvSeries'] if s['startYear'] == plex_tv.year), None)
            else:
                rt_show = next((s for s in rt_client_result['tvSeries']), None)
            
            if rt_show is None:
                print("Show not found on RottenTomatoes. Skipping show '{pm.title}'.".format(pm=plex_tv))
                continue
            
            # Get Audience
            html = requests.get('https://www.rottentomatoes.com' + rt_show['url'])

            soup = BeautifulSoup(html.content, 'html.parser')

            audience_rating = soup.select('.mop-ratings-wrap__percentage')

            if len(audience_rating) == 2:
                rt_audience_rating = int(audience_rating[1].text.strip()[:2]) / 10.0
                popcorn = 'upright' if rt_audience_rating >= 6 else 'spilled'
            else:
                rt_audience_rating = None
                popcorn = None

            if 'meterScore' in rt_show:
                rt_rating = rt_show['meterScore'] / 10.0
                tomato = 'ripe' if rt_rating >= 6 else 'rotten'
            else:
                rt_rating = None

            print('Critic\tAudience')
            print("{rt_rating}\t{rt_audience_rating}\t{pm.title}".format(pm=plex_tv, rt_rating=rt_rating, rt_audience_rating=rt_audience_rating))

            if not DRY_RUN:
                data = {}
                if rt_rating is not None:
                    ### Update Critic Rating ###
                    data['rating.value'] = rt_rating
                    data['rating.locked'] = 1
                
                if rt_audience_rating is not None:
                    ### Update Audience Rating ###
                    data['audienceRating.value'] = rt_audience_rating
                    data['audienceRating.locked'] = 1

                ### Update Images ###
                
                old_image_data = db_execute("SELECT extra_data FROM metadata_items WHERE id = \'{}\'".format(plex_tv.ratingKey))

                if old_image_data:
                    if re.search(r"at%3AratingImage=.+?&",old_image_data) is not None:
                        new_image_data = re.sub(r"at%3AratingImage=.+?&", 'at%3AratingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}&'.format(tomato), old_image_data)
                    else:
                        if rt_rating is not None:
                            new_image_data = 'at%3AratingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}&'.format(tomato) + old_image_data
                    if re.search(r"at%3AaudienceRatingImage=.+?&",old_image_data) is not None:
                        new_image_data = re.sub(r"at%3AaudienceRatingImage=.+?&", 'at%3AaudienceRatingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}&'.format(popcorn), new_image_data)
                    else:
                        if rt_audience_rating is not None:
                            if rt_rating is not None:
                                new_image_data = 'at%3AaudienceRatingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}&'.format(popcorn) + new_image_data
                            else:
                                new_image_data = 'at%3AaudienceRatingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}&'.format(popcorn) + old_image_data
                else:
                    if rt_rating is None and rt_audience_rating is None:
                        new_image_data = None
                    elif rt_rating is None and rt_audience_rating is not None:
                        new_image_data = 'at%3AaudienceRatingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}'.format(popcorn)
                    elif rt_rating is not None and rt_audience_rating is None:
                        new_image_data = 'at%3AratingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}'.format(tomato)
                    else:
                        new_image_data = 'at%3AaudienceRatingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}&at%3AratingImage=rottentomatoes%3A%2F%2Fimage%2Erating%2E{}'.format(popcorn,tomato)
                if new_image_data is not None:
                    db_execute("UPDATE metadata_items SET extra_data = \'{}\' WHERE id = \'{}\'".format(new_image_data, plex_tv.ratingKey))

                if data:
                    plex_tv.edit(**data)

    
def db_execute(query):
    try:
        result = subprocess.check_output([PLEX_DB_LOCATION , '--sqlite', PLEX_DB_LOCATION + PLEX_DB_NAME, '{}'.format(query)])
    except Exception as e:
        print("Operational Error: {}".format(e))

    return str(result.decode("utf-8"))
            
if __name__ == "__main__":
    main()
    print("Done.")