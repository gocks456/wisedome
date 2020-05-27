# -*- coding: utf8 -*-
# This file is part of PYBOSSA.
#
# Copyright (C) 2015 Scifabric LTD.
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
"""Leaderboard Jobs module for running background tasks in PYBOSSA server."""
from sqlalchemy import text
from pybossa.core import db
from pybossa.util import exists_materialized_view, refresh_materialized_view


def leaderboard(info=None):
    """Create or update leaderboard materialized view."""
    materialized_view = 'users_rank'
    materialized_view_idx = 'users_rank_idx'
    if info:
        materialized_view = 'users_rank_%s' % info
        materialized_view_idx = 'users_rank_%s_idx' % info

    if exists_materialized_view(db, materialized_view):
        #현재는 채점을 계속 누르는 상황이 아니므로 여기서 갱신 중 나중에 삭제 할 것
        all_rank_achievement()
        category_rank_achievement()
        return refresh_materialized_view(db, materialized_view)
    else:
        #sql = '''
        #           CREATE MATERIALIZED VIEW "{}" AS WITH scores AS (
        #                SELECT "user".*, COUNT(task_run.user_id) AS score
        #                FROM "user" LEFT JOIN task_run
        #                ON task_run.user_id="user".id where
        #                "user".restrict=false GROUP BY "user".id
        #            ) SELECT *, row_number() OVER (ORDER BY score DESC) as rank FROM scores;
        #      '''.format(materialized_view)

        sql = '''
                    CREATE MATERIALIZED VIEW "{}" AS WITH scores AS (
                        SELECT "user".*, "user".point_sum AS score FROM "user" where "user".restrict=false ORDER BY score DESC
                    ) SELECT *, row_number() OVER (ORDER BY score DESC) as rank FROM scores;
              '''.format(materialized_view)
       
        if info:
            sql = '''
                       CREATE MATERIALIZED VIEW "{}" AS WITH scores AS (
                            SELECT "user".*, COALESCE(CAST("user".info->>'{}' AS INTEGER), 0) AS score
                            FROM "user" where "user".restrict=false ORDER BY score DESC) SELECT *, row_number() OVER (ORDER BY score DESC) as rank FROM scores;
                  '''.format(materialized_view, info)
        db.session.execute(sql)
        db.session.commit()
        sql = '''
              CREATE UNIQUE INDEX "{}"
               on "{}"(id, rank);
              '''.format(materialized_view_idx, materialized_view)
        db.session.execute(sql)
        db.session.commit()

        return "Materialized view created"

def all_rank_achievement():
    sql = '''
                 SELECT id, point_sum, answer_rate
                 FROM users_rank
          '''
    results = db.session.execute(sql)
    for row in results:
        achieve = ''
        if row.point_sum >= 50000 and row.answer_rate >= 60:
            achieve = 'bronze_all'
            update_achievement(row.id, achieve, 'all')
        if row.point_sum >= 100000 and row.answer_rate >= 65:
            achieve = 'silver_all'
            update_achievement(row.id, achieve, 'all')
        if row.point_sum >= 150000 and row.answer_rate >= 70:
            achieve = 'gold_all'
            update_achievement(row.id, achieve, 'all')
        if row.point_sum >= 200000 and row.answer_rate >= 75:
            achieve = 'master_all'
            update_achievement(row.id, achieve, 'all')
        
    return "Achievement_all renewal"

def category_rank_achievement():
    from pybossa.cache import users as cached_users

    category_rank = cached_users.get_category_GPA()
    for row in category_rank:
        achieve = ''
        if row["point_sum"] >= 30000 and row["answer_rate"] >= 60:
            achieve = 'bronze_' + row["category_name"]
            update_achievement(row["id"], achieve, 'category', row["category_name"])
        if row["point_sum"] >= 50000 and row["answer_rate"] >= 65:
            achieve = 'silver_' + row["category_name"]
            update_achievement(row["id"], achieve, 'category', row["category_name"])
        if row["point_sum"] >= 100000 and row["answer_rate"] >= 70:
            achieve = 'gold_' + row["category_name"]
            update_achievement(row["id"], achieve, 'category', row["category_name"])
        if row["point_sum"] >= 150000 and row["answer_rate"] >= 75:
            achieve = 'master_' + row["category_name"]
            update_achievement(row["id"], achieve, 'category', row["category_name"])
        
    return "Achievement_category renewal"

def achieve_value(string):
    if string == 'bronze':
        return 0
    elif string == 'silver':
        return 1
    elif string == 'gold':
        return 2
    else:
        return 3

def update_achievement(user_id, achieve, achieve_id, category=None):
    from pybossa.core import achi_repo, user_repo
    from pybossa.model.achievement import Achievement
    import datetime

    if achi_repo.check_overlap(user_id, achieve) == True:
        now = datetime.datetime.now()
        created = now.strftime('%Y-%m-%dT%H:%M:%S.%f')
        user_achieve = Achievement(user_id = user_id, created = created, achievement = achieve, achieve_id = achieve_id)
        if category != None:
            user_achieve = Achievement(user_id = user_id, created = created, achievement = achieve, achieve_id = achieve_id, category = category)
        achi_repo.save(user_achieve)

        user = user_repo.get(user_id)
        if category == None:
            user_repo.update_achievement(user_id, achieve, achieve_id)
        else:
            u_tmp = user.achievement['category'].split('_')
            a_tmp = achieve.split('_')
            if achieve_value(u_tmp[0]) <= achieve_value(a_tmp[0]):
                user_repo.update_achievement(user_id, achieve, achieve_id)
        return "Achievement add"
    return "Achieve Overlap"
