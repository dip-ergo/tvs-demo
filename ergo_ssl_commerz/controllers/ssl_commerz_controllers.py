# -*- coding: utf-8 -*-
import json
import logging
import pprint
import requests
import werkzeug
from werkzeug import urls
import urllib.request
from odoo import http
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.http import request
from odoo import SUPERUSER_ID
from sslcommerz_python.payment import SSLCSession
from decimal import Decimal
from odoo.addons.payment.controllers.portal import PaymentProcessing

def unescape(s):
    s = s.replace("&lt;", "<")
    s = s.replace("&gt;", ">")
    # this has to be last:
    s = s.replace("&amp;", "&")
    s = s.replace("&quot;", "\"")
    return s

_logger = logging.getLogger(__name__)


class SSLCommerzController(http.Controller):
    # _notify_url = '/payment/moneris/ipn/'
    # _return_url = '/payment/moneris/dpn/'
    # _cancel_url = '/payment/moneris/cancel/'
    _success_url = '/payment/sslcommerz/success/'
    _fail_url = '/payment/sslcommerz/fail/'
    _cancel_url = '/payment/sslcommerz/cancel/'
    _ipn_url = '/payment/sslcommerz/ipn/'

    def _get_return_url(self, **post):
        _logger.info('####################### return URL #######################')
        """ Extract the return URL from the data coming from sslcommerz. """
        print(post)
        return_url = post.pop('return_url', '')

        # if not return_url:
        #     t = unescape(post.pop('rvarret', '{}'))
        #     custom = json.loads(t)
        #     return_url = custom.get('return_url', '/')

        if not return_url:
            return_url = '/payment/shop/validate'

        return return_url

    def sslcommerz_validate_data(self, **post):
        """ Moneris IPN: three steps validation to ensure data correctness

         - step 1: return an empty HTTP 200 response -> will be done at the end
           by returning ''
         - step 2: POST the complete, unaltered message back to Moneris (preceded
           by cmd=_notify-validate), with same encoding
         - step 3: moneris send either VERIFIED or INVALID (single word)

        Once data is validated, process it. """
        _logger.info('**************** sslcommerz_validate_data *******************')
        res = False
    
        val_id = post.get('val_id')
        tx = None

        # if val_id:

        #     tx_ids = request.env['payment.transaction'].search([('reference', '=', reference)])

        #     if tx_ids:
        #         tx = request.env['payment.transaction'].browse(tx_ids[0].id)
        
        # if tx:

        sslcommerz_urls = request.env['payment.acquirer']._get_sslcommerz_urls(tx and tx.acquirer_id and tx.acquirer_id.environment or 'prod')
        validate_url = sslcommerz_urls['sslcommerz_validation_url']

        # else:
        #     _logger.warning('Sslcommerz: No order found')
        #     return res
        acquirer_id = request.env['payment.acquirer'].search([('id', '=', 14)])
        store_id = acquirer_id.sslcommerz_store_id
        store_passwd = acquirer_id.sslcommerz_store_passwd
        new_post = dict(store_id=store_id, store_passwd=store_passwd, val_id=val_id)
        urequest = requests.post(validate_url, new_post)
        resp = urequest.text
        # part = resp.split('<br>')
        # new_response = dict([s.split(' = ') for s in part])
        success = post.get('status')
        txn_key = ""
        # try:
        #     if (int(success) < 50 and post.get('result') == '1' and
        #             new_response.get('response_code') is not 'null' and int(new_response.get('response_code')) < 50 and
        #             new_response.get('transactionKey') == post.get('transactionKey') and
        #             new_response.get('order_id') == post.get('response_order_id')
        #         ):
        #         _logger.info('Moneris: validated data')
        #         res = request.env['payment.transaction'].sudo().form_feedback(post, 'moneris')
        #         txn_key = post.get('transactionKey')
        #     else:
        #         res = 'Moneris: answered INVALID on data verification: ' + new_response.get('status') + '/' + post.get('response_order_id')

        # except ValueError:
        #     res = 'Moneris: answered INVALID on data verification: ' + new_response.get('status') + '/' + post.get('response_order_id')

        # if txn_key != "":
        #     res = "status=approved&transactionKey={}".format(txn_key)
        res = ''
        if success:
            res = "status={}".format(success)
        return res

    @http.route('/payment/sslcommerz/ipn/', type='http', auth='none', methods=['POST'], csrf=False)
    def sslcommerz_ipn(self, **post):
        """ sslcommerz ipn """
        _logger.info('****************************** /IPN')
        res = self.sslcommerz_validate_data(**post)

        return werkzeug.utils.redirect('/sslcommerz?{}'.format(res))


    @http.route('/payment/sslcommerz/success', type='http', auth="none", methods=['POST'], csrf=False)
    def sslcommerz_success(self, **post):
        """ sslcommerz Success """
        #_logger.info('Beginning Moneris DPN form_feedback with post data %s', p_logger.info.pformat(post))  # debug
        _logger.info('****************************** /success')
        return_url = self._get_return_url(**post)

        if self.sslcommerz_validate_data(**post):
            return werkzeug.utils.redirect(return_url)
        else:
            return werkzeug.utils.redirect(self._cancel_url)

    @http.route('/payment/sslcommerz/cancel', type='http', auth="none", methods=['POST'], csrf=False)
    def sslcommerz_cancel(self, **post):
        """ When the user cancels its sslcommerz payment: GET on this route """
        _logger.info('****************************** /cancel')
        reference = post.get('rvaroid')
        if reference:
            sales_order_obj = request.env['sale.order']
            so_ids = sales_order_obj.sudo().search([('name', '=', reference)])
            if so_ids:
                '''return_url = '/shop/payment/get_status/' + str(so_ids[0])'''
                so = sales_order_obj.browse(so_ids[0].id)
                if so:
                    '''
                    tx.write({'state': 'cancel'})
                    sale_order_obj.action_cancel(cr, SUPERUSER_ID, [order.id], context=request.context)
                    '''
                    '''
                    tx_ids = request.registry['payment.transaction'].search(cr, uid, [('reference', '=', reference)], context=context)
                    for tx in tx_ids:
                        tx = request.registry['payment.transaction'].browse(cr, uid, tx, context=context)
                        tx.write({'state': 'cancel'})
                    sales_order_obj.write(cr, SUPERUSER_ID, [so.id], {'payment_acquirer_id': None,}, context=context)
                    '''
                    '''
                    action_cancel(cr, SUPERUSER_ID, so.id, context=request.context)
                '''
        msg = "/sslcommerz?status=cancelled&"
        for key, value in post.items():
            msg += str(key)
            msg+= '='
            msg+= str(value)
            msg+='&'
        return werkzeug.utils.redirect(msg)

    # @http.route('/sslcommerz', type='http', auth='public', methods=['GET'], website=True)
    # def sslcommerz_status(self, **get):
    #     _logger.info('****************************** /SSLCOMMERZ')
    #     status = ''
    #     transactionKey = ''
    #     response_code = ''
    #     message = ''
    #     if 'status' in get:
    #         status = get['status']
    #     if 'transactionKey' in get:
    #         transactionKey = get['transactionKey']
    #     if 'response_code' in get:
    #         response_code = get['response_code']
    #     if 'message' in get:
    #         message = get['message']

    #     return request.render('ergo_ssl_commerz.sslcommerz_status', {'status': status, 'transactionKey': transactionKey, 'response_code': response_code, 'message': message})


    # @http.route(['/shop/payment/transaction/',
    #     '/shop/payment/transaction/<int:so_id>',
    #     '/shop/payment/transaction/<int:so_id>/<string:access_token>'], type='json', auth="public", website=True)
    # def payment_transaction(self, acquirer_id, save_token=False, so_id=None, access_token=None, token=None, **kwargs):
    #     """ Json method that creates a payment.transaction, used to create a
    #     transaction when the user clicks on 'pay now' button. After having
    #     created the transaction, the event continues and the user is redirected
    #     to the acquirer website.

    #     :param int acquirer_id: id of a payment.acquirer record. If not set the
    #                             user is redirected to the checkout page
    #     """
    #     print("*******************************************************************")
    #     # Ensure a payment acquirer is selected
    #     if not acquirer_id:
    #         return False

    #     try:
    #         acquirer_id = int(acquirer_id)
    #     except:
    #         return False

    #     # Retrieve the sale order
    #     if so_id:
    #         env = request.env['sale.order']
    #         domain = [('id', '=', so_id)]
    #         if access_token:
    #             env = env.sudo()
    #             domain.append(('access_token', '=', access_token))
    #         order = env.search(domain, limit=1)
    #     else:
    #         order = request.website.sale_get_order()

    #     # Ensure there is something to proceed
    #     if not order or (order and not order.order_line):
    #         return False

    #     assert order.partner_id.id != request.website.partner_id.id

    #     # Create transaction
    #     vals = {'acquirer_id': acquirer_id,
    #             'return_url': '/shop/payment/validate'}

    #     if save_token:
    #         vals['type'] = 'form_save'
    #     if token:
    #         vals['payment_token_id'] = int(token)

    #     transaction = order._create_payment_transaction(vals)

    #     # store the new transaction into the transaction list and if there's an old one, we remove it
    #     # until the day the ecommerce supports multiple orders at the same time
    #     last_tx_id = request.session.get('__website_sale_last_tx_id')
    #     last_tx = request.env['payment.transaction'].browse(last_tx_id).sudo().exists()
    #     if last_tx:
    #         PaymentProcessing.remove_payment_transaction(last_tx)
    #     PaymentProcessing.add_payment_transaction(transaction)
    #     request.session['__website_sale_last_tx_id'] = transaction.id
    #     return transaction.render_sale_button(order)