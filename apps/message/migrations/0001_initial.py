# Generated by Django 4.2.12 on 2024-05-13 10:46

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=100, verbose_name='消息标题')),
                ('content', models.TextField(verbose_name='消息内容')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='新建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='修改时间')),
            ],
        ),
    ]
