import time
from flask import Flask, request, render_template, url_for, session, redirect, jsonify, flash
from flask_sqlalchemy import SQLAlchemy  
from config import Config
from models import * 
from database import db
from collections import Counter
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from authenication import *
from itsdangerous import URLSafeTimedSerializer
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

#set up/start the flask app
app = Flask(__name__)
# configuring flask application 
app.config.from_object(Config)

#starts/initialises database for my flask
db.init_app(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])


# redirecting to login page
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        #find account and make sure user is not null then later check for password too
        user = Users.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['userid'] = user.UserID
            if user.admin:
                return redirect(url_for('adminhome'))
            return redirect(url_for('userhome'))
        else:
            return 'try again'
    return render_template('login.html')

#logout 
@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Removee user ID from session
    return redirect(url_for('login'))



#making route for home page
@app.route('/userhome', methods=['GET','POST'])
@login_required
def userhome():
    teams = Team.query.all()
    rows = []
    for team in teams:
        dic = {'House': '', 'Played': 0, 'Won': 0, 'Drawn': 0, 'Lost': 0, 'GoalsFor': 0, 'GoalsAgainst': 0, 'GoalDifference': 0, 'Points': 0,}
        dic['House'] = team.TeamName
        # when theyre team A 
        matchesWhereTeamA = Match.query.filter(Match.TeamA == team.TeamID).all()
        for match in matchesWhereTeamA:
            if match.Score is None:
                continue
            dic['GoalsFor'] += match.Score[0]
            dic['GoalsAgainst'] += match.Score[1]
            dic['Played'] += 1
            if match.Score[0] > match.Score[1]:
                dic['Won'] += 1
            elif match.Score[0] == match.Score[1]:
                dic['Drawn'] += 1
            else:
                dic['Lost'] += 1
        matchesWhereTeamB = Match.query.filter(Match.TeamB == team.TeamID).all()
        for match in matchesWhereTeamB:
            if match.Score is None:
                continue
            dic['GoalsFor'] += match.Score[1]
            dic['GoalsAgainst'] += match.Score[0]
            dic['Played'] += 1
            if match.Score[1] > match.Score[0]:
                dic['Won'] += 1
            elif match.Score[0] == match.Score[1]:
                dic['Drawn'] += 1
            else:
                dic['Lost'] += 1
        dic['GoalDifference'] = dic['GoalsFor'] - dic['GoalsAgainst']
        dic['Points'] = dic['Won'] * 3 + dic['Drawn']
        rows.append(dic)
    rows = sorted(
        rows, 
        key=lambda x: (x['Points'], x['GoalDifference']),  # Points is now guaranteed to be an integer
        reverse=True
    )
    return render_template('userhome.html', rows=rows)




#making route for admin home page
#allowing for admin home page to input data into database
# 

@app.route('/adminhome', methods=['GET','POST'])
@login_required
@admin_required
def adminhome():
    print("user in admin home")
    positions = ['GK','LB','CB','RB','LWB','RWB','CDM','CM','LM','RM','CAM','LW','RW','LF','RF','CF','ST']
    if request.method == 'POST':
        #retrieve formid to differentiate the different forms 
        form_id = request.form['form_id']
        if form_id == 'add_fixture':
            date = request.form['date']
            teamA = request.form['teamA']
            teamB = request.form['teamB']
            venue = request.form['venue']
            VenueID = Venue.query.filter_by(VenueName=venue).first().VenueID
            new_fixture = Match(MatchDate=date, TeamA=teamA, TeamB=teamB, VenueID=VenueID)
            try:
                #try add to the database
                db.session.add(new_fixture)
                #commit the session to the databade
                db.session.commit()
                return render_template('adminhome.html', fixture_entered_successfully=True, positions = positions)
            except Exception as e:
                #if there was an error get rid of changes in the database
                db.session.rollback()
                return f"error: {e}"
        elif form_id =='add_score':
            match = request.form['match']
            score = [int(request.form['scoreTeamA']), int(request.form['scoreTeamB'])]

            record = Match.query.get(match)

            try: 
                record.Score = score
                db.session.commit()
            
            except Exception as e:
                #if there was an error get rid of changes in the database
                db.session.rollback()
                return f"error: {e}"
            
            for key in request.form:
                if key.startswith('playerGoal'):
                    goalscorer=request.form[key]
                    player = Player.query.get(goalscorer)
                    
                    try:
                        if player.Goalsscored:
                            player.Goalsscored = player.Goalsscored + 1
                        else:
                            player.Goalsscored = 1
                        db.session.commit()
                    except Exception as e:
                    #if there was an error get rid of changes in the database
                        db.session.rollback()
                        return f"error: {e}"
            

            
            return render_template('adminhome.html', match_entered_successfully=True, positions = positions)
            




        elif form_id == 'add_player':
            forename = request.form['forename']
            surname = request.form['surname']
            team = request.form['team']
            position = request.form['position']
            new_player = Player(Forename=forename, Surname=surname, TeamID=team, Position=position)
            try:
                #try add new player to the database
                db.session.add(new_player)
                #commit the session to the databade
                db.session.commit()
                return render_template('adminhome.html', player_entered_successfully=True, positions = positions)
            except Exception as e: 
                #if there was an error get rid of changes in the database
                db.session.rollback()
                return f"error: {e}"

        elif form_id == 'add_manager':
            forename = request.form['forename-manager']
            surname = request.form['surname-manager']
            team = request.form['team-manager']
            new_manager = Manager(Forename=forename, Surname=surname, TeamID=team)
            try:
                #try add new manager to the database
                db.session.add(new_manager)
                #commit the session to the databade
                db.session.commit()
                return render_template('adminhome.html', manager_entered_successfully=True, positions = positions)
            except Exception as e:
                #if there was an error get rid of changes in the database
                db.session.rollback()
                return f"error: {e}"
    return render_template('adminhome.html', positions = positions)

# signup page processes link with db 
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    #check if method is post (if form is submitted)
    if request.method == 'POST': 
        username = request.form['username']
        email = request.form['email']
        forename = request.form['forename']
        surname = request.form['surname']
        password = request.form['password']
        #assume theyre not admin 
        if request.form.get('admin'):
            admin = True
        else:
            admin=False
        hashpassword = generate_password_hash(password,method='pbkdf2:sha256') 
        new_user = Users(username=username, email= email, forename=forename, surname=surname, password=hashpassword, admin=admin)

        try:
            #try add to the database
            db.session.add(new_user)
            #commit the session to the databade
            db.session.commit()
            return redirect(url_for('login'))
        except Exception as e: 
            #if there was an error get rid of changes in the database
            db.session.rollback()
            return f"error: {e}"
    return render_template('signup.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = Users.query.filter_by(email=email).first()
        print(f'user: {user}')
        if user:
            token = serializer.dumps(user.email, salt='password-reset-salt')
            print(f'token: {token}')
            reset_url = url_for('reset_password', email=email, token=token, _external=True)
            print(f'reset url: {reset_url}')
            send_reset_email(user.email, reset_url)
            return 'A password reset link has been sent'
    return render_template('forgotpassword.html')
        

def send_reset_email(to_email, reset_url):
    smtp_server = '108.177.15.109'
    smtp_port = 587
    smtp_username = 'mnfwelly@gmail.com'
    smtp_password = 'yccj umea jdvl hezh'
    # make the email content
    subject = "Password Reset Request"
    sender_email = smtp_username
    receiver_email = to_email
    body = f"To reset your password, visit the following link: {reset_url}\n\nIf you did not make this request, please ignore this email."
    #make the email 
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.set_debuglevel(1)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
            print(f"Password reset email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):

    email = request.args.get('email')

    if request.method == 'POST':
        new_password = request.form['password']
        user = Users.query.filter_by(email=email).first()
        if user:
            user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
            db.session.commit()
            flash('Your password has been changed')
            time.sleep(0.5)
            
            return redirect(url_for('login'))
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except:
        return 'The reset link is invalid or has expired.'


    return render_template('reset_password.html', token=token)
    


@app.route('/get-teams', methods=['GET'])
def get_teams():
    #fetch all teams from db
    teams=Team.query.all()

    teams_lists = [{'TeamID': team.TeamID, 'TeamName': team.TeamName} for team in teams]
    return jsonify(teams_lists)


@app.route('/get-venues', methods = ['GET'])
def get_venues():
    #fetch venues from db
    venues = Venue.query.all()
    #list of dictionaries, each dict is a venue
    #getting teamid and teamname 
    venue_lists = [{'VenueID': venue.VenueID, 'name': venue.VenueName, 'location': venue.Location} for venue in venues]
    return jsonify(venue_lists)

@app.route('/get-matches', methods=['GET'])
def get_matches():
    # using dictionary to convert teamid into team name 
    matches = Match.query.all()
    teams = Team.query.all()
    teams_dict = {team.TeamID: team.TeamName for team in teams}
    match_list = [{'MatchID': match.MatchID, 'date': match.MatchDate, 'teamA': teams_dict[match.TeamA], 
                   'teamB': teams_dict[match.TeamB]} for match in matches]
    #filter to see if match has been played or not
    match_list_filtered = [match for match in match_list if match['date']<= datetime.date.today()]
    #changing date to display only day and month
    for match in match_list_filtered:
        match['date'] = match['date'].strftime('%d-%m') 
    return jsonify(match_list_filtered)


@app.route('/get-players', methods=['GET'])
def get_players():
    #fetch all players from db
    players = Player.query.all()
    #create a list of dictionaries, a dict per player
    players_list = [{'PlayerID': player.PlayerID, 'forename': player.Forename, 'surname': player.Surname} for player in players]
    return jsonify(players_list)


@app.route('/topscorers', methods=['GET'])
@login_required
def top_scorers():
    players = Player.query.all()
    teams = Team.query.all()

    # Create a dictionary for teams (TeamID into their Teamname)
    teams_dict = {team.TeamID: team.TeamName for team in teams}

    #  a list of players with their details
    players_list = [{
        'PlayerID': player.PlayerID, 
        'forename': player.Forename, 
        'surname': player.Surname, 
        'Goalsscored': player.Goalsscored if player.Goalsscored is not None else 0,  
        'Team': teams_dict.get(player.TeamID, 'Unknown')  # Fetch team name using TeamID, default to unknown if cannot find
    } for player in players]

    # Sort players by goals scored in descending order
    players_list_sorted = sorted(
        players_list, 
        key=lambda x: x['Goalsscored'],  # Goalsscored is now guaranteed to be an integer
        reverse=True
    )
    print(players_list_sorted)
    
    return render_template('topscorers.html',top_scorers=players_list_sorted)

@app.route('/fixtures', methods=['GET'])
@login_required
def fixtures():
    fixtures = Match.query.order_by(Match.MatchDate).all()
    teams = Team.query.all()

    # Create a dictionary for teams (TeamID -> TeamName)
    teams_dict = {team.TeamID: team.TeamName for team in teams}
    for fixture in fixtures:
        fixture.TeamA = teams_dict[fixture.TeamA]
        fixture.TeamB = teams_dict[fixture.TeamB]
        if fixture.Score is None:
            fixture.Score = 'N/A'
    
    return render_template('fixtures.html', fixtures=reversed(fixtures))

@app.route('/houses', methods=['GET'])
@login_required
def houselist():

    housemembers = Player.query.all()
    houses = Team.query.all()

    #create a dictionary for teams (teamid-> teamName)
    houses_dict ={team.TeamID: team.TeamName for team in houses}

    #list of players and their details so i can put them in the house dropdowns
    house_list = {}
    for house in houses: 
        house_list[house.TeamName] = [{ 
            'PlayerID': player.PlayerID,
            'forename': player.Forename,
            'surname': player.Surname,
            'position': player.Position,
            'Team': houses_dict.get(player.TeamID, 'Unknown')
            
        } for player in housemembers if player.TeamID == house.TeamID
        ]
    return render_template('houses.html', houses=houses, house_list=house_list)

if __name__ == '__main__':
    app.run(debug=True) 

