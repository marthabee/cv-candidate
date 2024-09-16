from flask import Flask, request, render_template, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Email
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from gridfs import GridFS
from bson import ObjectId
import spacy

# Chuỗi kết nối MongoDB chính xác
uri = "mongodb+srv://bee29082004:pj2LSo7MDI3LaXPc@bee.ytah6.mongodb.net/talentmatch?retryWrites=true&w=majority"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'random_key'

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, email, user_type):
        self.id = email
        self.user_type = user_type

@login_manager.user_loader
def load_user(email):
    client = MongoClient(uri)
    db = client["login"]
    user_data = db.users.find_one({"email": email})

    # In thông tin để kiểm tra
    print("Loading User Email:", email)
    print("User Data from DB:", user_data)

    if user_data:
        return User(email=user_data["email"], user_type=user_data["user_type"])
    return None

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        client = MongoClient(uri)
        db = client["login"]
        user = db.users.find_one({"email": form.email.data})

        # In thông tin để kiểm tra
        print("Form Email:", form.email.data)
        print("Form Password:", form.password.data)
        print("User Data from DB:", user)

        if user:
            print("Stored Password Hash:", user['password'])
        if user and check_password_hash(user['password'], form.password.data):
            user_obj = User(email=user["email"], user_type=user["user_type"])
            login_user(user_obj)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')

    return render_template('login.html', title='Login', form=form)


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    user_type = StringField('User Type (candidate or company)', validators=[DataRequired()])
    submit = SubmitField('Register')

@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)  # Use default method
        new_user = {
            "email": form.email.data,
            "password": hashed_password,
            "user_type": form.user_type.data.lower()
        }

        # Print information for debugging
        print("Form Email:", form.email.data)
        print("Form Password:", form.password.data)
        print("Form User Type:", form.user_type.data)
        print("Hashed Password:", hashed_password)

        client = MongoClient(uri)
        db = client["login"]
        db.users.insert_one(new_user)

        print("CREATED")
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)



@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/upload_form')
@login_required
def upload_form():
    if current_user.user_type != 'candidate':
        flash('You do not have access to this page', 'danger')
        return redirect(url_for('job_request'))
    return render_template('upload.html')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_authenticated:
        flash('Please log in to access this page.')
    
    if current_user.user_type == 'candidate':
        return redirect(url_for('upload_form'))
    elif current_user.user_type == 'company':
        return render_template('job_request.html')
    else:
        flash('Unauthorized user type', 'danger')
        return redirect(url_for('logout'))

@app.route('/match', methods=['POST'])
def match_resumes():
    user_input = request.form.get('job_description')
    nlp = spacy.load("model_upgrade")
    doc = nlp(user_input)
    technology_names = []

    for ent in doc.ents:
        if ent.label_ in ["ORG", "TECHNOLOGY", "TECH"]:
            technology_names.append(ent.text)

    bef_technology_names = technology_names
    technology_names = list(set(technology_names))
    technology_names = [ele.lower() for ele in technology_names]

    client = MongoClient(uri)
    db = client["candidates"]
    users = db["candidates"]

    user_data = list(users.aggregate([
        {
            "$match": {
                "skills": {
                    "$in": technology_names
                }
            }
        },
        {
            "$addFields": {
                "matchedSkills": {
                    "$size": {
                        "$setIntersection": ["$skills", technology_names]
                    }
                }
            }
        },
        {
            "$sort": {
                "matchedSkills": -1,
            }
        }
    ]))

    return render_template('view_resumes.html', user_data=user_data, technology_names=bef_technology_names)

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        skills = request.form["skills"]
        resume_file = request.files["resume"]

        if not resume_file:
            flash('No resume file selected', 'danger')
            return redirect(url_for('upload'))

        try:
            client = MongoClient(uri)
            db = client["candidates"]
            fs = GridFS(db)

            # Process skills
            skills = [skill.strip().lower() for skill in skills.split(',') if skill.strip()]
            skills = list(set(skills))

            # Store the resume file in MongoDB GridFS
            resume_id = fs.put(resume_file, filename=resume_file.filename)

            # Store user details in a MongoDB collection
            users = db["candidates"]
            user_data = {
                "name": name,
                "email": email,
                "skills": skills,
                "resume_id": resume_id
            }
            users.insert_one(user_data)
            flash('Resume Uploaded Successfully', 'success')
            return redirect(url_for('upload'))

        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('upload'))

    return render_template('upload.html')

@app.route('/fetch_resume/<resume_id>')
def fetch_resume(resume_id):
    client = MongoClient(uri)
    db = client["candidates"]
    fs = GridFS(db)

    resume_file = fs.get(ObjectId(resume_id))
    response = send_file(resume_file, mimetype='application/pdf', as_attachment=True, download_name=f"{resume_id}.pdf")

    return response

if __name__ == '__main__':
    app.run(debug=True)
