# Generated by Django 3.2.7 on 2021-09-27 19:33

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TokensDiagnosticos',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=255)),
                ('id_descripcion', models.CharField(max_length=255)),
                ('largo_palabras_termino', models.IntegerField()),
            ],
        ),
    ]
