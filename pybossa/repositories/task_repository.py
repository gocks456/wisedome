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

from sqlalchemy.exc import IntegrityError
from sqlalchemy import cast, Date
from sqlalchemy.sql import func

from pybossa.repositories import Repository
from pybossa.model.task import Task
from pybossa.model.task_run import TaskRun
from pybossa.exc import WrongObjectError, DBIntegrityError
from pybossa.cache import projects as cached_projects
from pybossa.core import uploader
from sqlalchemy import text, and_, extract, desc, null, distinct


from pybossa.model.project import Project

class TaskRepository(Repository):


    def get_1hour_user_data(self):
        # 최근 1시간 답변을 제출한 사용자
        from datetime import datetime, timedelta
        time = datetime.now() - timedelta(hours=1)
        return self.db.session.query(func.array_agg(distinct(TaskRun.user_id)).label('user_ids')).filter(
               and_(time <= cast(TaskRun.finish_time, Date), TaskRun.user_id.isnot(None))).one()[0]

    def is_task_completed(self, task_id):
        # task_run 각각에 포인트 업데이트
        task = self.db.session.query(Task.state.label('state')).filter(Task.id==task_id).one()
        return task.state

    def is_project_self_score(self, project_id):
        # 프로젝트 채점 방식
        project = self.db.session.query(Project.self_score.label('self_score')).filter(Project.id==project_id).one()
        return project.self_score

    def self_score(self, user_id, task_run_id):
        # 수동 채점 프로젝트 채점한 데이터 적용

        task_run = self.get_task_run(task_run_id)

        from pybossa.model.project_stats import ProjectStats
        project_data = self.db.session.query((Project.all_point/ProjectStats.n_tasks).label('point'),
                Project.featured.label('featured')).filter(
                and_(Project.id==ProjectStats.project_id) , (Project.id==task_run.project_id)).first()

        self.db.session.query(TaskRun).filter(
				and_(TaskRun.project_id==task_run.project_id), (TaskRun.id < task_run.id)).update({'completed_score': True})


        point = project_data.point
        if project_data.featured:
            point = project_data.point * 1.1

        task_run.point = point
        task_run.completed_score = True
        self.user_point_update(user_id, point)
        self.db.session.commit()

    def task_update_point(self, project_id, task_id):
        # task_run 각각에 포인트 업데이트
        if self.is_task_completed(task_id) != 'completed':
            return

        if self.is_project_self_score(project_id):
            return

        answer_data = self.db.session.query(func.count(TaskRun.user_id).label('count'), func.array_agg(TaskRun.id).label('task_id')).filter(
               and_(TaskRun.project_id==project_id), (TaskRun.task_id==task_id)).group_by(TaskRun.info).order_by(desc('count')).first()
        from pybossa.model.project_stats import ProjectStats
        project_data = self.db.session.query((Project.all_point/ProjectStats.n_tasks).label('point'),
                Project.featured.label('featured')).filter(
                and_(Project.id==ProjectStats.project_id) , (Project.id==project_id)).first()

        point = project_data.point
        if project_data.featured:
            point = project_data.point * 1.1

        # 포인트 초기화
        self.db.session.query(TaskRun).filter(TaskRun.task_id==task_id).update({'point': 0})

        if answer_data.count == 1:
            # 정답이 다 다를 때 or 반복이 1이라서 답이 1개
            self.db.session.query(TaskRun).filter(TaskRun.task_id==task_id).update({'point': point})

            for task_run_id in answer_data.task_id:
                task_run = self.get_task_run(task_run_id)
                task_run.completed_score = True
                self.user_point_update(task_run.user_id, point)

            self.db.session.commit()

        else:
            for task_run_id in answer_data.task_id:
                # 과반수의 정답이 존재할 때
                task_run = self.get_task_run(task_run_id)
                task_run.point = point
                task_run.completed_score = True
                self.user_point_update(task_run.user_id, point)
            self.db.session.commit()
        return

    def user_point_update(self, user_id, point):
        # 사용자 포인트 갱신
        if user_id is None:
            return
        from pybossa.model.point import Point
        point_row = self.db.session.query(Point).filter(Point.user_id==user_id).first()
        point_row.current_point = point_row.current_point + point
        point_row.point_sum = point_row.point_sum + point
        return


    def get_30days_task_run(self, user_id):
        # 최근 30일 답변
        import datetime
        now = datetime.datetime.now()
        return self.db.session.query(func.count(TaskRun.id).label('count'), func.sum(TaskRun.point).label('point')).filter(
                and_(now.year == extract('year', cast(TaskRun.finish_time, Date)),
                    now.month == extract('month', cast(TaskRun.finish_time, Date)),
                    TaskRun.user_id == user_id)).group_by(TaskRun.user_id).first()


    def get_task_run_present(self, project_id, user_id, task_id):
        return self.db.session.query(TaskRun).filter(TaskRun.project_id == project_id).filter(TaskRun.user_id == user_id).filter(TaskRun.task_id==task_id).first()

    def get_answer_manage(self, project_id, user_id):
        return self.db.session.query(TaskRun).filter(TaskRun.project_id == project_id).filter(TaskRun.user_id == user_id).order_by(TaskRun.finish_time.desc()).first()

    def get_task_run_prev(self, project_id, user_id, finish_time):
        return self.db.session.query(TaskRun).filter(TaskRun.project_id == project_id).filter(TaskRun.user_id == user_id).filter(TaskRun.finish_time<finish_time).order_by(TaskRun.finish_time.desc()).first()
        #return self.db.session.query(TaskRun).filter(TaskRun.project_id == project_id).filter(TaskRun.user_id == user_id).filter(TaskRun.task_id<task_id).order_by(TaskRun.task_id.desc()).first()

    def get_task_run_next(self, project_id, user_id, task_id):
        return self.db.session.query(TaskRun).filter(TaskRun.project_id == project_id).filter(TaskRun.user_id == user_id).filter(TaskRun.task_id>task_id).order_by(TaskRun.task_id).first()

    def redundancy(self, project_id):
        return self.db.session.query(Task).filter_by(project_id = project_id).first()

    # Methods for queries on Task objects
    def get_task(self, id):
        return self.db.session.query(Task).get(id)

    def get_task_by(self, **attributes):
        filters, _, _, _ = self.generate_query_from_keywords(Task, **attributes)
        return self.db.session.query(Task).filter(*filters).first()

    def filter_tasks_by(self, limit=None, offset=0, yielded=False,
                        last_id=None, fulltextsearch=None, desc=False,
                        **filters):

        return self._filter_by(Task, limit, offset, yielded, last_id,
                              fulltextsearch, desc, **filters)

    def count_tasks_with(self, **filters):
        query_args, _, _, _  = self.generate_query_from_keywords(Task, **filters)
        return self.db.session.query(Task).filter(*query_args).count()

    def filter_tasks_by_user_favorites(self, uid, **filters):
        """Return tasks marked as favorited by user.id."""
        query = self.db.session.query(Task).filter(Task.fav_user_ids.any(uid))
        limit = filters.get('limit', 20)
        offset = filters.get('offset', 0)
        last_id = filters.get('last_id', None)
        desc = filters.get('desc', False)
        orderby = filters.get('orderby', 'id')
        if last_id:
            query = query.filter(Task.id > last_id)
        query = self._set_orderby_desc(query, Task, limit,
                                       last_id, offset,
                                       desc, orderby)
        return query.all()

    def get_task_favorited(self, uid, task_id):
        """Return task marked as favorited by user.id."""
        tasks = self.db.session.query(Task)\
                    .filter(Task.fav_user_ids.any(uid), 
                            Task.id==task_id)\
                    .all()
        return tasks

    # Methods for queries on TaskRun objects
    def get_task_run(self, id):
        return self.db.session.query(TaskRun).get(id)

    def get_task_run_by(self, fulltextsearch=None, **attributes):
        filters, _, _, _  = self.generate_query_from_keywords(TaskRun,
                                                    fulltextsearch,
                                                    **attributes)
        return self.db.session.query(TaskRun).filter(*filters).first()

    def filter_task_runs_by(self, limit=None, offset=0, last_id=None,
                            yielded=False, fulltextsearch=None,
                            desc=False, **filters):
        return self._filter_by(TaskRun, limit, offset, yielded, last_id,
                              fulltextsearch, desc, **filters)


    def count_task_runs_with(self, **filters):
        query_args, _, _, _ = self.generate_query_from_keywords(TaskRun, **filters)
        return self.db.session.query(TaskRun).filter(*query_args).count()


    # Methods for saving, deleting and updating both Task and TaskRun objects
    def save(self, element):
        self._validate_can_be('saved', element)
        try:
            self.db.session.add(element)
            self.db.session.commit()
            cached_projects.clean_project(element.project_id)
        except IntegrityError as e:
            self.db.session.rollback()
            raise DBIntegrityError(e)

    def update(self, element):
        self._validate_can_be('updated', element)
        try:
            self.db.session.merge(element)
            self.db.session.commit()
            cached_projects.clean_project(element.project_id)
        except IntegrityError as e:
            self.db.session.rollback()
            raise DBIntegrityError(e)

    def delete(self, element):
        self._delete(element)
        project = element.project
        self.db.session.commit()
        cached_projects.clean_project(element.project_id)
        self._delete_zip_files_from_store(project)

    def delete_valid_from_project(self, project):
        """Delete only tasks that have no results associated."""
        sql = text('''
                   DELETE FROM task WHERE task.project_id=:project_id
                   AND task.id NOT IN
                   (SELECT task_id FROM result
                   WHERE result.project_id=:project_id GROUP BY result.task_id);
                   ''')
        self.db.session.execute(sql, dict(project_id=project.id))
        self.db.session.commit()
        cached_projects.clean_project(project.id)
        self._delete_zip_files_from_store(project)

    def delete_taskruns_from_project(self, project):
        sql = text('''
                   DELETE FROM task_run WHERE project_id=:project_id;
                   ''')
        self.db.session.execute(sql, dict(project_id=project.id))
        self.db.session.commit()
        cached_projects.clean_project(project.id)
        self._delete_zip_files_from_store(project)

    def update_tasks_redundancy(self, project, n_answer):
        """update the n_answer of every task from a project and their state.
        Use raw SQL for performance"""
        sql = text('''
                   UPDATE task SET n_answers=:n_answers,
                   state='ongoing' WHERE project_id=:project_id''')
        self.db.session.execute(sql, dict(n_answers=n_answer, project_id=project.id))
        # Update task.state according to their new n_answers value
        sql = text('''
                   WITH project_tasks AS (
                   SELECT task.id, task.n_answers,
                   COUNT(task_run.id) AS n_task_runs, task.state
                   FROM task, task_run
                   WHERE task_run.task_id=task.id AND task.project_id=:project_id
                   GROUP BY task.id)
                   UPDATE task SET state='completed'
                   FROM project_tasks
                   WHERE (project_tasks.n_task_runs >=:n_answers)
                   and project_tasks.id=task.id
                   ''')
        self.db.session.execute(sql, dict(n_answers=n_answer, project_id=project.id))
        self.db.session.commit()
        cached_projects.clean_project(project.id)

    def _validate_can_be(self, action, element):
        if not isinstance(element, Task) and not isinstance(element, TaskRun):
            name = element.__class__.__name__
            msg = '%s cannot be %s by %s' % (name, action, self.__class__.__name__)
            raise WrongObjectError(msg)

    def _delete(self, element):
        self._validate_can_be('deleted', element)
        table = element.__class__
        inst = self.db.session.query(table).filter(table.id==element.id).first()
        self.db.session.delete(inst)

    def _delete_zip_files_from_store(self, project):
        from pybossa.core import json_exporter, csv_exporter
        global uploader
        if uploader is None:
            from pybossa.core import uploader
        json_tasks_filename = json_exporter.download_name(project, 'task')
        csv_tasks_filename = csv_exporter.download_name(project, 'task')
        json_taskruns_filename = json_exporter.download_name(project, 'task_run')
        csv_taskruns_filename = csv_exporter.download_name(project, 'task_run')

        QnA_filename = json_exporter.download_name(project, 'QnA')

        container = "user_%s" % project.owner_id
        uploader.delete_file(json_tasks_filename, container)
        uploader.delete_file(csv_tasks_filename, container)
        uploader.delete_file(json_taskruns_filename, container)
        uploader.delete_file(csv_taskruns_filename, container)
        uploader.delete_file(QnA_filename, container)

    def get_all_info(self):
        return self.db.session.query(Task.info).filter(Task.id > 175000).all()



    def get_all_info2(self):
        result = self.db.session.query(Task).filter(Task.id > 209728)
        results = result.all()
        print ("result : ")
        print (result)
        print ("results : ")
        print (results)
        print ("type")
        print ("result | results")
        print (str(type(result))+" | "+str(type(results)))
        print ("len : " + str(len(results)))
        return results


    def get_all_info3(self):
        return self.db.session.query(Task.info).all()

    def ttest(self):
        from pybossa.model.user import User
        from sqlalchemy import and_
        result = self.db.session.query(TaskRun.user_id, User.name).filter(and_(
                TaskRun.project_id == 78, User.id == TaskRun.user_id)).group_by(TaskRun.user_id,User.name)
        print (result)
        for i in result.all():
            print (i)
        return

    def get_QnA_data(self, project_id):
        sql = '''
              SELECT JSON_BUILD_OBJECT('question', t.info, 'answers', json_agg(
              json_build_object('user_id', r.user_id,'answer', r.info, 'task_run_id', r.id))) AS data
              FROM task t, task_run r WHERE t.id=r.task_id AND t.project_id=:project_id
              GROUP BY t.id ORDER BY t.id;
              '''
        results = self.db.session.execute(sql, dict(project_id=project_id))
        tmp = []
        for row in results:
            tmp.append(row.data)
        return tmp
