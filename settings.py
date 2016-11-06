
GAME_DIR = 'games'
SEASON_DIR = 'seasons'


MONGO_URI = 'localhost'
MONGO_DB = 'nba_stats'
MONGO_COLLECTION_GAME = 'games'
MONGO_COLLECTION_SEASON = 'seasons'

GAMELOG_SOURCE= {
    'url': "http://stats.nba.com/stats/leaguegamelog",
    'para': {
        'Direction': 'DESC',
        'LeagueID': '00',
        'PlayerOrTeam': 'T',
        'Season': '2015-16',
        'SeasonType': 'Regular Season',
        'Sorter': 'DATE'
    }
}


BOXSCORE_SOURCE = {
    'url': "http://stats.nba.com/stats/boxscoretraditionalv2",
    'para': {
        'EndPeriod': 10,
        'EndRange': 28800,
        'GameID': '0021501182',
        'RangeType': 0,
        'Season': '2015-16',
        'SeasonType': 'Regular Season',
        'StartPeriod': 1,
        'StartRange': 0
    }
}
