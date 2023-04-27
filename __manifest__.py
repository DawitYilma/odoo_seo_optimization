
{
    'name': 'SEO Optimization',
    'version': '14.0.1.0.0',
    'author': '''Dawit Yilma''',
    'license': "AGPL-3",
    'category': 'Other',
    'summary': 'An SEO Optimization and tracking of website visitors',
    'images': [''],
    'depends': ['website', 'mass_mailing'],
    'data': ["security/ir.model.access.csv",
             'views/link_tracker.xml',
             'views/google_analytics_auth.xml',
             'views/google_analytics.xml',
             'views/website_visitor_view_lead.xml',
             'data/cron.xml',
             ],
    'demo': [],
    'installable': True,
    'application': True
}
