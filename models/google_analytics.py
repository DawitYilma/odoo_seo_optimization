import pandas as pd
from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

import json
from odoo.modules.module import get_module_resource

from odoo import tools, models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError
from datetime import datetime


class GoogleAnalyticsAuthentication(models.Model):
    _name = "google.analytics.auth"

    name = fields.Many2one('website', string="Website")
    key_file_location = fields.Char('KEY_FILE_NAME')
    view_id = fields.Char('View Id')
    selected_auth = fields.Boolean('Authentication Used')


class GoogleAnalyticsReport(models.Model):
    _name = "google.analytics.report"

    name = fields.Char('Client Id')
    key_file_location = fields.Char('KEY_FILE_NAME')
    view_id = fields.Char('View Id')
    country = fields.Char('Country')
    google_analytics_report_ids = fields.One2many('google.analytics.report.line', 'google_analytics')

    def initialize_analyticsreporting(self, auth_fil):
        SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
        json_file_path = get_module_resource('seo_optimization', 'static/json/', f'{auth_fil.key_file_location}')

        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            json_file_path, SCOPES)
        analytics = build('analyticsreporting', 'v4', credentials=credentials)
        return analytics

    # Get one report page
    def get_report(self,analytics, pageTokenVar,auth_fil):
        return analytics.reports().batchGet(
            body={
                'reportRequests': [
                    {
                        'viewId': auth_fil.view_id,
                        'dateRanges': [{'startDate': '100daysAgo', 'endDate': 'today'}],
                        'metrics': [{'expression': 'ga:pageviews'}],
                        'dimensions': [{'name': 'ga:pagePath'}, {"name": "ga:clientId"}, {"name": "ga:country"}],
                        'pageSize': 10000,
                        'pageToken': pageTokenVar,
                        'samplingLevel': 'LARGE'
                    }]
            }
        ).execute()

    # get user information
    def get_user(self,analytics, pageTokenVar, unique_clients,auth_fil):
        clients = {}
        for i in unique_clients:
            body = {
                "viewId": auth_fil.view_id,
                "user": {
                    "type": "CLIENT_ID",
                    "userId": f"{i}"
                },
                "dateRange": {'startDate': '100daysAgo', 'endDate': 'today'},
            }
            clients[i] = analytics.userActivity().search(body=body).execute()
        return clients

    def handle_report(self, analytics, pagetoken, rows, auth_fil):
        response = self.get_report(analytics, pagetoken, auth_fil)

        # Header, Dimentions Headers, Metric Headers

        columnHeader = response.get("reports")[0].get('columnHeader', {})
        dimensionHeaders = columnHeader.get('dimensions', [])
        metricHeaders = columnHeader.get('metricHeader', {}).get('metricHeaderEntries', [])

        # Pagination
        pagetoken = response.get("reports")[0].get('nextPageToken', None)

        # Rows
        rowsNew = response.get("reports")[0].get('data', {}).get('rows', [])
        rows = rows + rowsNew
        client_ids = []
        for i in range(len(rows)):
            client_ids.append(str(rows[i]['dimensions'][1]))

        unique_clients = set(client_ids)
        list_clients = list(unique_clients)

        users = self.get_user(analytics, pagetoken, client_ids,auth_fil)
        for y in range(len(client_ids)):
            user_val = {}

            for i in range(len(users[client_ids[y]]['sessions'])):
                report = self.env['google.analytics.report'].search([('id', '>', 0)])
                for rep in report:
                    user_val = {'google_analytics': rep.id}
                    user_val['name'] = client_ids[y]
                    user_val['website'] = auth_fil.name.id
                    user_val['session_id'] = users[client_ids[y]]['sessions'][i]['sessionId']
                    user_val['device_category'] = users[client_ids[y]]['sessions'][i]['deviceCategory']
                    user_val['platform'] = users[client_ids[y]]['sessions'][i]['platform']
                    user_val['data_source'] = users[client_ids[y]]['sessions'][i]['dataSource']

                    for z in range(len(users[client_ids[y]]['sessions'][i]['activities'])):
                        rep_1 = users[client_ids[y]]['sessions'][i]['activities'][z]['activityTime'].replace('T', ' ')
                        rep_2 = rep_1.replace('Z', '')
                        user_val['activity_time'] = datetime.strptime(rep_2, '%Y-%m-%d %H:%M:%S.%f')
                        user_val['source'] = users[client_ids[y]]['sessions'][i]['activities'][z]['source']
                        user_val['medium'] = users[client_ids[y]]['sessions'][i]['activities'][z]['medium']
                        user_val['campaign'] = users[client_ids[y]]['sessions'][i]['activities'][z]['campaign']
                        user_val['keyword'] = users[client_ids[y]]['sessions'][i]['activities'][z]['keyword']
                        user_val['hostname'] = users[client_ids[y]]['sessions'][i]['activities'][z]['hostname']
                        user_val['landing_page_path'] = users[client_ids[y]]['sessions'][i]['activities'][z]['landingPagePath']
                        if users[client_ids[y]]['sessions'][i]['activities'][z]['activityType'] == 'PAGEVIEW':
                            user_val['page_path'] = users[client_ids[y]]['sessions'][i]['activities'][z]['pageview']['pagePath']
                            user_val['page_title'] = users[client_ids[y]]['sessions'][i]['activities'][z]['pageview']['pageTitle']
                        report_ids = self.env['google.analytics.report.line'].search([('name', '=', rep.name),
                                                                                      ('session_id', '=', user_val['session_id']),
                                                                                      ('activity_time', '=', user_val['activity_time']),
                                                                                      ('device_category', '=', user_val['device_category'])])

                        print(report_ids)
                        if user_val['name'] == rep.name and not report_ids:

                            self.google_analytics_report_ids.create(user_val)

            user_val.clear()

        # Recursivly query next page
        if pagetoken != None:
            return self.handle_report(analytics, pagetoken, rows, auth_fil)

        return response

    # Start
    def run_analysis(self):
        auth_fil = self.env['google.analytics.auth'].search([('selected_auth', '=', True)])
        for z in range(2):
            for rec in auth_fil:
                analytics = self.initialize_analyticsreporting(rec)
                rows = []
                rows = self.handle_report(analytics, '0', rows, rec)
                for i in range(len(rows['reports'])):
                    if rows['reports'][i]['data'].get("rows") is not None:
                        for y in range(len(rows['reports'][i]['data']['rows'])):
                            uniq_val = self.env['google.analytics.report'].search([('name', '=', rows['reports'][i]['data']['rows'][y]['dimensions'][1])])
                            if not uniq_val:
                                self.env['google.analytics.report'].create({
                                    'name': rows['reports'][i]['data']['rows'][y]['dimensions'][1],
                                    'country': rows['reports'][i]['data']['rows'][y]['dimensions'][2],
                                    'view_id': rec.view_id,
                                    'key_file_location': rec.key_file_location,
                                })


class GoogleAnalyticsReportLine(models.Model):
    _name = "google.analytics.report.line"
    _order = "activity_time desc"

    name = fields.Char('Client Id')
    website = fields.Many2one('website', string="Website")
    google_analytics = fields.Many2one('google.analytics.report', 'Google Analytics Report')
    session_id = fields.Char('Session Id')
    device_category = fields.Char('Device Category')
    platform = fields.Char('Platform')
    data_source = fields.Char('Data Source')
    activity_time = fields.Datetime('Visit Date', required=True, readonly=True)
    source = fields.Char('Source')
    medium = fields.Char('Medium')
    campaign = fields.Char('Campaign')
    keyword = fields.Char('Keyword')
    hostname = fields.Char('Hostname')
    landing_page_path = fields.Char('Landing Page Path')
    page_path = fields.Char('Page Path')
    page_title = fields.Char('Page Title')

