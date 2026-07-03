import unittest

from fastapi import HTTPException

from app.main import _billing_update_from_webhook
from app.models.history import BillingWebhookSubscriptionEvent


class BillingWebhookAdapterTests(unittest.TestCase):
    def test_stripe_subscription_payload_maps_metadata_and_period_end(self):
        user_id, update = _billing_update_from_webhook(
            BillingWebhookSubscriptionEvent(
                provider="stripe",
                providerPayload={
                    "type": "customer.subscription.updated",
                    "data": {
                        "object": {
                            "id": "sub_123",
                            "customer": "cus_123",
                            "status": "active",
                            "current_period_end": 1782864000,
                            "metadata": {"userId": "user-1"},
                            "items": {"data": [{"price": {"id": "price_premium_monthly"}}]},
                        }
                    },
                },
            )
        )

        self.assertEqual(user_id, "user-1")
        self.assertEqual(update.subscriptionStatus, "active")
        self.assertEqual(update.subscriptionPlanId, "price_premium_monthly")
        self.assertEqual(update.billingProviderCustomerId, "cus_123")
        self.assertEqual(update.billingProviderSubscriptionId, "sub_123")
        self.assertEqual(update.billingPeriodEnd, "2026-07-01T00:00:00Z")

    def test_razorpay_subscription_payload_maps_notes_and_status(self):
        user_id, update = _billing_update_from_webhook(
            BillingWebhookSubscriptionEvent(
                provider="razorpay",
                providerPayload={
                    "event": "subscription.authenticated",
                    "payload": {
                        "subscription": {
                            "entity": {
                                "id": "sub_razorpay",
                                "customer_id": "cust_razorpay",
                                "plan_id": "plan_monthly",
                                "status": "authenticated",
                                "current_end": 1785456000,
                                "notes": {"user_id": "user-2"},
                            }
                        }
                    },
                },
            )
        )

        self.assertEqual(user_id, "user-2")
        self.assertEqual(update.subscriptionStatus, "active")
        self.assertEqual(update.subscriptionPlanId, "plan_monthly")
        self.assertEqual(update.billingProviderCustomerId, "cust_razorpay")
        self.assertEqual(update.billingProviderSubscriptionId, "sub_razorpay")
        self.assertEqual(update.billingPeriodEnd, "2026-07-31T00:00:00Z")

    def test_direct_fields_override_provider_payload(self):
        user_id, update = _billing_update_from_webhook(
            BillingWebhookSubscriptionEvent(
                provider="stripe",
                userId="manual-user",
                subscriptionStatus="canceled",
                subscriptionPlanId="manual-plan",
                providerPayload={
                    "data": {
                        "object": {
                            "id": "sub_provider",
                            "status": "active",
                            "metadata": {"userId": "provider-user"},
                            "items": {"data": [{"price": {"id": "provider-plan"}}]},
                        }
                    }
                },
            )
        )

        self.assertEqual(user_id, "manual-user")
        self.assertEqual(update.subscriptionStatus, "canceled")
        self.assertEqual(update.subscriptionPlanId, "manual-plan")
        self.assertEqual(update.billingProviderSubscriptionId, "sub_provider")

    def test_missing_user_id_is_rejected(self):
        with self.assertRaises(HTTPException) as context:
            _billing_update_from_webhook(BillingWebhookSubscriptionEvent(provider="stripe", providerPayload={"data": {"object": {"status": "active"}}}))

        self.assertEqual(context.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
