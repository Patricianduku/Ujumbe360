# Generated migration for adding payment_method and mpesa_transaction fields to Payment model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0002_attendance'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='payment_method',
            field=models.CharField(choices=[('Cash', 'Cash'), ('M-Pesa', 'M-Pesa'), ('Bank Transfer', 'Bank Transfer'), ('Card', 'Card')], default='Cash', max_length=20),
        ),
        migrations.AddField(
            model_name='payment',
            name='mpesa_transaction',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payments', to='lms.mpesatransaction'),
        ),
    ]