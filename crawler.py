from collections import defaultdict
import urllib.request
import os
import os.path
import json
import re
import csv
#import pymongo

import settings

class FFOpener(urllib.request.FancyURLopener):
    version = 'Firefox'    


class NBAStatCrawler(object):

    def __init__(self):
        self.firefox = FFOpener()
        self.season_dir = settings.SEASON_DIR
        self.game_dir = settings.GAME_DIR
        self.playerSet = defaultdict(set)
        self.playerPos = {}
        self.playerList = []

    def start(self):
        data = [
            *self.getSeasonData('2016-17'),
            # *self.getSeasonData('2015-16')
        ]
        self.setPlayerPos()
        self.toCSV(data)
        #print(self.playerPos)


    # db not available now
    #@property
    #def db(self):
    #    if not self.db:
    #        client = pymongo.MongoClient(settings.MONGO_URI)
    #        self.db = client[settings.MONGO_DB]
    #    return self.db
    #
    ## db not available now
    #def insertGameToDatabase(self, data):
    #    collection = settings.MONGO_COLLECTION_GAME
    #    self.db[collection].insert(data)
    
    def download(self, _dir, filename, url):
        try: 
            res = self.firefox.open(fullurl=url)
            if not os.path.exists(_dir):
                os.mkdir(_dir)
            
            with open(_dir+'/'+filename, 'w') as out:
                out.write(res.read().decode('utf-8'))
        
        except urllib.error.HTTPError as e:
            print(e.reason)

    def loadJson(self, filepath):
        with open(filepath,'r') as f:
            data = json.load(f)
            return data

        return None

    def downloadLog(self, what, _id):
        print ('download '+ what + ': ' + _id)

    def downloadSeasonData(self, seasonID):
        get_para = settings.GAMELOG_SOURCE['para']
        get_para['Season'] = seasonID # ex. 2015-16
        gamelogUrl = (settings.GAMELOG_SOURCE['url'] + 
            '?' + urllib.parse.urlencode(get_para)
        )
        
        self.download(self.season_dir, seasonID, gamelogUrl)
        self.downloadLog('season data', seasonID)

    def downloadGameData(self, gameID): 
        get_para = settings.BOXSCORE_SOURCE['para']
        get_para['GameID'] = gameID # ex. 0021600079 
        boxscoreUrl = (settings.BOXSCORE_SOURCE['url'] + 
            '?' + urllib.parse.urlencode(get_para)
        )
        
        self.download(self.game_dir, gameID, boxscoreUrl)
        self.downloadLog('game data', gameID)

    def getSeasonData(self, seasonID):
        seasonfile = self.season_dir+'/'+seasonID
        
        if not os.path.exists(seasonfile):
            self.downloadSeasonData(seasonID)

        seasonData = self.loadJson(seasonfile)

        header = seasonData['resultSets'][0]['headers']
        rowSet = seasonData['resultSets'][0]['rowSet']
        data = []
        for row in rowSet:
            gameDict = dict(zip(header, row))
            gameDict['GAME_DETAIL'] = self.getGameData(gameDict['GAME_ID'])
            data.append(gameDict)
        return data
    
    def getGameData(self, gameID):
        gamefile = self.game_dir+'/'+gameID

        if not os.path.exists(gamefile):
            self.downloadGameData(gameID)

        gameData = self.loadJson(gamefile)
        
        playersRawData = gameData['resultSets'][0]
        playerHeader = playersRawData['headers']
        players = playersRawData['rowSet']

        teamsRawData = gameData['resultSets'][1]
        teamHeader = teamsRawData['headers']
        teams = teamsRawData['rowSet']
        teams[0] = dict(zip(teamHeader, teams[0]))
        teams[1] = dict(zip(teamHeader, teams[1]))

        playerList = []        

        for player in players:
            playerDict = dict(zip(playerHeader,player))
            playerList.append(playerDict)
           
            self.setPlayer(playerDict['TEAM_ABBREVIATION'],playerDict['PLAYER_NAME'])
        
        host, guest = teams
        if playerList[0]['TEAM_ABBREVIATION'] == teams[0]['TEAM_ABBREVIATION']:
            host, guest = guest, host
        
        gameDetail = {'PLAYER_STATS':playerList, 'HOST':host, 'GUEST':guest}
        return gameDetail
        
    def setPlayer(self, team, playerName):
        self.playerSet[team].add(playerName)

    def setPlayerPos(self): # positions of csv field
        idx = 0
        self.playerPos = {}
        self.playerList = []
        for team in self.playerSet:
            for name in self.playerSet[team]:
                self.playerPos[name] = idx
                self.playerList.append(name)
                idx += 1

    def toCSV(self, gamedata):
        with open('nba_stats.csv', 'w', newline='') as csvfile:
            cw = csv.writer(csvfile, delimiter=',',
                            quotechar='|',quoting=csv.QUOTE_MINIMAL)
            header_overall = [
                '對手','主場','賽季','主場分數','客場分數','勝負'
            ]
            header_player = [
                '', '先發', '主場', 
                '位置', '背靠背', '時間',
                '投籃', '命中', '出手',
                '三分', '三分命中', '三分出手',
                '罰球', '罰球命中', '罰球出手',
                '籃板', '前場', '後場', '助攻',
                '搶斷', '蓋帽', '失誤', '犯規',
                '得分'
            ]
            header = [
                *header_overall,
                # *[field + str(i) if field != '球員' else loc + field + str(i) 
                #  for field in header_player
                #  ]
                *[name + ' ' + field 
                  for name in self.playerList
                  for field in header_player]
            ]
            cw.writerow(header)
            
            for game in gamedata:

                # Find Opponent
                m = re.match(r'.*\s(.+)', game['MATCHUP'])
                oppo = m.group(1)

                host = game['GAME_DETAIL']['HOST']
                guest = game['GAME_DETAIL']['GUEST']

                if oppo == host['TEAM_ABBREVIATION']: continue

                wl = '1' if game['WL'] == 'W' else '0'
                row = [
                #    game['TEAM_NAME'],
                    oppo,
                    host['TEAM_ABBREVIATION'],
                    game['GAME_DATE'],
                    host['PTS'],
                    guest['PTS'],
                    wl
                ]
            
                # TODO: handle player's data
                player_field_start = len(row)
                player_field_len = len(header_player)
                players = game['GAME_DETAIL']['PLAYER_STATS']

                row.extend(['0'] * player_field_len * len(self.playerList))
                for player in players:
                    playerRow = self.toCSVPlayerRow(player, game)
                    if playerRow:
                        idx = self.playerPos[player['PLAYER_NAME']]
                        start_idx = player_field_start + (idx * player_field_len)
                        row[start_idx : start_idx + player_field_len] = playerRow
                cw.writerow(row)
            
    def toCSVPlayerRow(self, player, game):
        # '', '先發', '主場', 
        # '位置', '背靠背', '時間'
        # '投籃', '命中', '出手',
        # '三分', '三分命中', '三分出手',
        # '罰球', '罰球命中', '罰球出手',
        # '籃板', '前場', '後場', '助攻',
        # '搶斷', '蓋帽', '失誤', '犯規',
        # '得分'


        host = game['GAME_DETAIL']['HOST']
        guest = game['GAME_DETAIL']['GUEST']
        inGame = player['TEAM_ID'] in [host['TEAM_ID'], guest['TEAM_ID']]
        if not inGame: return []

        isHost = '1' if player['TEAM_ID'] == host['TEAM_ID'] else '0'
        backToBack = '1' # TODO: no idea yet
        isStart = '1' if bool(player['START_POSITION']) else '0'
        position = player['START_POSITION'] if player['START_POSITION'] else '0'
        
        mins = '0'
        if player['MIN']:
            colon = player['MIN'].find(':')
            mins = "%.2f" % (int(player['MIN'][:colon]) + float(player['MIN'][colon+1:])/60)
        
        return [
            "1", isStart, isHost,
            position, backToBack, mins,
            player['FG_PCT'], player['FGM'], player['FGA'],
            player['FG3_PCT'], player['FG3M'], player['FG3A'],
            player['FT_PCT'], player['FTM'], player['FTA'],
            player['REB'], player['OREB'], player['DREB'], player['AST'],
            player['STL'], player['BLK'], player['TO'], player['PF'],
            player['PTS'],
        ] 

if __name__ == "__main__":
    crawler = NBAStatCrawler()
    crawler.start()


#data = [
#{
#    'SEASON_ID': ...
#    'TEAM_ID': ...
#    ...
#    'GAME_DETAIL': { 
#        'PLAYER_STATS': [
#        {
#            'PLAYER_ID': ...
#            'PLAYER_NAME': ...
#            'START_POSITION': ...
#            ...
#        }...],
#        'HOST': 
#        {
#            'TEAM_ID': ...
#            'TEAM_NAME': ...
#            ...
#        },
#        'GUEST': 
#        {
#            'TEAM_ID': ...
#            'TEAM_NAME': ...
#            ...
#        },
#    }
#}
#...]
    

