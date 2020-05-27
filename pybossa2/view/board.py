# -*- coding: utf-8 -*- 
import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

def get_env_variable(name):
    try:
        return os.environ[name]
    except KeyError:
        message = "Expected environment variable '{}' not set.".format(name)
        raise Exception(message)

# get env vars OR ELSE
POSTGRES_URL = "220.68.54.36:5000" #get_env_variable("POSTGRES_URL") # 5432
POSTGRES_USER = get_env_variable("POSTGRES_USER")
POSTGRES_PW = get_env_variable("POSTGRES_PW")
POSTGRES_DB = get_env_variable("POSTGRES_DB")
REDIS_URL = "220.68.54.36:5000" #get_env_variable("REDIS_URL") # 6379

#SPOTIFY_CLIENT_ID = get_env_variable("SPOTIFY_CLIENT_ID")
#SPOTIFY_CLIENT_SECRET = get_env_variable("SPOTIFY_CLIENT_SECRET")
#SPOTIFY_REDIRECT_URL = get_env_variable("SPOTIFY_REDIRECT_URL")

#SPOTIFY_SCOPES = "user-read-private user-read-email user-read-playback-state user-read-currently-playing"

app = Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = "mysql://root:<mysql_password>@localhost/flask_board"
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = REDIS_URL
app.secret_key = get_env_variable("SECRET_KEY")

DB_URL = 'postgresql+psycopg2://{user}:{pw}@{url}/{db}'.format(user=POSTGRES_USER,pw=POSTGRES_PW,url=POSTGRES_URL,db=POSTGRES_DB)

app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # silence the deprecation warning

db = SQLAlchemy(app)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_title = db.Column(db.String(50), nullable=False)
    post_contents = db.Column(db.String(250), nullable=False)

    comment = db.relationship('Comment')

    @property
    def serializable(self):
        return {
            'id': self.id,
            'post_title': self.post_title,
            'post_content': self.post_contents
        }


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    comment_title = db.Column(db.String(50), nullable=False)
    comment_contents = db.Column(db.String(100), nullable=False)


# GET All Post
@app.route('/posts', methods=["GET"])
def all_user():
    posts = Post.query.all()

    return jsonify(data=[post.serializable for post in posts])
    # print(posts)
    # if posts is None or "[]":
    #     return jsonify({"message": "Post가 없습니다."})
    # else:
    #     return jsonify(data=[post.serializable for post in posts])


# Get Post
@app.route('/posts/<post_id>', methods=["GET"])
def view_post(post_id):
    post = Post.query.join().filter_by(id=post_id).first()

    if post is None:
        return jsonify({"message": "없는 Post 입니다."})
    else:
        return jsonify({"data": post.serializable})


# Add Post
@app.route('/posts', methods=['POST'])
def add_post():
    post_title = request.form.get("post_title")
    post_contents = request.form.get("post_contents")

    if (post_title and post_contents) is "" or None:
        return jsonify({"message": "제목이나 내용은 비워둘 수 없습니다."})
    else:
        data = Post(post_title=post_title, post_contents=post_contents)
        db.session.add(data)
        db.session.commit()
        return jsonify({"message": "Post 생성을 성공했습니다."})


# Delete Post
@app.route('/posts/<post_id>', methods=["DELETE"])
def delete_post(post_id):
    if post_id is "" or None:
        return jsonify({"message": "없는 Post 입니다."})
    else:
        data = Post.query.filter_by(id=post_id).first()

        if data is None:
            return jsonify({"message": "없는 Post 입니다."})
        else:
            db.session.delete(data)
            db.session.commit()
            return jsonify({"message": "Post 삭제를 성공했습니다."})


# Add Comment
@app.route('/posts/<post_id>/comment', methods=['POST'])
def add_comment(post_id):
    comment_title = request.form.get("comment_title")
    comment_contents = request.form.get("comment_contents")

    if (comment_title and comment_contents) is "" or None:
        return jsonify({"message": "제목이나 내용은 비워둘 수 없습니다."})

    if post_id is None or "":
        return jsonify({"message": "Comment 작성 중 오류가 발생했습니다."})
    else:
        data = Comment(post_id=post_id, comment_title=comment_title, comment_contents=comment_contents)
        db.session.add(data)
        db.session.commit()
        return jsonify({"message": "Comment 생성을 성공했습니다."})


# Delete Comment
@app.route('/comments/<comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    if comment_id is "" or None:
        return jsonify({"message": "없는 Comment 입니다"})
    else:
        data = Comment.query.filter_by(id=comment_id).first()

        if data is None:
            return jsonify({"message": "없는 Comment 입니다"})
        else:
            db.session.delete(data)
            db.session.commit()
            return jsonify({"message": "Comment 삭제를 성공했습니다."})


# Server Start
if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)


