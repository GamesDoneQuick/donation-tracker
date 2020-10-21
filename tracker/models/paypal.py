from django.db import models

_currencyChoices = (('USD', 'US Dollars'), ('CAD', 'Canadian Dollars'))


class IPNSettings(models.Model):
    event = models.OneToOneField(
        'tracker.Event', on_delete=models.CASCADE, related_name='paypal_ipn_settings'
    )
    receiver_email = models.EmailField(max_length=128, verbose_name='Receiver Email')
    currency = models.CharField(
        max_length=8,
        default=_currencyChoices[0][0],
        choices=_currencyChoices,
        verbose_name='Currency',
    )
    logo_url = models.CharField(max_length=1024, blank=True, verbose_name='Logo URL',)

    def __str__(self):
        return f'IPNSettings: {self.event}'

    class Meta:
        verbose_name = 'IPN Settings'
        verbose_name_plural = 'IPN Settings'


class DonorPayPalInfo(models.Model):
    donor = models.OneToOneField(
        'tracker.Donor', on_delete=models.CASCADE, related_name='paypal_info'
    )

    # couple things I've learned from looking at GDQ's IPNs:
    # payer_id is only stable over the long term if they have an account
    # all verified payers have accounts, but not all accounts are verified
    # multiple payer_email can belong to the same payer_id
    #
    # what I think this means
    #
    # - If the payer_id exists, treat it as that donor
    # - If the payer_id does not exist but the payer_email does, that's also a match
    #   - Consider verified and unverified `payer_status` as separate donors for now just for edge case reasons

    payer_id = models.CharField(max_length=16, unique=True)
    payer_email = models.EmailField(max_length=128)
    payer_verified = models.BooleanField()

    class Meta:
        unique_together = ('payer_email', 'payer_verified')
        verbose_name = 'Donor PayPal Info'
        verbose_name_plural = 'Donor PayPal Info'
