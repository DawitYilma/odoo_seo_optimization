from datetime import datetime, timedelta
from odoo import tools, models, fields, api, _
from odoo.http import request
from odoo.osv import expression


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    def _add_tracking(self, domain, website_track_values):
        """ Add the track and update the visitor"""
        url = request.httprequest.url
        enviro = request.httprequest.environ['HTTP_USER_AGENT']
        domain = expression.AND([domain, [('visitor_id', '=', self.id)]])
        last_view = self.env['website.track'].sudo().search(domain, limit=1)
        if not last_view or last_view.visit_datetime < datetime.now() - timedelta(minutes=30):
            website_track_values['visitor_id'] = self.id
            website_track_values['source'] = enviro
            print(website_track_values)
            tra = self.env['website.track'].create(website_track_values)
            track = self.sudo().env['link.tracker.click'].search(
                [('link_id.redirected_url', '=', url),
                 ('clicked_datetime', '=', website_track_values['visit_datetime'])])
            track.write({
                'web_visitor': self.id,
                'web_track ': tra.id
            })
            tra.write({
                'link_tracker_click': track.id
            })
        self._update_visitor_last_visit()

    def _create_visitor(self):
        """ Create a visitor. Tracking is added after the visitor has been created."""
        country_code = request.session.get('geoip', {}).get('country_code', False)
        country_id = request.env['res.country'].sudo().search([('code', '=', country_code)], limit=1).id if country_code else False
        vals = {
            'lang_id': request.lang.id,
            'country_id': country_id,
            'website_id': request.website.id,
        }

        tz = self._get_visitor_timezone()
        if tz:
            vals['timezone'] = tz

        if not self.env.user._is_public():
            vals['partner_id'] = self.env.user.partner_id.id
            vals['name'] = self.env.user.partner_id.name

        visit = self.sudo().create(vals)
        print(vals, ' VAL', visit.visitor_page_count)
        return visit


class WebsiteTracker(models.Model):
    _inherit = 'website.track'

    link_tracker_click = fields.Many2one('link.tracker.click', 'Link Tracked')
    source = fields.Char('Source')

    def compute_link_tracker(self):
        for rec in self:
            track = self.sudo().env['link.tracker.click'].search(
                [
                 ('web_visitor', '=', rec.visitor_id.id)])
            for lead in track:
                rec.link_tracker_click = lead
                break

        return {
            'link_tracker_click': self.link_tracker_click
        }



