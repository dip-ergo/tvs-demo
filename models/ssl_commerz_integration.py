# -*- coding: utf-'8' "-*-"

import base64

import logging
from urllib.parse import urljoin
import werkzeug
from werkzeug import urls
import urllib.request
import json
import requests
from uuid import uuid4
from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.ergo_ssl_commerz.controllers.ssl_commerz_controllers import SSLCommerzController
from odoo.tools.float_utils import float_compare
import pprint
from decimal import Decimal

_logger = logging.getLogger(__name__)


class PaymentAcquirerSSLCommerz(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('sslcommerz', 'SSL-Commerz')])
    sslcommerz_store_id = fields.Char('Store ID', required_if_provider='sslcommerz')
    sslcommerz_store_passwd = fields.Char('Store Pasword')
    # moneris_use_ipn = fields.Boolean('Use IPN', default=True, help='Moneris Instant Payment Notification')
    # # Server 2 server
    # moneris_api_enabled = fields.Boolean('Use Rest API')
    # moneris_api_username = fields.Char('Rest API Username')
    # moneris_api_password = fields.Char('Rest API Password')
    # moneris_api_access_token = fields.Char('Access Token')
    # moneris_api_access_token_validity = fields.Datetime('Access Token Validity')


    # fees_active = fields.Boolean(default=False)
    # moneris_api_enabled = fields.Boolean(default=False)

    # fees_dom_fixed = fields.Float(default=0.35)
    # fees_dom_var = fields.Float(default=3.4)
    # fees_int_fixed = fields.Float(default=0.35)
    # fees_int_var = fields.Float(default=3.9)

    def _get_sslcommerz_urls(self, environment):
        """ SSLCommerz URLS """
        # sslcommerz_gatewaypage_url = ''
        # if not sslcommerz_gatewaypage_url:
        #     sslcommerz_gatewaypage_url = self.sslcommerz_set_gateway_page_url()
            
        if environment == 'prod':
            return {
                'sslcommerz_session_url':       'https://securepay.sslcommerz.com/gwprocess/v4/api.php',
                'sslcommerz_validation_url':    'https://securepay.sslcommerz.com/validator/api/validationserverAPI.php',
            }
        else:
            return {
                'sslcommerz_session_url':       'https://sandbox.sslcommerz.com/gwprocess/v4/api.php',
                # 'sslcommerz_gatewaypage_url' :   sslcommerz_gatewaypage_url,
                'sslcommerz_validation_url':    'https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php',
            }

    def sslcommerz_form_generate_values(self, values):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # print('values ===> ', values)
        sslcommerz_tx_values = dict(values)
        # sslcommerz_tx_final_values = dict(values)
        sslcommerz_tx_values.update({
            'store_passwd': str(self.sslcommerz_store_passwd),
            # 'business': self.moneris_email_account,
            'store_id': str(self.sslcommerz_store_id),
            'product_category': 'clothing',
            'total_amount': values['amount'],
            'currency': values['currency'].name,     #   and values['currency'].name or '',
            'tran_id': str(uuid4()),
            'cus_city': values.get('partner_city'),
            'cus_country': values.get('partner_country').name, # and values.get('partner_country').code or '',
            'cus_state': values.get('partner_state').name or '',
            # and (
                        # values.get('partner_state').code or values.get('partner_state').name) or '',
            'cus_add1': values.get('partner_address'),
            'cus_email': values.get('partner_email'),
            'cus_postcode': values.get('partner_zip'),
            'cus_name': values.get('partner_first_name') + ' ' + values.get('partner_last_name'),
            'cus_phone': values.get('partner_phone'),
            'ipn_url': urls.url_join(base_url, SSLCommerzController._ipn_url),
            'success_url': urls.url_join(base_url, SSLCommerzController._success_url),
            'cancel_url': urls.url_join(base_url, SSLCommerzController._cancel_url),
            'fail_url': urls.url_join(base_url, SSLCommerzController._fail_url),
            # 'handling': '%.2f' % sslcommerz_tx_values.pop('fees', 0.0) if self.fees_active else False,
            # 'custom': json.dumps({'return_url': '%s' % sslcommerz_tx_values.pop('return_url')}) 
            #     if sslcommerz_tx_values.get('return_url') else False,
            'emi_option' : 0,
            'shipping_method' : 'No',
            'num_of_item' :  1,
            'product_name' : 'test',
            'product_profile' : 'general',

        })

        response_sslc = requests.post(self._get_sslcommerz_urls('test')['sslcommerz_session_url'], sslcommerz_tx_values)
        response_data = {}

        if response_sslc.status_code == 200:
            response_json = json.loads(response_sslc.text)
            if response_json['status'] == 'FAILED':
                response_data['status'] = response_json['status']
                response_data['failedreason'] = response_json['failedreason']
                # return response_data

            response_data['status'] = response_json['status']
            response_data['sessionkey'] = response_json['sessionkey']
            response_data['GatewayPageURL'] = response_json['GatewayPageURL']
            # return response_data

        else:
            response_json = json.loads(response_sslc.text)
            response_data['status'] = response_json['status']
            response_data['failedreason'] = response_json['failedreason']
            # return response_data
        
        print('response_json =====> ', response_json)
        print('response_data =====>', response_data)
        # print(type(sslcommerz_tx_values['total_amount']))
        # pprint.pprint(sslcommerz_tx_values)
        # sslcommerz_tx_final_values.update({ 'tx_url' : response_data['GatewayPageURL'] })
        # self.sslcommerz_set_gateway_page_url(response_data['GatewayPageURL'])
        # pprint.pprint(sslcommerz_tx_values)
        return sslcommerz_tx_values

    def sslcommerz_set_gateway_page_url(self, GatewayPageURL):
        self.ensure_one()
        return GatewayPageURL
        # return self._get_sslcommerz_urls(environment)['sslcommerz_session_url']

    def sslcommerz_get_form_action_url(self):
        self.ensure_one()
        environment = 'prod' if self.state == 'enabled' else 'test'
        # return self._get_sslcommerz_urls(environment)['sslcommerz_gatewaypage_url']
        return self._get_sslcommerz_urls(environment)['sslcommerz_session_url']


class TxSslcommerz(models.Model):
    _inherit = 'payment.transaction'

    sslcommerz_txn_type = fields.Char('Transaction type')

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _sslcommerz_form_get_tx_from_data(self, data):
        print('_sslcommerz_form_get_tx_from_data')
        print('_sslcommerz_form_get_tx_from_data data =====> ', data)
        GatewayPageURL = data.get('GatewayPageURL')
        if not GatewayPageURL:
            error_msg = _('Sslcommerz: received data with missing GatewayPageURL (%s)') % (GatewayPageURL)
            #_logger.info(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use txn_id ?
        txs = self.env['payment.transaction'].search([('reference', '=', GatewayPageURL)])
        if not txs or len(txs) > 1:
            error_msg = 'Sslcommerz: received data for reference %s' % (GatewayPageURL)
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        _logger.info(txs[0])
        return txs[0]

    def _sslcommerz_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        print('_sslcommerz_form_get_invalid_parameters')
        print('_sslcommerz_form_get_invalid_parameters data ======> ', data)
        """
        if data.get('notify_version')[0] != '3.4':
            _logger.warning(
                'Received a notification from Moneris with version %s instead of 2.6. This could lead to issues when managing it.' %
                data.get('notify_version')
            )
        if data.get('test_ipn'):
            _logger.warning(
                'Received a notification from Moneris using sandbox'
            ),
        """
        # TODO: txn_id: shoudl be false at draft, set afterwards, and verified with txn details
        if self.acquirer_reference and data.get('response_order_id') != self.acquirer_reference:
            invalid_parameters.append(('response_order_id', data.get('response_order_id'), self.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('charge_total', '0.0')), (self.amount), 2) != 0:
            invalid_parameters.append(('charge_total', data.get('charge_total'), '%.2f' % self.amount))
        """
        if data.get('mc_currency') != tx.currency_id.name:
            invalid_parameters.append(('mc_currency', data.get('mc_currency'), tx.currency_id.name))
        """
        """
        if 'handling_amount' in data and float_compare(float(data.get('handling_amount')), tx.fees, 2) != 0:
            invalid_parameters.append(('handling_amount', data.get('handling_amount'), tx.fees))
        """
        # check buyer
        """
        if tx.partner_reference and data.get('payer_id') != tx.partner_reference:
            invalid_parameters.append(('payer_id', data.get('payer_id'), tx.partner_reference))
        """
        # check seller
        '''
        if data.get('rvarid') != tx.acquirer_id.moneris_email_account:
            invalid_parameters.append(('rvarid', data.get('rvarid'), tx.acquirer_id.moneris_email_account))
        if data.get('rvarkey') != tx.acquirer_id.moneris_seller_account:
            invalid_parameters.append(('rvarkey', data.get('rvarkey'), tx.acquirer_id.moneris_seller_account))
        '''

        return invalid_parameters

    def _sslcommerz_form_validate(self, data):
        print('_sslcommerz_form_validate')
        print('_sslcommerz_form_validate data ======> ', data)
        status = data.get('result')
        _logger.info("-----------------form -----validate----------------------")
        _logger.info(status)
        if status == '1':
            _logger.info('Validated Sslcommerz payment for tx %s: set as done' % (self.reference))
            data.update(state='done', date_validate=data.get('date_stamp', fields.datetime.now()))
            #_logger.info("---form validate----------------------")
            return self.sudo().write(data)
        else:
            error = 'Received unrecognized status for Sslcommerz payment %s: %s, set as error' % (self.reference, status)
            #_logger.info(error)
            data.update(state='error', state_message=error)
            return self.sudo().write(data)

    def _sslcommerz_form_feedback(self, data):
        print('==== data ==========', data)

    def render_sale_button(self, order, submit_txt=None, render_values=None):
        values = {
            'partner_id': order.partner_id.id,
        }
        if render_values:
            values.update(render_values)
        # Not very elegant to do that here but no choice regarding the design.
        self._log_payment_transaction_sent()
        if self.acquirer_id.id == 14:
            return self.acquirer_id.with_context(submit_class='btn btn-primary', submit_txt=submit_txt or _('Pay Now')).sudo().render(
                self.reference,
                order.amount_total,
                order.pricelist_id.currency_id.id,
                values=values,
            )

    # --------------------------------------------------
    # SERVER2SERVER RELATED METHODS
    # --------------------------------------------------

    # def _sslcommerz_try_url(self, request, tries=3, context=None):
    #     """ Try to contact SSLCommerz. Due to some issues, internal service errors
    #     seem to be quite frequent. Several tries are done before considering
    #     the communication as failed.

    #      .. versionadded:: pre-v8 saas-3
    #      .. warning::

    #         Experimental code. You should not use it before OpenERP v8 official
    #         release.
    #     """
    #     done, res = False, None
    #     while (not done and tries):
    #         try:
    #             res = urllib.request.urlopen(request)
    #             done = True
    #         except urllib.request.HTTPError as e:
    #             res = e.read()
    #             e.close()
    #             if tries and res and json.loads(res)['name'] == 'INTERNAL_SERVICE_ERROR':
    #                 _logger.warning('Failed contacting SSLcommerz, retrying (%s remaining)' % tries)
    #         tries = tries - 1
    #     if not res:
    #         pass
    #         # raise openerp.exceptions.
    #     result = res.read()
    #     res.close()
    #     return result
