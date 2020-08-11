# -*- coding: utf8 -*-
# This file is part of PYBOSSA.
#
# Copyright (C) 2017 Scifabric LTD.
#
# PYBOSSA is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PYBOSSA is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PYBOSSA.  If not, see <http://www.gnu.org/licenses/>.
"""Cache module for users."""
from sqlalchemy.sql import text
from sqlalchemy.exc import ProgrammingError
from pybossa.core import db, timeouts
from pybossa.cache import cache, memoize, delete_memoized
from pybossa.util import pretty_date, exists_materialized_view
from pybossa.model.user import User
from pybossa.cache.projects import overall_progress, n_tasks, n_volunteers
from pybossa.model.project import Project
from pybossa.leaderboard.data import get_leaderboard as gl
from pybossa.leaderboard.jobs import leaderboard as lb


session = db.slave_session


def get_leaderboard(n, user_id=None, window=0, info=None):
    """Return the top n users with their rank."""
    try:
        lb(info=info)
        return gl(top_users=n, user_id=user_id, window=window, info=info)
    except ProgrammingError:
        db.session.rollback()
        lb(info=info)
        return gl(top_users=n, user_id=user_id, window=window, info=info)


def get_category_leaderboard(current_user_name, category_name):
    sql = text('''
               SELECT ROW_NUMBER() OVER(ORDER BY SUM(t.point) desc) AS rank, u.id AS id, u.name AS name,
               SUM(t.point) AS point, c.name AS category_name
               FROM "user" u, category c, project p, task_run t
               WHERE p.category_id = c.id AND t.project_id = p.id AND t.user_id = u.id AND c.name=:cat_name GROUP BY u.id, c.name ORDER BY c.name, 4 DESC;
               ''')
    results = session.execute(sql, dict(cat_name=category_name))
    rank_categorys = []
    for row in results:
        if row.rank <= 20:
            rank_category = dict(id=row.id, rank=row.rank, name=row.name, point=row.point,
                                category_name=row.category_name)
            rank_categorys.append(rank_category)
        elif row.rank > 20 and row.name == current_user_name:
            rank_category = dict(id=row.id, rank=row.rank, name=row.name, point=row.point,
                                category_name=row.category_name)
            rank_categorys.append(rank_category)
    return rank_categorys

def get_category_GPA():
    sql = text('''
               SELECT u.id AS id, SUM(t.point) AS point, COUNT(t.id) AS n_tasks,
               COUNT(CASE WHEN t.score_mark = True THEN 1 END) AS n_correct,
               COUNT(CASE WHEN t.completed_score = False THEN 1 END) AS n_no_score, c.name AS category_name
               FROM "user" u, category c, project p, task_run t
               WHERE p.category_id = c.id AND t.project_id = p.id AND t.user_id = u.id GROUP BY p.name, u.id, c.name ORDER BY c.name DESC;
               ''')
    results = session.execute(sql)
    rank_categorys = []
    for row in results:
        # n_tasks 와 n_correct 는 정답률이 얼마인지 계산하여 answer_rate 로 저장
        if(row.n_tasks - row.n_no_score > 0):
            rank_category = dict(id=row.id, point_sum=row.point,
                                 answer_rate=round((row.n_correct - row.n_no_score) / (row.n_tasks - row.n_no_score) * 100, 1),
                                 category_name=row.category_name)
        else:
            rank_category = dict(id=row.id, point_sum=row.point,
                                 answer_rate=0,
                                 category_name=row.category_name)
        rank_categorys.append(rank_category)
    return rank_categorys

def get_achievement(user_id, achievement_id):
    sql = text('''
               SELECT * FROM achievement WHERE user_id=:user_id AND achieve_id=:achieve_id;
               ''')
    results = session.execute(sql, dict(user_id=user_id, achieve_id=achievement_id))
    achievement = []
    for row in results:
        achieve = dict(id=row.id, user_id=row.user_id, created=row.created[0:10], achievement=row.achievement, achieve_id=row.achieve_id)
        achievement.append(achieve)
    return achievement

def get_category_achieve(user_id):
    sql = text('''SELECT * FROM category''')
    results = session.execute(sql)
    achieve = dict()
    for row in results:
        achieve[row.id] = 0
    sql = text('''
               SELECT a.achievement AS achievement, c.id AS c_id
               FROM achievement a, category c
               WHERE (a.category, a.created) IN
               (SELECT category, max(created) FROM achievement GROUP BY category)
               AND a.category = c.name AND user_id =:user_id
               ''')
    results = session.execute(sql, dict(user_id=user_id))
    for row in results:
        if row.achievement == None:
            continue
        rank = row.achievement.split('_')
        if rank[0] == 'bronze':
            achieve[row.c_id] = 1
        elif rank[0] == 'silver':
            achieve[row.c_id] = 2
        elif rank[0] == 'gold':
            achieve[row.c_id] = 3
        elif rank[0] == 'master':
            achieve[row.c_id] = 4
    return achieve

def get_answer_rate(user):
    sql = text('''
              SELECT COUNT(id) AS n_tasks, COUNT(CASE WHEN score_mark = True THEN 1 END) AS n_correct,
              COUNT(CASE WHEN completed_score = False THEN 1 END) AS n_no_score
              FROM task_run
              WHERE user_id=:user_id
              ''')
    results = session.execute(sql, dict(user_id=user.id))
    answer_rate = 0
    for row in results:
        if row.n_tasks - row.n_no_score > 0:
            answer_rate = row.n_correct / (row.n_tasks - row.n_no_score) * 100
        else:
            answer_rate = 0

    return round(answer_rate, 1)

def get_point_management():
    sql = ('''
           SELECT e.user_id, u.name, u.point_sum, current_point, sum(exchange_point) "exchange_sum", count(*) "count_exchange",
           count (CASE WHEN e.exchanged = '정상환급' THEN 1 END) "n_success",
           count (e.exchanged)-count (CASE WHEN e.exchanged = '정상환급' THEN 1 END) "n_failure",
           count(*)-count(e.exchanged) "n_todo"
           FROM exchange e ,"user" u
           WHERE u.id = e.user_id
           GROUP BY e.user_id,u.name,u.point_sum,current_point
           ''')
    results = session.execute(sql,dict())
    point_management = []
    for row in results:
        temp = dict(user_id=row.user_id, name=row.name, point_sum=row.point_sum, current_point=row.current_point,
                exchange_sum=row.exchange_sum, count_exchange=row.count_exchange, n_success=row.n_success,
                n_failure=row.n_failure, n_todo=row.n_todo)
        point_management.append(temp)

    return point_management

def get_user_point_history(user_id):
    """Return user point history."""
    sql = text('''
               SELECT u.id AS id, t.project_id AS project_id, p.name AS project_name, MAX(t.finish_time) AS finish_time,
               sum(t.point) AS point, p.short_name AS project_short_name, c.name AS category
               FROM "user" u, task_run t, project p, category c
               WHERE t.project_id = p.id AND t.user_id = u.id AND p.category_id = c.id
               AND u.id =:user_id
               GROUP BY t.project_id, u.id, p.name, p.short_name, c.name
               ORDER BY finish_time desc
               ''')
    results = session.execute(sql, dict(user_id=user_id))
    point_historys = []
    for row in results:
        point_history = dict(id=row.id, #project_id=row.project_id,
                project_name=row.project_name, finish_time=row.finish_time,
                            point=row.point, project_short_name=row.project_short_name, category=row.category)
        point_historys.append(point_history)
#================================================#
    sql = text('''
               SELECT user_id AS id, exchange_point, finish_time, exchanged
               FROM exchange
               WHERE user_id =:user_id AND finish_time IS NOT NULL AND exchanged != '정상환급'
               ''')
    results = session.execute(sql, dict(user_id=user_id))
    for row in results:
        exchange_point_history = dict(id=row.id, project_name="---" + str(row.exchange_point) + "포인트 "+row.exchanged, finish_time=row.finish_time,
                point="(0)", project_short_name="exchange", category="환급취소")
        point_historys.append(exchange_point_history)
#================================================#
    sql = text('''
               SELECT user_id AS id, exchange_point, finish_time
               FROM exchange
               WHERE user_id =:user_id AND finish_time IS NOT NULL AND exchanged = '정상환급'
               ''')
    results = session.execute(sql, dict(user_id=user_id))
    for row in results:
        exchange_point_history = dict(id=row.id, project_name="---" + str(row.exchange_point) + "포인트", finish_time=row.finish_time,
                point=int(row.exchange_point)*(-1), project_short_name="exchange", category="환급")
        point_historys.append(exchange_point_history)

#=============================================#
    sql = text('''
               SELECT user_id AS id, exchange_point, created
               FROM exchange
               WHERE user_id =:user_id AND finish_time IS NULL
               ''')
    results = session.execute(sql,dict(user_id=user_id))
    for row in results:
        exchange_point_history = dict(id=row.id, project_name="---" + str(row.exchange_point) + "포인트", finish_time = row.created,
                point=int(row.exchange_point)*(-1), project_short_name="exchange", category="환급신청")
        point_historys.append(exchange_point_history)


    return point_historys


#==============================================#
#def get_all_user_point_history():
#    """Return user point history."""
#    sql = text('''
#               SELECT u.id AS id, u.name AS uname, t.project_id AS project_id, p.name AS project_name, MAX(t.finish_time) AS finish_time,
#               sum(t.point) AS point, p.short_name AS project_short_name, c.name AS category
#               FROM "user" u, task_run t, project p, category c
#               WHERE t.project_id = p.id AND t.user_id = u.id AND p.category_id = c.id
#               GROUP BY t.project_id, u.id, p.name, p.short_name, c.name
#               ORDER BY finish_time desc
#               ''')
#    results = session.execute(sql, dict())
#    all_point_historys = []
#    for row in results:
#        all_point_history = dict(id=row.id, project_id=row.project_id, name=row.uname,
#                project_name=row.project_name, finish_time=row.finish_time[0:10],
#                            point=row.point, project_short_name=row.project_short_name, category=row.category)
#        all_point_historys.append(all_point_history)
#
#    return all_point_historys

def get_all_user_point_history():
    """Return user point history."""
    sql = text('''
               SELECT u.id AS id, u.name AS uname, t.project_id AS project_id, p.name AS project_name, MAX(t.finish_time) AS finish_time,
               sum(t.point) AS point, p.short_name AS project_short_name, c.name AS category
               FROM "user" u, task_run t, project p, category c
               WHERE t.project_id = p.id AND t.user_id = u.id AND p.category_id = c.id
               GROUP BY t.project_id, u.id, p.name, p.short_name, c.name
               ORDER BY finish_time desc
             ''')
    results = session.execute(sql, dict())
    point_historys = []
    for row in results:
        point_history = dict(id=row.id, name=row.uname,
                project_name=row.project_name, finish_time=row.finish_time,
                point=row.point, project_short_name=row.project_short_name, category=row.category)
        point_historys.append(point_history)
#================================================#
    sql = text('''
               SELECT e.user_id AS id, u.name AS uname, e.exchange_point, e.finish_time, e.exchanged
               FROM exchange e, "user" u
               WHERE finish_time IS NOT NULL AND exchanged != '정상환급'
               AND e.user_id = u.id
               ''')
    results = session.execute(sql, dict())
    for row in results:
        exchange_point_history = dict(id=row.id, project_name="---" + str(row.exchange_point) + "포인트 "+row.exchanged, finish_time=row.finish_time, name=row.uname,
                point="(0)", project_short_name="exchange", category="환급취소")
        point_historys.append(exchange_point_history)
#================================================#
    sql = text('''
               SELECT user_id AS id, u.name AS uname, exchange_point, finish_time
               FROM exchange e, "user" u
               WHERE finish_time IS NOT NULL AND exchanged = '정상환급'
               AND e.user_id = u.id
               ''')
    results = session.execute(sql, dict())
    for row in results:
        exchange_point_history = dict(id=row.id, project_name="---" + str(row.exchange_point) + "포인트", finish_time=row.finish_time, name=row.uname,
                point=int(row.exchange_point)*(-1), project_short_name="exchange", category="환급완료")
        point_historys.append(exchange_point_history)
#=============================================#
    sql = text('''
               SELECT user_id AS id, u.name AS uname, exchange_point, e.created
               FROM exchange e, "user" u
               WHERE finish_time IS NULL
               AND e.user_id = u.id
               ''')
    results = session.execute(sql,dict())
    for row in results:
        exchange_point_history = dict(id=row.id, project_name="---" + str(row.exchange_point) + "포인트", finish_time = row.created, name=row.uname,
                point=int(row.exchange_point)*(-1), project_short_name="exchange", category="환급신청")
        point_historys.append(exchange_point_history)

    return point_historys



def get_manage_exchange():
    """RETURN REQUESTED EXCHANGE"""
    sql = text('''
               SELECT e.id AS id, e.user_id AS user_id, u.name AS user, e.request_name AS account_holder, e.bank AS bank,
               e.account_number AS account_number, e.exchange_point AS point, e.created as request_time, e.down_check AS down_check
               FROM exchange e, "user" u
               WHERE u.id = e.user_id and e.finish_time is null and e.down_check is null
               ORDER BY finish_time desc
               ''')
    results = session.execute(sql, dict())
    manage_exchanges =[]
    for row in results:
        manage_exchange = dict(id=row.id, user_id=row.user_id, user=row.user, account_number=row.account_number,
                bank=row.bank, account_holder=row.account_holder, point=row.point, request_time=row.request_time[0:10], down_check=row.down_check)
        manage_exchanges.append(manage_exchange)
    return manage_exchanges

def get_down_check_exchange():
    """RETURN REQUESTED EXCHANGE"""
    sql = text('''
               SELECT e.id AS id, e.user_id AS user_id, u.name AS user, e.request_name AS account_holder, e.bank AS bank,
               e.account_number AS account_number, e.exchange_point AS point, e.created as request_time, e.down_check AS down_check
               FROM exchange e, "user" u
               WHERE u.id = e.user_id and e.finish_time is null and e.down_check is not null
               ORDER BY finish_time desc
               ''')
    results = session.execute(sql, dict())
    manage_exchanges =[]
    for row in results:
        manage_exchange = dict(id=row.id, user_id=row.user_id, user=row.user, account_number=row.account_number,
                bank=row.bank, account_holder=row.account_holder, point=row.point, request_time=row.request_time[0:10], down_check=row.down_check)
        manage_exchanges.append(manage_exchange)
    return manage_exchanges

def get_all_exchange_history():
    """RETURN ALL EXCHANGE HISTORY"""
    sql = text('''
               SELECT u.name AS name, e.request_name AS request_name, e.bank AS bank ,e.account_number AS account_number,
               e.finish_time AS finish_time, e.exchanged AS exchanged, e.exchange_point AS point
               FROM "user" u, exchange e
               WHERE u.id = e.user_id AND e.finish_time IS NOT NULL
               ORDER BY finish_time desc
               ''')
    results = session.execute(sql,dict())
    all_exchange_history=[]
    for row in results:
        exchange_history = dict(name=row.name, request_name=row.request_name, bank=row.bank, account_number=row.account_number,
                finish_time=row.finish_time, point=row.point, exchanged=row.exchanged)
        all_exchange_history.append(exchange_history)

    return all_exchange_history

def get_manage_exchange_list():
    """RETURN REQUESTED EXCHANGE"""
    sql = text('''
               SELECT e.id AS id, e.user_id AS user_id, u.name AS user, e.request_name AS account_holder, e.bank AS bank,
               e.account_number AS account_number, e.exchange_point AS point, e.created as request_time
               FROM exchange e, "user" u
               WHERE u.id = e.user_id and e.finish_time is null
               ORDER BY finish_time desc
               ''')
    results = session.execute(sql, dict())
    manage_exchanges =[]
    for row in results:
        manage_exchange = [row.user_id, row.user, row.account_number,row.bank, row.account_holder, row.point, row.request_time[0:10]]
        manage_exchanges.append(manage_exchange)
    return manage_exchanges

def get_all_user_point_history_list():
    """Return user point history."""
    sql = text('''
               SELECT u.id AS id, u.name AS uname, t.project_id AS project_id, p.name AS project_name, MAX(t.finish_time) AS finish_time,
               sum(t.point) AS point, p.short_name AS project_short_name, c.name AS category
               FROM "user" u, task_run t, project p, category c
               WHERE t.project_id = p.id AND t.user_id = u.id AND p.category_id = c.id
               GROUP BY t.project_id, u.id, p.name, p.short_name, c.name
               ORDER BY finish_time desc
               ''')
    results = session.execute(sql, dict())
    all_point_historys = []
    for row in results:
        all_point_history = [row.id, row.uname, row.category, row.project_name, row.finish_time[0:10],
                            row.point]
        all_point_historys.append(all_point_history)

    return all_point_historys

def get_all_exchange_history_list():
    """RETURN ALL EXCHANGE HISTORY"""
    sql = text('''
               SELECT u.id AS id, u.name AS name, e.request_name AS request_name, e.bank AS bank ,e.account_number AS account_number,
               e.finish_time AS finish_time, e.exchanged AS exchanged, e.exchange_point AS point
               FROM "user" u, exchange e
               WHERE u.id = e.user_id AND e.finish_time IS NOT NULL
               ORDER BY finish_time desc
               ''')
    results = session.execute(sql,dict())
    all_exchange_history=[]
    for row in results:
        exchange_history = [row.id, row.name, row.request_name, row.bank, row.account_number,
                row.finish_time[0:10], row.point, row.exchanged]
        all_exchange_history.append(exchange_history)

    return all_exchange_history
 

def get_requested_exchange_by_id(exchange_id):
    """RERUTN REQUESTED_EXCHANGE OF ONE ROW for ID"""
    sql = text('''
               SELECT id , user_id, exchange_point AS point
               FROM exchange
               WHERE id =:exchange_id
               ''')
    result = session.execute(sql,dict(exchange_id=exchange_id))
    for row in result:
        get_re = dict(id=row.id, user_id=row.user_id, point=row.point)

    return get_re





@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def get_user_summary(name, current_user=None):
    """Return user summary."""
    sql = text('''
               SELECT "user".id, "user".name, "user".fullname, "user".created,
               "user".api_key, "user".twitter_user_id, "user".facebook_user_id,
               "user".google_user_id, "user".info, "user".admin,
               "user".locale, "user".sex, "user".birth, "user".point_sum, "user".current_point, "user".achievement,
               "user".email_addr, COUNT(task_run.user_id) AS n_answers,
               "user".valid_email, "user".confirmation_email_sent, 
               "user".restrict
               FROM "user"
               LEFT OUTER JOIN task_run ON "user".id=task_run.user_id
               WHERE "user".name=:name
               GROUP BY "user".id;
               ''')
    results = session.execute(sql, dict(name=name))
    user = dict()
    for row in results:
        user = dict(id=row.id, name=row.name, fullname=row.fullname,
                    created=row.created, api_key=row.api_key,
                    twitter_user_id=row.twitter_user_id,
                    google_user_id=row.google_user_id,
                    facebook_user_id=row.facebook_user_id,
                    info=row.info, admin=row.admin,
                    locale=row.locale, sex=row.sex, birth=row.birth, point_sum=row.point_sum, current_point=row.current_point, achievement=row.achievement,
                    email_addr=row.email_addr, n_answers=row.n_answers,
                    valid_email=row.valid_email,
                    confirmation_email_sent=row.confirmation_email_sent,
                    restrict=row.restrict,
                    registered_ago=pretty_date(row.created))
    if user:
        rank_score = rank_and_score(user['id'])
        user['rank'] = rank_score['rank']
        user['score'] = rank_score['score']
        user['total'] = get_total_users()
        if user['restrict']:
            if (current_user and
                current_user.is_authenticated and
               (current_user.id == user['id'])):
                return user
            else:
                return None
        else:
            return user
    else:  # pragma: no cover
        return None


@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def public_get_user_summary(name):
    """Sanitize user summary for public usage"""
    private_user = get_user_summary(name)
    public_user = None
    if private_user is not None:
        u = User()
        public_user = u.to_public_json(data=private_user)
    return public_user


@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def rank_and_score(user_id):
    """Return rank and score for a user."""
    if exists_materialized_view(db, 'users_rank') is False:
        lb()
    sql = text('''SELECT * from users_rank WHERE id=:user_id''')

    results = session.execute(sql, dict(user_id=user_id))
    rank_and_score = dict(rank=None, score=None)
    for row in results:
        rank_and_score['rank'] = row.rank
        rank_and_score['score'] = row.score
    return rank_and_score

def projects_answer_rate(user_id):
    sql = text('''
               SELECT p.id AS id, COUNT(t.id) AS n_tasks, COUNT(CASE WHEN t.score_mark = True THEN 1 END) AS n_correct,
               COUNT(CASE WHEN t.completed_score = False THEN 1 END) AS complete_check
               FROM project p, task_run t
               WHERE t.project_id = p.id AND t.user_id=:user_id GROUP BY p.id
               ''')
    results = session.execute(sql, dict(user_id=user_id))
    projects_answer_rate = []
    for row in results:
        project = dict(id=row.id, n_correct_rate=row.n_correct, n_tasks_rate=row.n_tasks, complete_check=True)
        if row.complete_check == row.n_tasks:
            project['complete_check'] = False
        projects_answer_rate.append(project)
    return projects_answer_rate

def projects_contributed(user_id, order_by='name'):
    """Return projects that user_id has contributed to."""
    sql = text('''
               WITH projects_contributed as
                    (SELECT project_id, MAX(finish_time) as last_contribution  FROM task_run
                     WHERE user_id=:user_id GROUP BY project_id)
               SELECT * FROM project, projects_contributed
               WHERE project.id=projects_contributed.project_id ORDER BY {} DESC;
               '''.format(order_by))
    results = session.execute(sql, dict(user_id=user_id))
    projects_contributed = []
    for row in results:
        project = dict(row)
        project['n_tasks'] = n_tasks(row.id)
        project['n_volunteers'] = n_volunteers(row.id)
        project['overall_progress'] = overall_progress(row.id)
        projects_contributed.append(project)
    return projects_contributed


@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def projects_contributed_cached(user_id, order_by='name'):
    """Return projects contributed too (cached version)."""
    return projects_contributed(user_id, order_by='name')


def public_projects_contributed(user_id):
    """Return projects that user_id has contributed to. Public information only"""
    unsanitized_projects = projects_contributed(user_id)
    public_projects = []
    if unsanitized_projects:
        p = Project()
        for project in unsanitized_projects:
            public_project = p.to_public_json(data=project)
            public_projects.append(public_project)
    return public_projects


@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def public_projects_contributed_cached(user_id):
    """Return projects contributed too (cached version)."""
    return public_projects_contributed(user_id)


def published_projects(user_id):
    """Return published projects for user_id."""
    sql = text('''
               SELECT *
               FROM project
               WHERE project.published=true
               AND :user_id = ANY (project.owners_ids::int[]);
               ''')
    projects_published = []
    results = session.execute(sql, dict(user_id=user_id))
    for row in results:
        project = dict(row)
        project['n_tasks'] = n_tasks(row.id)
        project['n_volunteers'] = n_volunteers(row.id)
        project['overall_progress'] = overall_progress(row.id)
        projects_published.append(project)
    return projects_published


@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def published_projects_cached(user_id):
    """Return published projects (cached version)."""
    return published_projects(user_id)


def public_published_projects(user_id):
    """Return projects that user_id has contributed to. Public information only"""
    unsanitized_projects = published_projects(user_id)
    public_projects = []
    if unsanitized_projects:
        p = Project()
        for project in unsanitized_projects:
            public_project = p.to_public_json(data=project)
            public_projects.append(public_project)
    return public_projects


@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def public_published_projects_cached(user_id):
    """Return published projects (cached version)."""
    return public_published_projects(user_id)


def draft_projects(user_id):
    """Return draft projects for user_id."""
    sql = text('''
               SELECT *
               FROM project
               WHERE project.published=false
               AND :user_id = ANY (project.owners_ids::int[]);
               ''')
    projects_draft = []
    results = session.execute(sql, dict(user_id=user_id))
    for row in results:
        project = dict(row)
        project['n_tasks'] = n_tasks(row.id)
        project['n_volunteers'] = n_volunteers(row.id)
        project['overall_progress'] = overall_progress(row.id)
        projects_draft.append(project)
    return projects_draft


@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def draft_projects_cached(user_id):
    """Return draft projects (cached version)."""
    return draft_projects(user_id)


@cache(timeout=timeouts.get('USER_TOTAL_TIMEOUT'),
       key_prefix="site_total_users")
def get_total_users():
    """Return total number of users in the server."""
    count = User.query.count()
    return count


@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def get_users_page(page, per_page=24):
    """Return users with a paginator."""
    offset = (page - 1) * per_page
    sql = text('''SELECT "user".id, "user".name,
               "user".fullname, "user".email_addr,
               "user".created, "user".info, COUNT(task_run.id) AS task_runs
               FROM task_run, "user"
               WHERE "user".id=task_run.user_id GROUP BY "user".id
               ORDER BY "user".created DESC LIMIT :limit OFFSET :offset''')
    results = session.execute(sql, dict(limit=per_page, offset=offset))
    accounts = []

    u = User()

    for row in results:
        user = dict(id=row.id, name=row.name, fullname=row.fullname,
                    email_addr=row.email_addr, created=row.created,
                    task_runs=row.task_runs, info=row.info,
                    registered_ago=pretty_date(row.created))
        tmp = u.to_public_json(data=user)
        accounts.append(tmp)
    return accounts


def delete_user_summary_id(oid):
    """Delete from cache the user summary."""
    user = db.session.query(User).get(oid)
    delete_memoized(get_user_summary, user.name)


def delete_user_summary(name):
    """Delete from cache the user summary."""
    delete_memoized(get_user_summary, name)


@memoize(timeout=timeouts.get('APP_TIMEOUT'))
def get_project_report_userdata(project_id):
    """Return users details who contributed to a particular project."""
    if project_id is None:
        return None

    total_tasks = n_tasks(project_id)
    sql = text(
            '''
            SELECT id as u_id, name, fullname,
            (SELECT count(id) FROM task_run WHERE user_id = u.id AND project_id=:project_id) AS completed_tasks,
            ((SELECT count(id) FROM task_run WHERE user_id = u.id AND project_id =:project_id) * 100 / :total_tasks) AS percent_completed_tasks,
            (SELECT min(finish_time) FROM task_run WHERE user_id = u.id AND project_id=:project_id) AS first_submission_date,
            (SELECT max(finish_time) FROM task_run WHERE user_id = u.id AND project_id=:project_id) AS last_submission_date,
            (SELECT coalesce(AVG(to_timestamp(finish_time, 'YYYY-MM-DD"T"HH24-MI-SS.US') -
            to_timestamp(created, 'YYYY-MM-DD"T"HH24-MI-SS.US')), interval '0s')
            FROM task_run WHERE user_id = u.id AND project_id=:project_id) AS avg_time_per_task
            FROM public.user u WHERE id IN
            (SELECT DISTINCT user_id FROM task_run tr GROUP BY project_id, user_id HAVING project_id=:project_id);
            ''')
    results = session.execute(sql, dict(project_id=project_id, total_tasks=total_tasks))
    users_report = [
        [row.u_id, row.name, row.fullname,
         row.completed_tasks, row.percent_completed_tasks,
         row.first_submission_date, row.last_submission_date,
         round(row.avg_time_per_task.total_seconds() / 60, 2)]
         for row in results]
    return users_report


@memoize(timeout=timeouts.get('APP_TIMEOUT'))
def get_user_pref_metadata(name):
    sql = text("""
    SELECT info->'metadata', user_pref FROM public.user WHERE name=:name;
    """)

    cursor = session.execute(sql, dict(name=name))
    row = cursor.fetchone()
    upref_mdata = row[0] or {}
    upref_mdata.update(row[1] or {})
    return upref_mdata


def delete_user_pref_metadata(name):
    delete_memoized(get_user_pref_metadata, name)
