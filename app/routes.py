
import os
import random
import numpy as np
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# DISABLE DEBUG FOR PRODUCTION!
app.debug = False

def write_db(db_name = "", besteam = ""):
    save_path = os.path.join("db", str(db_name).upper() + ".dat")
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

def read_db(db_name = ""):
    save_path = os.path.join("db", str(db_name).upper() + ".dat")
    f1 = open(save_path, "r")
    team = f1.readlines()
    f1.close()
    return team

def db2dict(team = ""):
    besteam = {}
    for player in team:
        name, rating, votes, *voted = player.strip('\n').split(',')
        besteam[name] = {'rating': float(rating), 'votes': int(votes), 'voted': list(voted)}
    return besteam

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
        db_name = str(request.form['team']).upper()
        # Create database
        root_path = Path("db")
        if not (os.path.exists(root_path)): root_path.mkdir(parents=True, exist_ok=True)
        # Create new group key
        save_path = os.path.join("db", str(db_name) + ".dat")
        if os.path.isfile(save_path):
            return render_template('create.html', ERROR = 1)
        elif db_name.isalnum() == False or len(db_name) < 5: 
            return render_template('create.html', ERROR = 2)
        else:
            f1 = open(save_path, "w")
            f1.close()
            return redirect(url_for('access', db_name= db_name))   

@app.route('/join', methods=['GET', 'POST'])
def join():
    if request.method == 'GET':
        return render_template('join.html', ERROR = 0) 
    else:
        db_name = str(request.form['team']).upper()
        if Path(os.path.join("db", db_name + ".dat")).is_file(): 
            return redirect(url_for('access', db_name = db_name))
        else:
            return render_template('join.html', ERROR = 1)

@app.route('/team/<db_name>', methods=['GET', 'POST'])
def access(db_name = ""):
    if request.method == 'GET':
        besteam = db2dict(read_db(db_name))
        team = [player.split(',')[0] for player in besteam]
        return render_template('access.html', TEAM_NAME = db_name, TEAM = team)
    else:
        user = str((request.form['user'])).upper()
        if user == "":
            render_template('add.html', TEAM_NAME = db_name, ERROR =  0) 
            return redirect(url_for('add', db_name = db_name))
            
        else:
            return redirect(url_for('view', db_name = db_name, user = user))


@app.route('/team/<db_name>/view', methods=['GET'])
def view(db_name = ""):
    user = str(request.args.get('user')).upper()
    team = [player.split(',')[0] for player in db2dict(read_db(db_name))]
    return render_template('team.html', TEAM_NAME = db_name, TEAM = team, USER = user)

@app.route('/team/<db_name>/add', methods=['GET', 'POST'])
def add(db_name = ""):
    if request.method == 'GET':
        return render_template('add.html', TEAM_NAME = db_name, ERROR =  0) 
    else:
        player = str(request.form['new_player']).upper()
        # Populate team
        besteam = db2dict(read_db(db_name))       
        # Check if player exists
        if player != "" or player.isalnum() == False:     
            if not player in besteam:
                besteam[player]= {'rating': 0, 'votes': 0, 'voted': []}
                error = 0
            else:
                error = 1
        else:
            error = 2
        # Overwrite data into DB
        if error == 0: 
            write_db(db_name, besteam) 
            return redirect(url_for('view', db_name = db_name, user =  player))
        else:
            return render_template('add.html', TEAM_NAME = db_name, ERROR =  error) 

@app.route('/vote/<db_name>/<user>', methods = ['GET', 'POST'])
def vote(db_name = "", user = ""):
    # Get and create dictionary
    besteam = db2dict(read_db(db_name))
    if request.method == 'GET':
        # Populate not voted people
        team = []
        for player in besteam:
            if player != user and not player in besteam[user]['voted']:
                team.append(player)
        if team == []:
            return render_template('team.html', TEAM_NAME = db_name, TEAM = besteam, USER = user, VOTED = 1)
        else:
            return render_template('vote.html', TEAM_NAME = db_name, USER = user, TEAM =  team) 
    else:
        # Vote all team members 
        for player in besteam:
            if player != user and not player in besteam[user]['voted']:
                besteam[player]['votes'] += 1
                besteam[player]['rating'] += float(request.form[player])
                besteam[user]['voted'].append(player) 
        # Overwrite data into DB
        write_db(db_name, besteam)   
        return render_template('team.html', TEAM_NAME = db_name, TEAM = besteam, USER = user, VOTED = 0)


@app.route('/match/<db_name>/<user>', methods = ['GET', 'POST'])
def match(db_name = "", user = ""):
    # Get and create dictionary
    besteam = db2dict(read_db(db_name))    
    if request.method == 'GET':
        return render_template('match.html', TEAM_NAME = db_name, USER = user, TEAM =  besteam) 
    else:
        team = [player for player in besteam if player in request.form.keys()]
        # Check if number of players is even
        nplayers = len(team)
        if nplayers % 2:
            return render_template('match.html', TEAM_NAME = db_name, USER = user, TEAM =  besteam, ERROR = 1) 
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
            return render_template('match.html', TEAM_NAME = db_name, USER = user, TEAM =  besteam, TEAM_A = besteam_a, TEAM_A_AVG = besteam_a_avg, TEAM_B = besteam_b, TEAM_B_AVG = besteam_b_avg) 


if __name__ == "__main__":
    app.run()
