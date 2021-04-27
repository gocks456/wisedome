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
from sqlalchemy import cast, Date, or_, func, and_

from pybossa.repositories import Repository
from pybossa.model.project import Project
from pybossa.model.category import Category
from pybossa.exc import WrongObjectError, DBIntegrityError
from pybossa.cache import projects as cached_projects
from pybossa.core import uploader


class ProjectRepository(Repository):

    # 마감 임박 프로젝트 업데이트(7일 이내 프로젝트)
    def update_end_date_7days(self):
        from datetime import datetime, timedelta
        time = datetime.now()
        after_7days = time + timedelta(days=7)

        # featured True
        self.db.session.query(Project).filter(and_(time <= cast(Project.end_date, Date),
                                                   after_7days >= cast(Project.end_date, Date),
                                                   Project.published == True)).update({'featured': True}, synchronize_session='fetch')
        
        # 마감
        self.db.session.query(Project).filter(and_(
                time>cast(Project.end_date, Date), Project.complete==False)).update({'published':False}, synchronize_session='fetch')

        print("마감 작업 테스트 중")

        self.db.session.commit()
        return


    # 공개된 프로젝트 수
    def get_count_published_projects(self):
        return self.db.session.query(func.count(Project.id).label('count')).filter(
                 and_(Project.published==True, Project.complete==False)).one()

    
    # 프로필 / 최근 참여한 프로젝트 top 10
    def get_contributed_projects_top10(self, user_id):
        from pybossa.model.project_stats import ProjectStats
        from pybossa.model.task_run import TaskRun
        return self.db.session.query(Project.name, ProjectStats.overall_progress, Project.short_name,
                func.sum(TaskRun.point).label('point'), func.max(TaskRun.finish_time).label('time')).filter(
                        and_(Project.id==ProjectStats.project_id,
                            Project.id==TaskRun.project_id,
                            TaskRun.user_id==user_id)).group_by(Project.id, ProjectStats.overall_progress, TaskRun.project_id).order_by(func.max(TaskRun.finish_time).desc()).limit(10).all()


    # 대시보드 / 참여한 프로젝트 (종료된 프로젝트 X)
    def get_contributed_projects_all(self, user_id):
        from pybossa.model.task_run import TaskRun
        from pybossa.model.category import Category

        return self.db.session.query(Project.name, Project.short_name, Project.description, Project.condition, Project.all_point, 
                            Project.updated, Project.end_date, Project.featured, Project.info, Category.name.label('category_name')).filter(
                        and_(Project.id==TaskRun.project_id, #Project.complete==False, Project.published==True,
                            TaskRun.user_id==user_id, Project.category_id==Category.id)).group_by(
                        Project.id, TaskRun.project_id, Category.id).order_by(Project.end_date).all()

    #20.02.25. 수정사항
    def get_point(self, short_name):
        return self.db.session.query(Project).filter_by(short_name=short_name).all()

    def search_by_name(self, keyword):
        if len(keyword) == 0:
            return []
        keyword = '%' + keyword.lower() + '%'
        return self.db.session.query(Project).filter(or_(func.lower(Project.name).like(keyword),
                                  func.lower(Project.name).like(keyword))).all()

    # Methods for Project objects
    def get(self, id):
        return self.db.session.query(Project).get(id)

    def get_by_shortname(self, short_name):
        return self.db.session.query(Project).filter_by(short_name=short_name).first()

    def get_by(self, **attributes):
        return self.db.session.query(Project).filter_by(**attributes).first()

    def get_all(self):
        return self.db.session.query(Project).all()

    def filter_by(self, limit=None, offset=0, yielded=False, last_id=None,
                  fulltextsearch=None, desc=False, **filters):
        if filters.get('owner_id'):
            filters['owner_id'] = filters.get('owner_id')
        return self._filter_by(Project, limit, offset, yielded, last_id,
                               fulltextsearch, desc, **filters)

    def save(self, project):
        self._validate_can_be('saved', project)
        self._empty_strings_to_none(project)
        self._creator_is_owner(project)
        try:
            self.db.session.add(project)
            self.db.session.commit()
        except IntegrityError as e:
            self.db.session.rollback()
            raise DBIntegrityError(e)

    def update(self, project):
        self._validate_can_be('updated', project)
        self._empty_strings_to_none(project)
        self._creator_is_owner(project)
        try:
            self.db.session.merge(project)
            self.db.session.commit()
        except IntegrityError as e:
            self.db.session.rollback()
            raise DBIntegrityError(e)

    def delete(self, project):
        self._validate_can_be('deleted', project)
        project = self.db.session.query(Project).filter(Project.id==project.id).first()
        self.db.session.delete(project)
        self.db.session.commit()
        cached_projects.clean(project.id)
        self._delete_zip_files_from_store(project)


    # Methods for Category objects
    def get_category(self, id=None):
        if id is None:
            return self.db.session.query(Category).first()
        return self.db.session.query(Category).get(id)

    def get_category_by(self, **attributes):
        return self.db.session.query(Category).filter_by(**attributes).first()

    def get_all_categories(self):
        return self.db.session.query(Category).all()

    def filter_categories_by(self, limit=None, offset=0, yielded=False,
                             last_id=None, fulltextsearch=None,
                             orderby='id',
                             desc=False, **filters):
        if filters.get('owner_id'):
            del filters['owner_id']
        return self._filter_by(Category, limit, offset, yielded, last_id,
                               fulltextsearch, desc, orderby, **filters)

    def save_category(self, category):
        self._validate_can_be('saved as a Category', category, klass=Category)
        try:
            self.db.session.add(category)
            self.db.session.commit()
        except IntegrityError as e:
            self.db.session.rollback()
            raise DBIntegrityError(e)

    def update_category(self, new_category, caller="web"):
        self._validate_can_be('updated as a Category', new_category, klass=Category)
        try:
            self.db.session.merge(new_category)
            self.db.session.commit()
        except IntegrityError as e:
            self.db.session.rollback()
            raise DBIntegrityError(e)

    def delete_category(self, category):
        self._validate_can_be('deleted as a Category', category, klass=Category)
        self.db.session.query(Category).filter(Category.id==category.id).delete()
        self.db.session.commit()

    def _empty_strings_to_none(self, project):
        if project.name == '':
            project.name = None
        if project.short_name == '':
            project.short_name = None
        if project.description == '':
            project.description = None

    def _creator_is_owner(self, project):
        if project.owners_ids is None:
            project.owners_ids = []
        if project.owner_id not in project.owners_ids:
            project.owners_ids.append(project.owner_id)

    def _validate_can_be(self, action, element, klass=Project):
        if not isinstance(element, klass):
            name = element.__class__.__name__
            msg = '%s cannot be %s by %s' % (name, action, self.__class__.__name__)
            raise WrongObjectError(msg)

    def _delete_zip_files_from_store(self, project):
        from pybossa.core import json_exporter, csv_exporter
        global uploader
        if uploader is None:
            from pybossa.core import uploader
        json_tasks_filename = json_exporter.download_name(project, 'task')
        csv_tasks_filename = csv_exporter.download_name(project, 'task')
        json_taskruns_filename = json_exporter.download_name(project, 'task_run')
        csv_taskruns_filename = csv_exporter.download_name(project, 'task_run')
        container = "user_%s" % project.owner_id
        uploader.delete_file(json_tasks_filename, container)
        uploader.delete_file(csv_tasks_filename, container)
        uploader.delete_file(json_taskruns_filename, container)
        uploader.delete_file(csv_taskruns_filename, container)
