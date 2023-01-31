# coding: utf-8

import json
import logging
import dateutil.parser
import pytz
import requests

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AcquirerOPay(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('opay', 'OPay')], ondelete={'opay': 'cascade'})
    opay_merchant_account = fields.Char(
        string="Merchant ID",
        help="The code of the merchant account to use with this acquirer",
        required_if_provider='opay', groups='base.group_user')
    opay_checkout_api_url = fields.Char(
        string="Checkout API URL", help="The base URL for the Checkout API endpoints",
        required_if_provider='opay')
    # opay_email_account = fields.Char('opay Email ID', required_if_provider='opay', groups='base.group_user')
    opay_seller_account = fields.Char(
        'Public Key', groups='base.group_user',
        help='The Merchant ID is used to ensure communications coming from opay are valid and secured.')
    opay_use_ipn = fields.Boolean('Use IPN', default=True, help='opay Instant Payment Notification',
                                  groups='base.group_user')
    opay_pdt_token = fields.Char(string='Secret Key',
                                 help='Payment Data Transfer allows you to receive notification of successful payments as they are made.',
                                 groups='base.group_user')
    # Server 2 server
    opay_api_enabled = fields.Boolean('Use Rest API', default=False)
    opay_api_username = fields.Char('Rest API Username', groups='base.group_user')
    opay_api_password = fields.Char('Rest API Password', groups='base.group_user')
    opay_api_access_token = fields.Char('Access Token', groups='base.group_user')
    opay_api_access_token_validity = fields.Datetime('Access Token Validity', groups='base.group_user')
    # Default opay fees
    fees_dom_fixed = fields.Float(default=0.35)
    fees_dom_var = fields.Float(default=3.4)
    fees_int_fixed = fields.Float(default=0.35)
    fees_int_var = fields.Float(default=3.9)

    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        res = super(AcquirerOPay, self)._get_feature_support()
        res['fees'].append('opay')
        return res

    @api.model
    def _opay_make_request(
            self, url_field_name, endpoint, endpoint_param=None, payload=None, method='POST'
    ):
        """ Make a request to OPay API at the specified endpoint.

        Note: self.ensure_one()

        :param str url_field_name: The name of the field holding the base URL for the request
        :param str endpoint: The endpoint to be reached by the request
        :param str endpoint_param: A variable required by some endpoints which are interpolated with
                                   it if provided. For example, the acquirer reference of the source
                                   transaction for the '/payments/{}/refunds' endpoint.
        :param dict payload: The payload of the request
        :param str method: The HTTP method of the request
        :return: The JSON-formatted content of the response
        :rtype: dict
        :raise: ValidationError if an HTTP error occurs
        """

        def _build_url(_base_url, _version, _endpoint):
            """ Build an API URL by appending the version and endpoint to a base URL.

            The final URL follows this pattern: `<_base>/V<_version>/<_endpoint>`.

            :param str _base_url: The base of the url prefixed with `https://`
            :param int _version: The version of the endpoint
            :param str _endpoint: The endpoint of the URL.
            :return: The final URL
            :rtype: str
            """
            _base = _base_url.rstrip('/')  # Remove potential trailing slash
            # _endpoint = _endpoint.lstrip('/')  # Remove potential leading slash
            _endpoint = 'international/cashier/create'  # Remove potential leading slash
            return f'{_base}/v{_version}/{_endpoint}'

        self.ensure_one()

        base_url = self[url_field_name]  # Restrict request URL to the stored API URL fields
        # version = API_ENDPOINT_VERSIONS[endpoint]
        version = '1'
        endpoint = endpoint if not endpoint_param else endpoint.format(endpoint_param)
        url = _build_url(base_url, version, endpoint)
        headers = {'Authorization': 'Bearer ' + self.opay_seller_account,
                   'MerchantId': self.opay_merchant_account}
        try:
            response = requests.request(method, url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach endpoint at %s", url)
            raise ValidationError("OPay: " + _("Could not establish the connection to the API."))
        except requests.exceptions.HTTPError as error:
            _logger.exception(
                "invalid API request at %s with data %s: %s", url, payload, error.response.text
            )
            raise ValidationError("OPay: " + _("The communication with the API failed."))
        return response.json()

    def _get_default_payment_method_id(self):
        self.ensure_one()
        return self.env.ref('payment_opay_integration.payment_method_opay_id').id

class Txopay(models.Model):
    _inherit = 'payment.transaction'

    opay_txn_type = fields.Char('Transaction type')

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _process_feedback_data(self, data):
        """ Override of payment to process the transaction based on OPay data.

        Note: self.ensure_one()

        :param dict data: The feedback data sent by the provider
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_feedback_data(data)
        if self.provider != 'opay':
            return

        # Handle the acquirer reference
        data_list = data['data']
        if 'orderNo' in data_list:
            self.acquirer_reference = data_list.get('orderNo')

        # Handle the payment state
        payment_code = data.get('code')
        if not payment_code:
            raise ValidationError("OPay: " + _("Received data with missing payment state."))

        if payment_code == '00000':
            self._set_pending()

