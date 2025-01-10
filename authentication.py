from flask import session, redirect, url_for
from functools import wraps
from models import Users

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("userid")
        user = Users.query.filter_by(UserID=user_id).first()
        if not user:  # check users logged in
            return redirect(url_for('login')) 
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('userid')
        user = Users.query.filter_by(UserID=user_id).first()
        if user:
            userIsAdmin = user.admin
            if userIsAdmin: 
                return f(*args, **kwargs)
            return redirect(url_for('userhome'))
    return decorated_function
