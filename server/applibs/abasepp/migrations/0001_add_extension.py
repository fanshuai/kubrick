from django.contrib.postgres.operations import CreateExtension
from django.contrib.postgres import operations
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        operations.BtreeGinExtension(),
        operations.BtreeGistExtension(),
        operations.CITextExtension(),
        operations.HStoreExtension(),
        operations.TrigramExtension(),
        operations.UnaccentExtension(),
        operations.CryptoExtension(),
        CreateExtension('postgis'),
    ]
