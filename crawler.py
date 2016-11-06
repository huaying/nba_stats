from collections import defaultdict
import urllib.request
import os
import os.path
import json
import re
import csv
import pymongo

import settings

class FFOpener(urllib.request.FancyURLopener):
    version = 'Firefox'    


class NBAStatCrawler(object):

    def __init__(self):
        self.firefox = FFOpener()
        self.season_dir = settings.SEASON_DIR
        self.game_dir = settings.GAME_DIR
        self.playerSet = defaultdict(set)

    def start(self):
        data = [
            *self.getSeasonData('2016-17'),
            *self.getSeasonData('2015-16')
        ]
        self.toCSV(data)


    # db not available now
    @property
    def db(self):
        if not self.db:
            client = pymongo.MongoClient(settings.MONGO_URI)
            self.db = client[settings.MONGO_DB]
        return self.db
    
    # db not available now
    def insertGameToDatabase(self, data):
        collection = settings.MONGO_COLLECTION_GAME
        self.db[collection].insert(data)
    
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

        #row1 = seasonData['resultSets'][0]['rowSet'][60]
        #game1 = dict(zip(header,row1))
        #game1['GAME'] = self.getGameData(game1['GAME_ID'])
        #print(json.dumps(game1, indent=2))
    
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
        
        playerList = []
        teamList = []
        gameDetail = {'PLAYER_STATS':playerList, 'TEAM_STATS':teamList}

        for player in players:
            playerDict = dict(zip(playerHeader,player))
            playerList.append(playerDict)
           
            self.setPlayer(playerDict['TEAM_ABBREVIATION'],playerDict['PLAYER_NAME'])
            
        for team in teams:
            teamDict = dict(zip(teamHeader, team))
            teamList.append(teamDict)
        
        return gameDetail
        
    def setPlayer(self, team, playerName):
        self.playerSet['team'].add(playerName)

    def toCSV(self, gamedata):
        with open('nba_stats.csv', 'w', newline='') as csvfile:
            cw = csv.writer(csvfile, delimiter=',',
                            quotechar='|',quoting=csv.QUOTE_MINIMAL)
            header_overall = [
                '球隊','對手','主場','賽季','主場分數','客場分數','勝負'
            ]
            header_player = [
                '球員','時間','投籃','命中',
                '三分','三分命中','三分出手',
                '罰球','罰球命中','罰球出手',
                '籃板','前場','後場','助攻',
                '搶斷','蓋帽','失誤','犯規',
                '得分','先發','位置',
            ]
            header = [
                *header_overall,
                *[field + str(i) if field != '球員' else loc + field + str(i) 
                 for loc in ['主場','客場']
                 for i in range(1,21) 
                 for field in header_player
                 ]
            ]
            cw.writerow(header)
            
            for game in gamedata:

                # Find Opponent
                m = re.match(r'.*\s(.+)', game['MATCHUP'])
                oppo = m.group(1)

                host = game['GAME_DETAIL']['TEAM_STATS'][1]
                guest = game['GAME_DETAIL']['TEAM_STATS'][0]

                row = [
                    game['TEAM_NAME'],
                    oppo,
                    host['TEAM_ABBREVIATION'],
                    game['GAME_DATE'],
                    host['PTS'],
                    guest['PTS'],
                    game['WL']
                ]
            
                # TODO: handle player's data
            
                cw.writerow(row)

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
#        # First Team is Guest
#        'TEAM_STATS': [
#        {
#            'TEAM_ID': ...
#            'TEAM_NAME': ...
#            ...
#        }...]
#    }
#}
#...]
    

