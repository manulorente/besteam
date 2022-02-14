
from distutils.log import error
import os
import random
import datetime
import logging
import numpy as np
import sqlite3 as sql
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for

# APP SECTION
app = Flask(__name__)
app.debug = False

# DATABASE SECTION
DB_FILE = 'db\\besteam_database.db'

# LOGGER SECTION
logging.basicConfig(
    filename = 'log\\debug.log',
    filemode = "a",
    level = logging.INFO,
    format = "[%(asctime)s] %(levelname)-8s %(funcName)-20s %(message)s",
    datefmt = "%m/%d/%Y %H:%M:%S",
)

def create_connection(db_file = DB_FILE):
    conn = None
    try:
        conn = sql.connect(db_file)
        sql_create_teams_table = """CREATE TABLE IF NOT EXISTS teams (
                                            id INTEGER PRIMARY KEY,
                                            name TEXT NOT NULL,
                                            created_by TEXT NOT NULL,
                                            modified_by TEXT NOT NULL
                                            );"""
        sql_create_players_table = """CREATE TABLE IF NOT EXISTS players (
                                            id INTEGER PRIMARY KEY,
                                            team_id INTEGER NOT NULL,
                                            name TEXT NOT NULL,
                                            rating FLOAT NOT NULL,
                                            votes INTEGER NOT NULL,
                                            voted TEXT,
                                            FOREIGN KEY(team_id) REFERENCES teams(id)
                                            );"""                                            
        create_table(conn, sql_create_teams_table)   
        create_table(conn, sql_create_players_table)                                                                                             
    except sql.Error as e:
        logging.error(e)
    finally:
        if conn:
            conn.close()

def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except sql.Error as e:
        print(e)    

def create_team(conn, team):
    now = datetime.datetime.utcnow()
    now.strftime('%m/%d/%Y %H:%M:%S')
    cur = conn.cursor()
    cur.execute("INSERT INTO teams(name, created_by, modified_by) VALUES(?, ?, ?);", 
                (team, now, now))
    conn.commit()
    return cur.lastrowid

def read_db(team_name = ""):
    conn = None
    team = []
    try:
        conn = sql.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT * FROM teams WHERE name = ?;", (team_name, ))  
        team_id = cur.fetchone()[0]
        if team_id != None:
            cur.execute("SELECT * FROM players WHERE team_id = ?;", (team_id, )) 
            team = cur.fetchall()
    except sql.Error as e:
        logging.error(e)
    finally:
        if conn: conn.close() 
    return team

def add_player(team_name = "", player = ""):
    error = 0
    if player != "" or player.isalnum() == False: 
        conn = None
        try:
            conn = sql.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("SELECT * FROM teams WHERE name = ?;", (team_name, )) 
            team_id = cur.fetchone()[0]
            if team_id != None:
                cur.execute("SELECT * FROM players WHERE team_id = ?;", (team_id, ))
                rows = cur.fetchall() 
                # Check if player already exist on database
                if any(player in row for row in rows):
                    error = 1
                else:
                    now = datetime.datetime.utcnow()
                    now.strftime('%m/%d/%Y %H:%M:%S')                    
                    cur.execute("INSERT INTO players(team_id, name, rating, votes) VALUES(?,?,?,?);", 
                                (team_id, player, 0.0, 0))
                    cur.execute("UPDATE teams SET modified_by = ? WHERE id = ?;", (now, team_id))
                    conn.commit()
        except sql.Error as e:
            logging.error(e)
        finally:        
            if conn:
                conn.close() 
    else:
        error = 2
    return error

def db2dict(players = {}):
    team = {}
    for player in players:
        _, _, name, rating, votes, *voted = player
        team[name] = {'rating': float(rating), 'votes': int(votes), 'voted': list(voted)}
    return team

def write_db(team_name = "", besteam = ""):
    save_path = os.path.join("db", str(team_name).upper() + ".dat")
    f1 = open(save_path, "w")
    for player in besteam:
        f1.write(player+","+str(besteam[player]['rating'])) 
        f1.write(","+str(besteam[player]['votes']))
        if besteam[player]['voted'] != []: 
            f1.write(',')
            print(*besteam[player]['voted'], sep = ",", file = f1)
        else:
            f1.write('\n')
    f1.close()    
    return True

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')    

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/how', methods=['GET', 'POST'])
def how():
    if request.method == 'GET':
        return render_template('how.html')   
    else:
        return redirect(url_for('index')) 

@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'GET':
        return render_template('create.html', ERROR = 0)
    else:
        # Create team in the database if doesn't exist
        team_name = str(request.form['team']).upper()
        conn = None
        try:
            if team_name.isalnum() == False or len(team_name) < 5:
                return render_template('create.html', ERROR = 2)
            else:
                conn = sql.connect(DB_FILE)
                cur = conn.cursor()
                cur.execute("SELECT * FROM teams WHERE name = ?", (team_name, ))  
        except sql.Error as e:
            logging.error(e)
        finally:
            if conn:
                if cur.fetchone() != None:
                    conn.close() 
                    return render_template('create.html', ERROR = 1)
                else:
                    create_team(conn, team_name)   
                    conn.close() 
                    return redirect(url_for('access', team_name= team_name))


@app.route('/team/<team_name>', methods=['GET', 'POST'])
def access(team_name = ""):
    if request.method == 'GET':
        besteam = db2dict(read_db(team_name))
        players = [player.split(',')[0] for player in besteam]
        return render_template('access.html', TEAM_NAME = team_name, TEAM = players)
    else:
        user = str((request.form['user'])).upper()
        if user == "":
            render_template('add.html', TEAM_NAME = team_name, ERROR =  0) 
            return redirect(url_for('add', team_name = team_name))
        else:
            return redirect(url_for('view', team_name = team_name, user = user))

@app.route('/join', methods=['GET', 'POST'])
def join():
    if request.method == 'GET':
        return render_template('join.html', ERROR = 0) 
    else:
        error = 0
        conn = None
        team_name = str(request.form['team']).upper()
        try:
            conn = sql.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("SELECT * FROM teams WHERE name = ?", (team_name, )) 
            if cur.fetchone() == None: error = 1
        except sql.Error as e:
            logging.error(e)
        finally:
            if conn: conn.close() 
            if error:
                return render_template('join.html', ERROR = error)
            else:
                return redirect(url_for('access', team_name = team_name))

@app.route('/team/<team_name>/view', methods=['GET'])
def view(team_name = ""):
    user = str(request.args.get('user')).upper()
    team = [player for player in db2dict(read_db(team_name))]
    return render_template('team.html', TEAM_NAME = team_name, TEAM = team, USER = user)

@app.route('/team/<team_name>/add', methods=['GET', 'POST'])
def add(team_name = ""):
    if request.method == 'GET':
        return render_template('add.html', TEAM_NAME = team_name, ERROR =  0) 
    else:
        player = str(request.form['new_player']).upper()     
        error = add_player(team_name, player)
        if error == 0: 
            return redirect(url_for('view', team_name = team_name, user =  player))
        else:
            return render_template('add.html', TEAM_NAME = team_name, ERROR =  error) 

# @app.route('/vote/<team_name>/<user>', methods = ['GET', 'POST'])
# def vote(team_name = "", user = ""):
#     # Get and create dictionary
#     besteam = db2dict(read_db(team_name))
#     if request.method == 'GET':
#         # Populate not voted people
#         team = []
#         for player in besteam:
#             if player != user and not player in besteam[user]['voted']:
#                 team.append(player)
#         if team == []:
#             return render_template('team.html', TEAM_NAME = team_name, TEAM = besteam, USER = user, VOTED = 1)
#         else:
#             return render_template('vote.html', TEAM_NAME = team_name, USER = user, TEAM =  team) 
#     else:
#         # Vote all team members 
#         for player in besteam:
#             if player != user and not player in besteam[user]['voted']:
#                 besteam[player]['votes'] += 1
#                 besteam[player]['rating'] += float(request.form[player])
#                 besteam[user]['voted'].append(player) 
#         # Overwrite data into DB
#         write_db(team_name, besteam)   
#         return render_template('team.html', TEAM_NAME = team_name, TEAM = besteam, USER = user, VOTED = 0)

@app.route('/vote/<team_name>/<user>', methods = ['GET', 'POST'])
def vote(team_name = "", user = ""):
    if request.method == 'GET':
        conn = None
        try:
            conn = sql.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("SELECT * FROM teams WHERE name = ?;", (team_name, )) 
            team_id = cur.fetchone()[0]
            if team_id != None:
                cur.execute("SELECT name, voted FROM players WHERE team_id = ?;", (team_id,))
                rows = cur.fetchall() 
        except sql.Error as e:
            logging.error(e)
        finally:        
            if conn: conn.close() 
            team = [player for player in db2dict(read_db(team_name))]
            # Populate not voted people
            if any(user in row[1] for row in rows if row[1] != None):
                return render_template('team.html', TEAM_NAME = team_name, TEAM = team, USER = user, VOTED = 1)
            else:
                return render_template('vote.html', TEAM_NAME = team_name, USER = user, TEAM =  team)
    else:
        # Vote all team members 
        for player in besteam:
            if player != user and not player in besteam[user]['voted']:
                besteam[player]['votes'] += 1
                besteam[player]['rating'] += float(request.form[player])
                besteam[user]['voted'].append(player) 
        # Overwrite data into DB
        write_db(team_name, besteam)   
        return render_template('team.html', TEAM_NAME = team_name, TEAM = besteam, USER = user, VOTED = 0)
 

@app.route('/match/<team_name>/<user>', methods = ['GET', 'POST'])
def match(team_name = "", user = ""):
    # Get and create dictionary
    besteam = db2dict(read_db(team_name))    
    if request.method == 'GET':
        return render_template('match.html', TEAM_NAME = team_name, USER = user, TEAM =  besteam) 
    else:
        team = [player for player in besteam if player in request.form.keys()]
        # Check if number of players is even
        nplayers = len(team)
        if nplayers % 2:
            return render_template('match.html', TEAM_NAME = team_name, USER = user, TEAM =  besteam, ERROR = 1) 
        else:
            # Repeat the algorithm N times times to increase accuracy
            n = 10
            repeat = True
            nit = 0
            besteam_a_avg = 0
            besteam_b_avg = 0
            while repeat:
                nit +=1
                # Get random order
                index = random.sample(range(0, nplayers), nplayers)
                # Populate teams
                team_a = []  
                team_b = [] 
                team_a_avg = [] 
                team_b_avg = []  
                for i in index:
                    player_rating = besteam[list(besteam)[i]]['rating']/besteam[list(besteam)[i]]['votes']
                    if (np.mean(team_a_avg) < np.mean(team_b_avg) and len(team_a) < int(nplayers/2)) or team_a_avg == []:
                        team_a.append(list(besteam)[i])
                        team_a_avg.append(player_rating)
                    elif len(team_b) < int(nplayers/2):
                        team_b.append(list(besteam)[i])
                        team_b_avg.append(np.around(player_rating)) 
                    else:
                        team_a.append(list(besteam)[i])
                        team_a_avg.append(player_rating)  
                if abs(np.mean(team_a_avg) - np.mean(team_b_avg)) <= abs(besteam_a_avg - besteam_b_avg) or nit == 1:
                    besteam_a = zip(team_a, np.around(team_a_avg, decimals = 1))  
                    besteam_b = zip(team_b, np.around(team_b_avg, decimals = 1))  
                    besteam_a_avg = np.around(np.mean(team_a_avg), decimals = 1)
                    besteam_b_avg = np.around(np.mean(team_b_avg), decimals = 1)
                if nit == n: repeat = False
            return render_template('match.html', TEAM_NAME = team_name, USER = user, TEAM =  besteam, TEAM_A = besteam_a, TEAM_A_AVG = besteam_a_avg, TEAM_B = besteam_b, TEAM_B_AVG = besteam_b_avg) 


if __name__ == "__main__":
    create_connection()
    app.run()
