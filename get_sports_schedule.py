#!/usr/bin/python3

##  Intent is to read in a list of teams from known leagues and
##  make requests to a service to get their recent scores and schedules
##  then write that to a text file that can be displayed elsewhere

import os
import re
import json
import pytz
import datetime
import argparse
import requests

##  set up some functions before getting to the heart of the script

##  read teams from config/text file, return array of team names/leagues
def read_teams_list(filename):
    teams = []
    f = open(filename, 'r')
    for line in f.readlines():
        if line[0] != "#":
            league, team, active = line.rstrip('\n').split('\t')
            if active == "true":
                teams.append(league + '\t' + team)
    f.close()
    return teams

##  convert event data to comma separated list of strings I want to display
def convert_events(events, args):
    new_data = []

    for sport_group in events: ## iterate over each sport grouping
        for event in sport_group: ## iterate over each entry
            if args.verbose:
                print('convert:')
                print(event)

            ## check for 'no games found' in the line, don't need to do anything fancy for that
            if "No games found" not in event:
                gametime = datetime.datetime.strptime(event['commence_time'], '%Y-%m-%dT%H:%M:%SZ')
                gametime += datetime.timedelta(hours = args.utc_offset)
                date = gametime.strftime("%a %b %d")
                time = gametime.strftime("%H:%M")

                #line = event['commence_time'].split('T')[0] + ' ' + event['commence_time'].split('T')[1] + '\t'
                ## this will break downstream if there are any team names with commas in them...
                line = date + ' ' + time + '|'
                line += event['sport_title'] + '|'
                if event['location'] == 'home':
                    line += event['home_team'].split(' ')[-1] + ' vs ' + event['away_team'].split(' ')[-1]
                elif event['location'] == 'away':
                    line += event['away_team'].split(' ')[-1] + ' at ' + event['home_team'].split(' ')[-1]
                else:
                    line += event['home_team'].split(' ')[-1] + ' XX ' + event['away_team'].split(' ')[-1]
                line += '|'
        
                if event['scores'] != None:
                    scores = event['scores']
                    for i in (0,1):
                        if event['scores'][i]['name'] == event['team']:
                            first_score = event['scores'][i]['score']
                        else:
                            second_score = event['scores'][i]['score']

                    line += first_score + ':' + second_score
                else:
                    line += 'TDB'
                #line += '\n'
                if args.verbose:
                    print('in convert function: ' + line)
                new_data.append(line)
            else:
                new_data.append(event)

        new_data.append('\n')

    return new_data

##  request recent and upcoming games for a specific sport, filter for team and return those results
def request_team_data(host, key, league, team, args):
    team_events = []
    url = host + league + "/scores?daysFrom=3&apiKey=" + key
    response = requests.request("GET", url)
    resp = response.json()

    for i in range(0,len(resp)):
        entry = resp[i]
        if entry['home_team'] == team:
            entry['team'] = team
            entry['location'] = 'home'
            team_events.append(entry)
        if entry['away_team'] == team:
            entry['team'] = team
            entry['location'] = 'away'
            team_events.append(entry)

    if len(team_events) == 0:
        team_events.append(team + ': No games found')
        if args.verbose:
            print('request: ' + team + ': No games found')
    else:
        for each in team_events:
            if args.verbose:
                print('request:')
                print(each)

    return(team_events)

##  convert event data to presentable strings
def write_events_to_file(events, args):
    if args.verbose:    print('Writing to ' + args.output)

    f = open(args.output, 'w')
    f.write('Recent and Upcoming Games (as of ' + datetime.datetime.today().strftime("%Y-%m-%d") + ')\n')
    ## could loop through each 'matchup' string to find the longest and format the prints for that
    ## but we dont care that much about them, just estimate it and printf the thing
    f.write('=' * 56)
    f.write('\n')
    for each in events:
        if args.verbose:
            print(events)
            print(each)
        if "No games found" not in each:
            if len(each) > 5:
                dt, ty, byline, score = each.split('|')
                line = "{date:13s} {league:5s} {byline:25s} {score:7s}\n"
                f.write(line.format(date = str(dt), league = str(ty), byline = str(byline), score = str(score)))
            else:
                if args.verbose: print('newline found')
                f.write('\n')
        else:
            f.write(each)

    f.close()

##  part where all the things happen
def main():
    ##  Should probably pull this out into an env variable and pass it in to the cron command
    api_host = "https://api.the-odds-api.com/v4/sports/"
    api_key = "d7bbd27e377d86ead653d433a2b57990"

    parser = argparse.ArgumentParser(
            prog = "Sports Schedules",
            description = "Get sport things",
            epilog = "some epilog text")
    parser.add_argument("-f", "--filename", type=str, default="./teams.txt")
    parser.add_argument("-o", "--output", type=str, default="./SportsTeamsSchedule.txt")
    parser.add_argument("-b", "--betting-odds", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-u", "--utc_offset", type=int, default=-6)

    args = parser.parse_args()
    
    if os.path.exists(args.filename):
        try:
            teams = read_teams_list(args.filename)
        except Exception as e:
            print('Error reading teams file, check script for parsing errors')
            print(e)
            return(-1)
    else:
        print('Error reading teams file, check filename')
        return(-1)
    
    events = []
    for team in teams:
        team_events = []
        league, team_name = team.split('\t')
        try:
            team_events = request_team_data(api_host, api_key, league, team_name, args)
            events.append(team_events)
            if args.verbose: print('main: appended ' + str(len(team_events)) + ' events')
        except Exception as e:
            print('Failed to load events for ' + team_name + ' for some reason')
            print(e)
            events.append('Errored on ' + team_name)
        events.append('')

    if args.verbose: print('loading ' + str(len(events)) + ' events complete apparently')
    
    data = convert_events(events, args)
    write_events_to_file(data, args)

    if args.verbose:
        for each in data:
            if len(each) > 5:
                print(datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'), 'in main: ' + each)

    return 0

if __name__ == "__main__":
    main()
