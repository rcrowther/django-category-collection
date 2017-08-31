# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-16 09:40
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('taxonomy', '0005_auto_20170810_1445'),
    ]

    operations = [
        migrations.CreateModel(
            name='Taxonomy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(db_index=True, help_text='Name for a tree of categories. Limited to 255 characters.', max_length=255)),
                ('slug', models.SlugField(help_text='Short name for use in urls.', max_length=64, unique=True)),
                ('is_single', models.BooleanField(default=True, help_text='Nunber of parents allowed for a term in the taxonomy (True = one only, False = many).')),
                ('is_unique', models.BooleanField(default=False, help_text='Nunber of parents allowed for a node in the taxonomy (True = one only, False = many).')),
                ('weight', models.PositiveSmallIntegerField(blank=True, default=0, help_text='Priority for display in some templates. Lower value orders first. 0 to 32767.')),
            ],
        ),
        migrations.CreateModel(
            name='TermNode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('node', models.IntegerField(db_index=True, help_text='Id of data to be associated with a Term.')),
            ],
        ),
        migrations.CreateModel(
            name='TermTree',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.RemoveField(
            model_name='term',
            name='parent',
        ),
        migrations.AlterField(
            model_name='term',
            name='slug',
            field=models.SlugField(help_text='Short name for use in urls.', max_length=64),
        ),
        migrations.AlterField(
            model_name='term',
            name='title',
            field=models.CharField(db_index=True, help_text='Name for the category. Limited to 255 characters.', max_length=255),
        ),
        migrations.AlterField(
            model_name='term',
            name='weight',
            field=models.PositiveSmallIntegerField(blank=True, default=0, help_text='Priority for display in some templates. Lower value orders first. 0 to 32767.'),
        ),
        migrations.CreateModel(
            name='TaxonomyNodetype',
            fields=[
                ('taxonomy', models.OneToOneField(help_text='Type of data allowed in the Taxonomy.', on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='taxonomy.Taxonomy')),
                ('node_type', models.CharField(db_index=True, help_text='Type of data allowed in the Taxonomy.', max_length=255)),
            ],
        ),
        migrations.AddField(
            model_name='termtree',
            name='parent',
            field=models.ForeignKey(blank=True, help_text='Term parent for another term, or null for root (connection to self forbidden)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='taxonomy.Term'),
        ),
        migrations.AddField(
            model_name='termtree',
            name='term',
            field=models.ForeignKey(help_text='Term to connect to another Term', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='taxonomy.Term'),
        ),
        migrations.AddField(
            model_name='termnode',
            name='term',
            field=models.ForeignKey(help_text='A Term associated with data.', on_delete=django.db.models.deletion.CASCADE, to='taxonomy.Term'),
        ),
    ]
