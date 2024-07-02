# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint
from frappe.utils.password import get_decrypted_password
import requests
import json
import urllib.parse

class new_issue_object:
    # See https://docs.gitlab.com/ee/api/issues.html#new-issue

    def __init__(self):
        id=0 # Required
        title='' # Required
        assignee_id=0
        assignee_ids=[] # Premium and Ultimate only
        confidential=False
        created_at=''
        description=''
        discussion_to_resolve=''
        due_date=''
        epic_id=0 # Premium and Ultimate only
        epic_iid=0 # Deprecated
        iid=0
        issue_type=''
        labels=''
        merge_request_to_resolve_discussions_of=0
        milestone_id=0
        weight=0 # Premium and Ultimate only
    
    def toJSON(self):
        return ObjectToJSON(self)

    def toURL(self):
        return ObjectToURL(self)

class edit_issue_object:
    # See https://docs.gitlab.com/ee/api/issues.html#edit-an-issue

    def __init__(self):
        id=0 # Required
        issue_iid=0 # Required
        add_labels=''
        assignee_ids=[]
        confidential=False
        description=''
        discussion_locked=False
        due_date=''
        epic_id=0 # Premium and Ultimate only
        epic_iid=0 # Premium and Ultimate only
        issue_type='issue'
        labels=''
        milestone_id=''
        remove_labels=''
        state_event=''
        title=''
        updated_at=''
        weight=0 # Premium and Ultimate only
    
    def toJSON(self):
        return ObjectToJSON(self)

    def toURL(self):
        return ObjectToURL(self)

class GitLabSettings(Document):
    def check_activation(self):
        if cint(self.enabled) == 1:
            return True
        
        return False
    
    def post_new_issue(self, issue_object):
        if not self.check_activation():
            frappe.throw("GitLab API is disabled")
        
        url = "{0}/api/v4/projects/{1}/issues?{2}".format(self.url, self.project_id, issue_object.toURL())
        secret = get_decrypted_password("GitLab Settings", "GitLab Settings", "private_token", False)
        headers = {
            "PRIVATE-TOKEN": "{0}".format(secret),
            "Content-Type": "application/json; charset=utf-8"
        }
        data = issue_object.toJSON()
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 201:
            return response.json()
        else:
            frappe.log_error(message="{0}\n\n{1}".format(str(response.status_code), str(response.json())) , title="GitLab: Create Issue failed")
            return
    
    def put_edit_issue(self, issue_object):
        if not self.check_activation():
            frappe.throw("GitLab API is disabled")
        
        url = "{0}/api/v4/projects/{1}/issues/{2}?{3}".format(self.url, self.project_id, issue_object.issue_iid, issue_object.toURL())
        secret = get_decrypted_password("GitLab Settings", "GitLab Settings", "private_token", False)
        headers = {
            "PRIVATE-TOKEN": "{0}".format(secret),
            "Content-Type": "application/json; charset=utf-8"
        }
        data = issue_object.toJSON()
        
        response = requests.put(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            frappe.log_error(message="{0}\n\n{1}".format(str(response.status_code), str(response.json())) , title="GitLab: Update Issue failed")
            return

def ObjectToJSON(object):
    return json.dumps(
        object,
        default=lambda x: x.__dict__, 
        sort_keys=True,
        indent=4)

def ObjectToURL(object):
    return urllib.parse.urlencode(object.__dict__)

@frappe.whitelist()
def create_new_issue(**kwargs):
    gitlab_settings = frappe.get_doc("GitLab Settings", "GitLab Settings")
    
    issue_object = new_issue_object()
    issue_object.id = cint(gitlab_settings.project_id)
    issue_object.title = kwargs['title'] if 'title' in kwargs else ''
    issue_object.assignee_id = kwargs['assignee_id'] if 'assignee_id' in kwargs else 0
    issue_object.confidential = kwargs['confidential'] if 'confidential' in kwargs else False
    issue_object.created_at = kwargs['created_at'] if 'created_at' in kwargs else ''
    issue_object.iid = kwargs['iid'] if 'iid' in kwargs else ''
    issue_object.issue_type = kwargs['issue_type'] if 'issue_type' in kwargs else 'issue'
    issue_object.description = kwargs['description'] if 'description' in kwargs else ''
    issue_object.discussion_to_resolve = kwargs['discussion_to_resolve'] if 'discussion_to_resolve' in kwargs else ''
    issue_object.labels = kwargs['labels'] if 'labels' in kwargs else ''
    issue_object.merge_request_to_resolve_discussions_of = kwargs['merge_request_to_resolve_discussions_of'] if 'merge_request_to_resolve_discussions_of' in kwargs else 0
    issue_object.milestone_id = kwargs['milestone_id'] if 'milestone_id' in kwargs else 0
    issue_object.due_date = kwargs['due_date'] if 'due_date' in kwargs else ''
    
    return gitlab_settings.post_new_issue(issue_object)

@frappe.whitelist()
def edit_issue(**kwargs):
    gitlab_settings = frappe.get_doc("GitLab Settings", "GitLab Settings")
    issue_object = edit_issue_object()
    issue_object.id = cint(gitlab_settings.project_id)
    issue_object.issue_iid = kwargs['issue_iid'] if 'issue_iid' in kwargs else frappe.throw("issue_iid missing")

    if 'add_labels' in kwargs:
        issue_object.add_labels = kwargs['add_labels']
    if 'assignee_ids' in kwargs:
        issue_object.assignee_ids = kwargs['assignee_ids']
    if 'confidential' in kwargs:
        issue_object.confidential = kwargs['confidential']
    if 'description' in kwargs:
        issue_object.description = kwargs['description']
    if 'discussion_locked' in kwargs:
        issue_object.discussion_locked = kwargs['discussion_locked']
    if 'epic_id' in kwargs:
        issue_object.epic_id = kwargs['epic_id']
    if 'epic_iid' in kwargs:
        issue_object.epic_iid = kwargs['epic_iid']
    if 'issue_type' in kwargs:
        issue_object.issue_type = kwargs['issue_type']
    if 'labels' in kwargs:
        issue_object.labels = kwargs['labels']
    if 'milestone_id' in kwargs:
        issue_object.milestone_id = kwargs['milestone_id']
    if 'remove_labels' in kwargs:
        issue_object.remove_labels = kwargs['remove_labels']
    if 'state_event' in kwargs:
        issue_object.state_event = kwargs['state_event']
    if 'title' in kwargs:
        issue_object.title = kwargs['title']
    if 'updated_at' in kwargs:
        issue_object.updated_at = kwargs['updated_at']
    if 'weight' in kwargs:
        issue_object.weight = kwargs['weight']
    
    return gitlab_settings.put_edit_issue(issue_object)
