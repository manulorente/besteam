
import random
import datetime
import logging
import numpy as np
import sqlite3 as sql
from flask import Flask, render_template, request, redirect, url_for

# APP SECTION
app = Flask(__name__)
app.debug = False

# DATABASE SECTION
DB_FILE = 'besteam_database.db'

# LOGGER SECTION
logging.basicConfig(
    filename = 'debug.log',
    filemode = "w+",
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
        conn.execute(sql_create_teams_table)   
        conn.execute(sql_create_players_table)                                                                                             
    except sql.Error as e:
        logging.error(e)
    finally:
        if conn:
            conn.close()

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
        id, _, name, rating, votes, voted = player
        if voted ==  None: 
            team[name] = {'id': int(id), 'rating': float(rating), 'votes': int(votes), 'voted': []}
        else:
            team[name] = {'id': int(id), 'rating': float(rating), 'votes': int(votes), 'voted': voted.split(',')}
    return team

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
                    now = datetime.datetime.utcnow()
                    now.strftime('%m/%d/%Y %H:%M:%S')
                    cur = conn.cursor()
                    cur.execute("INSERT INTO teams(name, created_by, modified_by) VALUES(?, ?, ?);", 
                                (team_name, now, now))
                    conn.commit() 
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

@app.route('/vote/<team_name>/<user>', methods = ['GET', 'POST'])
def vote(team_name = "", user = ""):
    conn = None
    try:
        conn = sql.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT * FROM teams WHERE name = ?;", (team_name, )) 
        team_id = cur.fetchone()[0]
        if team_id != None:
            cur.execute("SELECT * FROM players WHERE team_id = ?;", (team_id,))
            rows = cur.fetchall() 
    except sql.Error as e:
        logging.error(e)
    finally:
        team = db2dict(rows)        
        if request.method == 'GET':
            # Check if user already voted and populate not voted people
            no_voted = [player in team[user]['voted'] for player in team if team[user]['voted'] != [] and player != user]
            if conn: conn.close() 
            if no_voted == []:
                return render_template('team.html', TEAM_NAME = team_name, TEAM = team, USER = user, VOTED = 1)
            elif no_voted != [] and all(no_voted):
                return render_template('team.html', TEAM_NAME = team_name, TEAM = team, USER = user, VOTED = 2)
            else:
                team = [player for player in team if not player in team[user]['voted'] and player != user]
                return render_template('vote.html', TEAM_NAME = team_name, USER = user, TEAM =  team)
        else:
            # Vote all team members and store data into de database
            for player in team:
                if player != user and not player in team[user]['voted']:
                    team[player]['votes'] += 1
                    team[player]['rating'] += float(request.form[player])
                    team[user]['voted'].append(player) 
                    cur.execute("UPDATE players SET votes=?, rating=? WHERE id=?;", 
                    (team[player]['votes'], team[player]['rating'], team[player]['id'],))
            cur.execute("UPDATE players SET voted=? WHERE id=?;", (','.join(team[user]['voted']), team[user]['id'],))
            if conn:
                conn.commit()
                conn.close() 
            return render_template('team.html', TEAM_NAME = team_name, TEAM = team, USER = user, VOTED = 0)
 

@app.route('/match/<team_name>/<user>', methods = ['GET', 'POST'])
def match(team_name = "", user = ""):
    # Get and create dictionary
    players = db2dict(read_db(team_name))    
    if request.method == 'GET':
        return render_template('match.html', TEAM_NAME = team_name, USER = user, TEAM =  players) 
    else:
        squad = [player for player in players if player in request.form.keys()]
        # Check if number of players is even
        nplayers = len(squad)
        if nplayers % 2:
            return render_template('match.html', TEAM_NAME = team_name, USER = user, TEAM =  players, ERROR = 1) 
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
                    player_rating = players[list(squad)[i]]['rating']/players[list(squad)[i]]['votes']
                    if team_a_avg == []:
                        team_a.append(list(squad)[i])
                        team_a_avg.append(player_rating)
                    elif team_b_avg == []:
                        team_b.append(list(squad)[i])
                        team_b_avg.append(player_rating)                        
                    elif (np.mean(team_a_avg) < np.mean(team_b_avg) and len(team_a) < int(nplayers/2)):
                        team_a.append(list(squad)[i])
                        team_a_avg.append(player_rating)
                    elif len(team_b) < int(nplayers/2):
                        team_b.append(list(squad)[i])
                        team_b_avg.append(player_rating)
                    else:
                        team_a.append(list(squad)[i])
                        team_a_avg.append(player_rating)  
                if abs(np.mean(team_a_avg) - np.mean(team_b_avg)) <= abs(besteam_a_avg - besteam_b_avg) or nit == 1:
                    besteam_a = zip(team_a, np.around(team_a_avg, decimals = 1))  
                    besteam_b = zip(team_b, np.around(team_b_avg, decimals = 1))  
                    besteam_a_avg = np.around(np.mean(team_a_avg), decimals = 1)
                    besteam_b_avg = np.around(np.mean(team_b_avg), decimals = 1)
                if nit == n: repeat = False
            return render_template('match.html', TEAM_NAME = team_name, USER = user, TEAM =  players, TEAM_A = besteam_a, TEAM_A_AVG = besteam_a_avg, TEAM_B = besteam_b, TEAM_B_AVG = besteam_b_avg) 


if __name__ == "__main__":
    create_connection()
    app.run()
