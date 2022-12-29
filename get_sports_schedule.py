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

##  convert event data to presentable strings
def convert_events_to_strings(events, args):
    new_data = []

    for sport_group in events: ## iterate over each sport grouping
        for event in sport_group: ## iterate over each entry
            if args.verbose:
                print('convert:')
                print(event)

            gametime = datetime.datetime.strptime(event['commence_time'], '%Y-%m-%dT%H:%M:%SZ')
            gametime += datetime.timedelta(hours = args.utc_offset)
            date = gametime.strftime("%a %b %d")
            time = gametime.strftime("%H:%M")

            #line = event['commence_time'].split('T')[0] + ' ' + event['commence_time'].split('T')[1] + '\t'
            line = date + ' ' + time + '\t'
            line += event['sport_title'] + '\t'
            if event['location'] == 'home':
                line += event['home_team'].split(' ')[-1] + ' vs ' + event['away_team'].split(' ')[-1]
            elif event['location'] == 'away':
                line += event['away_team'].split(' ')[-1] + ' at ' + event['home_team'].split(' ')[-1]
            else:
                line += event['home_team'].split(' ')[-1] + ' XX ' + event['away_team'].split(' ')[-1]
        
            if event['scores'] != None:
                scores = event['scores']
                for i in (0,1):
                    if event['scores'][i]['name'] == event['team']:
                        first_score = event['scores'][i]['score']
                    else:
                        second_score = event['scores'][i]['score']

                line += '\t' + first_score + ':' + second_score
            else:
                line += '\t' + 'TDB'
            line += '\n'
            if args.verbose:
                print('in convert function: ' + line)
            new_data.append(line)

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
            print('request:')
            print(each)

    return(team_events)

##  convert event data to presentable strings
def write_events_to_file(events, output_file, args):
    if args.verbose:
        print('Writing to ' + output_file)

    f = open(output_file, 'w')
    f.write('Recent and Upcoming Games\n')
    max_len = 0
    for each in events:
        if len(each) > max_len:
            max_len = len(each)
    f.write('=' * max_len + '\n') ## not working currently :/
    for each in events:
        f.write(each)
    f.close()

##  part where all the things happen
def main():
    api_host = "https://api.the-odds-api.com/v4/sports/"
    api_key = ""

    parser = argparse.ArgumentParser(
            prog = "Sports Schedules",
            description = "Get sport things",
            epilog = "some epilog text")
    parser.add_argument("-f", "--filename", type=str, default="teams.txt")
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
    
    data = convert_events_to_strings(events, args)
    write_events_to_file(data, args.output, args)

    if args.verbose:
        for each in data:
            print('in main: ' + each)

    return 0

if __name__ == "__main__":
    main()
