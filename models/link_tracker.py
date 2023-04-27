
from odoo import tools, models, fields, api, _


class LinkTrackerClick(models.Model):
    _inherit = "link.tracker.click"

    web_visitor = fields.Many2one('website.visitor', 'Website Visitor')
    web_track = fields.Many2one('website.track', 'Website Track')
    clicked_datetime = fields.Datetime('Clicked Time', default=fields.Datetime.now, readonly=True)

        