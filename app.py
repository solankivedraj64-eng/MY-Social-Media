import os
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'mysocial_media_full_production_key'

# SQLite Database Setup
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'facebook.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# DATABASE MODELS
# ==========================================

# Saved Posts Junction Table
saved_posts_table = db.Table('saved_posts',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'))
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    bio = db.Column(db.String(200), default="Coding my own social media app!")
    avatar = db.Column(db.String(300), default="https://i.pravatar.cc/150?img=68")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    saved_posts = db.relationship('Post', secondary=saved_posts_table, backref=db.backref('saved_by_users', lazy='dynamic'))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    caption = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    likes_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

# ==========================================
# FULL FRONTEND UI WITH FUNCTIONAL SHORTCUTS
# ==========================================

MASTER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Social Media</title>
    <style>
        :root { --fb-blue: #1877f2; --fb-bg: #f0f2f5; --fb-card: #ffffff; --fb-text: #050505; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: var(--fb-bg); margin: 0; padding: 0; color: var(--fb-text); }
        
        .navbar { background: var(--fb-card); height: 56px; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); position: sticky; top: 0; z-index: 100; }
        .logo { color: var(--fb-blue); font-size: 24px; font-weight: bold; text-decoration: none; }
        .nav-center { display: flex; gap: 8px; }
        .nav-tab { padding: 10px 20px; border-radius: 8px; text-decoration: none; color: #65676b; font-weight: bold; font-size: 15px; }
        .nav-tab:hover, .nav-tab.active { background: #f2f2f2; color: var(--fb-blue); }
        .nav-right { display: flex; align-items: center; gap: 12px; }
        .profile-badge { display: flex; align-items: center; gap: 8px; font-weight: 600; text-decoration: none; color: var(--fb-text); }
        .profile-badge img { width: 36px; height: 36px; border-radius: 50%; }
        .btn-logout { background: #e4e6eb; border: none; padding: 8px 12px; border-radius: 6px; font-weight: 600; cursor: pointer; text-decoration: none; color: black; font-size: 13px; }

        .auth-container { max-width: 400px; margin: 80px auto; background: var(--fb-card); padding: 30px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); text-align: center; }
        .auth-container h1 { color: var(--fb-blue); font-size: 32px; margin-bottom: 10px; }
        .input-box { width: 92%; padding: 12px; margin: 8px 0; border: 1px solid #dddfe2; border-radius: 6px; font-size: 15px; }
        .btn-submit { width: 98%; padding: 12px; background: var(--fb-blue); color: white; border: none; border-radius: 6px; font-size: 17px; font-weight: bold; cursor: pointer; margin-top: 10px; }
        .btn-green { background: #42b72a; }
        .switch-link { color: var(--fb-blue); cursor: pointer; margin-top: 15px; display: block; font-size: 14px; }

        .app-layout { display: flex; justify-content: center; gap: 24px; padding: 20px 16px; max-width: 1100px; margin: 0 auto; }
        .sidebar-left { width: 280px; display: flex; flex-direction: column; gap: 12px; }
        .feed-center { width: 580px; }

        .card { background: var(--fb-card); border-radius: 8px; padding: 14px 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); margin-bottom: 16px; }
        .shortcut-item { display: flex; align-items: center; gap: 12px; padding: 10px; border-radius: 8px; text-decoration: none; color: #050505; font-weight: 600; font-size: 15px; }
        .shortcut-item:hover { background: #e4e6eb; }

        .create-post-header { display: flex; gap: 10px; align-items: center; }
        .create-post-header img { width: 40px; height: 40px; border-radius: 50%; }
        .post-input { width: 94%; border: none; background: #f0f2f5; padding: 12px; border-radius: 20px; outline: none; font-size: 15px; }
        .post-actions-bar { display: flex; justify-content: space-between; border-top: 1px solid #e4e6eb; margin-top: 12px; padding-top: 8px; }
        .post-action-btn { background: none; border: none; padding: 8px; border-radius: 4px; color: #65676b; font-weight: 600; cursor: pointer; flex: 1; display: flex; justify-content: center; align-items: center; gap: 6px; text-decoration: none; font-size: 14px; }
        .post-action-btn:hover { background: #f2f2f2; }

        .post-author-info { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
        .post-author-info img { width: 40px; height: 40px; border-radius: 50%; }
        .post-time { font-size: 12px; color: #65676b; }
        .post-image { width: 100%; border-radius: 6px; margin: 10px 0; max-height: 450px; object-fit: cover; }
        .comments-section { border-top: 1px solid #e4e6eb; padding-top: 10px; margin-top: 10px; }
        .comment-item { background: #f0f2f5; padding: 8px 12px; border-radius: 12px; margin-bottom: 6px; font-size: 13px; }
        .user-row { display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }
    </style>
</head>
<body>

    {% if not current_user %}
    <div class="auth-container">
        <h1>My Social Media</h1>
        
        <div id="login-box">
            <form action="/login" method="POST">
                <input type="email" name="email" class="input-box" placeholder="Email Address" required>
                <input type="password" name="password" class="input-box" placeholder="Password" required>
                <button type="submit" class="btn-submit">Log In</button>
            </form>
            <span class="switch-link" onclick="toggleAuth()">Create new account</span>
        </div>

        <div id="signup-box" style="display: none;">
            <form action="/signup" method="POST">
                <input type="text" name="username" class="input-box" placeholder="Username" required>
                <input type="email" name="email" class="input-box" placeholder="Email Address" required>
                <input type="password" name="password" class="input-box" placeholder="New Password" required>
                <button type="submit" class="btn-submit btn-green">Sign Up</button>
            </form>
            <span class="switch-link" onclick="toggleAuth()">Already have an account? Log In</span>
        </div>
    </div>

    <script>
        function toggleAuth() {
            var l = document.getElementById('login-box');
            var s = document.getElementById('signup-box');
            l.style.display = l.style.display === 'none' ? 'block' : 'none';
            s.style.display = s.style.display === 'none' ? 'block' : 'none';
        }
    </script>
    {% else %}
    <div class="navbar">
        <a href="/" class="logo">My Social Media</a>
        <div class="nav-center">
            <a href="/" class="nav-tab {% if page == 'home' %}active{% endif %}">🏠 Feed</a>
            <a href="/saved" class="nav-tab {% if page == 'saved' %}active{% endif %}">🔖 Saved</a>
            <a href="/friends" class="nav-tab {% if page == 'friends' %}active{% endif %}">👥 Friends</a>
            <a href="/settings" class="nav-tab {% if page == 'settings' %}active{% endif %}">⚙️ Settings</a>
        </div>
        <div class="nav-right">
            <div class="profile-badge">
                <img src="{{ current_user.avatar }}">
                <span>{{ current_user.username }}</span>
            </div>
            <a href="/logout" class="btn-logout">Log Out</a>
        </div>
    </div>

    <div class="app-layout">
        <!-- FUNCTIONAL SIDEBAR SHORTCUTS -->
        <div class="sidebar-left">
            <div class="card">
                <h3 style="margin-top:0;">Shortcuts</h3>
                <a href="/friends" class="shortcut-item">👥 Friends & Users</a>
                <a href="/saved" class="shortcut-item">🔖 Saved Posts ({{ current_user.saved_posts|length }})</a>
                <a href="/settings" class="shortcut-item">⚙️ Profile Settings</a>
            </div>
        </div>

        <!-- CENTER DYNAMIC FEED / PAGE CONTENT -->
        <div class="feed-center">
            {% block content %}
            {% if page == 'home' %}
            <!-- CREATE POST -->
            <div class="card">
                <form action="/create_post" method="POST">
                    <div class="create-post-header">
                        <img src="{{ current_user.avatar }}">
                        <input type="text" name="caption" class="post-input" placeholder="What's on your mind, {{ current_user.username }}?" required>
                    </div>
                    <input type="text" name="image_url" class="input-box" style="margin-top:10px; padding:8px;" placeholder="Optional Image URL">
                    <div class="post-actions-bar">
                        <button type="submit" class="post-action-btn" style="color:#45bd62;">🖼️ Share Post</button>
                    </div>
                </form>
            </div>

            <!-- POSTS FEED -->
            {% for post in posts %}
            <div class="card">
                <div class="post-author-info">
                    <img src="{{ post.author.avatar }}">
                    <div>
                        <strong>{{ post.author.username }}</strong>
                        <div class="post-time">{{ post.created_at.strftime('%b %d, %Y at %H:%M') }}</div>
                    </div>
                </div>
                <div>{{ post.caption }}</div>
                {% if post.image_url %}
                <img src="{{ post.image_url }}" class="post-image">
                {% endif %}

                <div class="post-actions-bar">
                    <form action="/like/{{ post.id }}" method="POST" style="flex:1;">
                        <button class="post-action-btn">👍 Like ({{ post.likes_count }})</button>
                    </form>
                    <form action="/save_post/{{ post.id }}" method="POST" style="flex:1;">
                        <button class="post-action-btn" style="color:#1877f2;">🔖 Save</button>
                    </form>
                </div>

                <div class="comments-section">
                    {% for comment in post.comments %}
                    <div class="comment-item">
                        <strong>{{ comment.author.username }}:</strong> {{ comment.content }}
                    </div>
                    {% endfor %}
                    <form action="/comment/{{ post.id }}" method="POST" style="display:flex; gap:6px; margin-top:8px;">
                        <input type="text" name="content" class="post-input" placeholder="Write a comment..." required>
                        <button type="submit" class="btn-logout" style="background:var(--fb-blue); color:white;">Comment</button>
                    </form>
                </div>
            </div>
            {% endfor %}

            {% elif page == 'saved' %}
            <h2>🔖 Saved Posts</h2>
            {% for post in current_user.saved_posts %}
            <div class="card">
                <div class="post-author-info">
                    <img src="{{ post.author.avatar }}">
                    <div><strong>{{ post.author.username }}</strong></div>
                </div>
                <div>{{ post.caption }}</div>
                {% if post.image_url %}<img src="{{ post.image_url }}" class="post-image">{% endif %}
            </div>
            {% else %}
            <div class="card"><p>No saved posts yet!</p></div>
            {% endfor %}

            {% elif page == 'friends' %}
            <h2>👥 Registered Users / Friends</h2>
            <div class="card">
                {% for u in all_users %}
                <div class="user-row">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <img src="{{ u.avatar }}" style="width:40px; height:40px; border-radius:50%;">
                        <div>
                            <strong>{{ u.username }}</strong><br>
                            <small style="color:#65676b;">{{ u.bio }}</small>
                        </div>
                    </div>
                    <button class="btn-logout" style="background:var(--fb-blue); color:white;">Connect</button>
                </div>
                {% endfor %}
            </div>

            {% elif page == 'settings' %}
            <h2>⚙️ Profile Settings</h2>
            <div class="card">
                <form action="/update_profile" method="POST">
                    <label><strong>Bio:</strong></label>
                    <input type="text" name="bio" class="input-box" value="{{ current_user.bio }}">
                    <label><strong>Avatar URL:</strong></label>
                    <input type="text" name="avatar" class="input-box" value="{{ current_user.avatar }}">
                    <button type="submit" class="btn-submit">Save Changes</button>
                </form>
            </div>
            {% endif %}

            {% endblock %}
        </div>
    </div>
    {% endif %}

</body>
</html>
"""

# ==========================================
# ROUTES & LOGIC
# ==========================================

@app.route('/')
def home():
    if 'user_id' not in session:
        return render_template_string(MASTER_TEMPLATE, current_user=None)
    
    current_user = User.query.get(session['user_id'])
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template_string(MASTER_TEMPLATE, current_user=current_user, posts=posts, page='home')

@app.route('/saved')
def saved():
    if 'user_id' not in session: return redirect(url_for('home'))
    current_user = User.query.get(session['user_id'])
    return render_template_string(MASTER_TEMPLATE, current_user=current_user, page='saved')

@app.route('/friends')
def friends():
    if 'user_id' not in session: return redirect(url_for('home'))
    current_user = User.query.get(session['user_id'])
    all_users = User.query.filter(User.id != current_user.id).all()
    return render_template_string(MASTER_TEMPLATE, current_user=current_user, all_users=all_users, page='friends')

@app.route('/settings')
def settings():
    if 'user_id' not in session: return redirect(url_for('home'))
    current_user = User.query.get(session['user_id'])
    return render_template_string(MASTER_TEMPLATE, current_user=current_user, page='settings')

@app.route('/signup', methods=['POST'])
def signup():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    if User.query.filter_by(email=email).first(): return "Email already exists!", 400

    hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(username=username, email=email, password_hash=hashed_pw)
    db.session.add(new_user)
    db.session.commit()

    session['user_id'] = new_user.id
    return redirect(url_for('home'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        return redirect(url_for('home'))
    return "Invalid credentials!", 401

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/create_post', methods=['POST'])
def create_post():
    if 'user_id' not in session: return redirect(url_for('home'))
    caption = request.form.get('caption')
    image_url = request.form.get('image_url')

    new_post = Post(caption=caption, image_url=image_url if image_url else None, user_id=session['user_id'])
    db.session.add(new_post)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    if 'user_id' in session:
        post = Post.query.get(post_id)
        if post:
            post.likes_count += 1
            db.session.commit()
    return redirect(url_for('home'))

@app.route('/save_post/<int:post_id>', methods=['POST'])
def save_post(post_id):
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        post = Post.query.get(post_id)
        if post and post not in user.saved_posts:
            user.saved_posts.append(post)
            db.session.commit()
    return redirect(url_for('home'))

@app.route('/comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    if 'user_id' in session:
        content = request.form.get('content')
        if content:
            new_comment = Comment(content=content, user_id=session['user_id'], post_id=post_id)
            db.session.add(new_comment)
            db.session.commit()
    return redirect(url_for('home'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        user.bio = request.form.get('bio')
        user.avatar = request.form.get('avatar')
        db.session.commit()
    return redirect(url_for('settings'))

import os

if __name__ == '__main__':
    init_and_fix_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
