/* global OPayCheckout */
odoo.define('payment_opay_integration.payment_form', require => {
    'use strict';

    const core = require('web.core');
    const checkoutForm = require('payment.checkout_form');
    var rpc = require('web.rpc');
    const manageForm = require('payment.manage_form');
    const _t = core._t;

    const opayMixin = {
        _dropinOnAdditionalDetails: function (state, dropin) {
            console.log("HHHHHHHHHHHHHHHHHHHHHHHHhhh1");
            return this._rpc({
                route: '/payment/opay/payment_details',
                params: {
                    'acquirer_id': dropin.acquirerId,
                    'reference': this.opayDropin.reference,
                    'payment_details': state.data,
                },
            }).then(paymentDetails => {
                if (paymentDetails.action) { // Additional action required from the shopper
                    dropin.handleAction(paymentDetails.action);
                } else { // The payment reached a final state, redirect to the status page
                    window.location = '/payment/status';
                }
            }).guardedCatch((error) => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("We are not able to process your payment."),
                    error.message.data.message
                );
            });
        },
        _dropinOnError: function (error) {
            console.log("HHHHHHHHHHHHHHHHHHHHHHHHhhh2");
            this._displayError(
                _t("Incorrect Payment Details"),
                _t("Please verify your payment details.")
            );
        },
        _prepareInlineForm: function (provider, paymentOptionId, flow) {
            console.log("paymentOptionId",paymentOptionId);
            console.log("provider",provider);
            console.log("flow",flow);
            console.log("this",this);
            if (provider !== 'opay') {
                return this._super(...arguments);
            }

            // Check if instantiation of the drop-in is needed
            if (flow === 'token') {
                return Promise.resolve(); // No drop-in for tokens
            } else if (this.opayDropin && this.opayDropin.acquirerId === paymentOptionId) {
                this._setPaymentFlow('direct'); // Overwrite the flow even if no re-instantiation
                return Promise.resolve(); // Don't re-instantiate if already done for this acquirer
            }

            // Overwrite the flow of the select payment option
            this._setPaymentFlow('direct');

            // Get public information on the acquirer (state, client_key)
            return this._rpc({
                route: '/payment/opay/acquirer_info',
                params: {
                    'acquirer_id': paymentOptionId,
                },
            }).then(acquirerInfo => {
                // Get the available payment methods
                return this._rpc({
                    route: '/payment/opay/payment_methods',
                    params: {
                        'acquirer_id': paymentOptionId,
                        'partner_id': parseInt(this.txContext.partnerId),
                        'amount': this.txContext.amount
                            ? parseFloat(this.txContext.amount)
                            : undefined,
                        'currency_id': this.txContext.currencyId
                            ? parseInt(this.txContext.currencyId)
                            : undefined,
                    },
                }).then(paymentMethodsResult => {
                    // Instantiate the drop-in

                });
            }).guardedCatch((error) => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("An error occurred when displayed this payment form."),
                    error.message.data.message
                );
            });
        },

        async _processPayment(provider, paymentOptionId, flow) {
            console.log("HHHHHHHHHHHHHHHHHHHHHHHHhhh5");
            console.log("this.opayDropin",provider, flow);
            if (provider !== 'opay' || flow === 'token') {
                return this._super(...arguments); // Tokens are handled by the generic flow
            }
            else {
                return this._rpc({
                route: this.txContext.transactionRoute,
                params: this._prepareTransactionRouteParams('opay',paymentOptionId, 'direct'),
            }).then(processingValues => {
                console.log("HHHHHHHHHHHHHHHHHHHHHHHHhhh3", paymentOptionId, this.txContext.amount, this.txContext.currencyId, this.txContext.partnerId, this.txContext.accessToken);
                console.log("HHHHHHHHHHHHHHHHHHHHHHHHhhh25", processingValues.acquirer_id, processingValues.amount, processingValues.currency_id, processingValues.partner_id, processingValues.reference);
                // Initiate the payment

                return this._rpc({
                    route: '/payment/opay/payments',
                    params: {
                        'acquirer_id': processingValues.acquirer_id,
                        'reference': processingValues.reference,
                        'converted_amount': processingValues.amount,
                        'currency_id': processingValues.currency_id,
                        'partner_id': processingValues.partner_id,
                        'payment_method': '',
                        'access_token': this.txContext.accessToken,
                    },
                });
            }).then(paymentResponse => {
                if (paymentResponse.data.cashierUrl) { // Additional action required from the shopper
                    window.open(paymentResponse.data.cashierUrl, "_new");
                    this._hideInputs(); // Only the inputs of the inline form should be used
                    $('body').unblock(); // The page is blocked at this point, unblock it
//                    processingValues.handleAction(paymentResponse.cashierUrl);
                } else { // The payment reached a final state, redirect to the status page
                    window.location = '/payment/status';
                }
            }).guardedCatch((error) => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("We are not able to process your payment."),
                    error.message.data.message
                );
            });
            }
        },
    };

    checkoutForm.include(opayMixin);
    manageForm.include(opayMixin);
});