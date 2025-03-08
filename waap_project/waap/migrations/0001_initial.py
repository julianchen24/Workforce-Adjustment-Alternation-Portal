# Generated by Django 5.1.7 on 2025-03-08 00:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="WaapUser",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("first_name", models.CharField(max_length=100)),
                ("last_name", models.CharField(max_length=100)),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("department", models.CharField(max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="JobPosting",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("job_title", models.CharField(max_length=200)),
                ("location", models.CharField(max_length=100)),
                (
                    "classification",
                    models.CharField(
                        choices=[
                            ("PERMANENT", "Permanent"),
                            ("TEMPORARY", "Temporary"),
                            ("CONTRACT", "Contract"),
                            ("CASUAL", "Casual"),
                        ],
                        max_length=20,
                    ),
                ),
                ("alternation_criteria", models.JSONField(blank=True, default=dict)),
                (
                    "language_profile",
                    models.CharField(
                        choices=[
                            ("ENGLISH", "English Essential"),
                            ("FRENCH", "French Essential"),
                            ("BILINGUAL", "Bilingual"),
                            ("ENGLISH_PREFERRED", "English Preferred"),
                            ("FRENCH_PREFERRED", "French Preferred"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "contact_email",
                    models.EmailField(blank=True, max_length=254, null=True),
                ),
                ("posting_date", models.DateTimeField(auto_now_add=True)),
                ("expiration_date", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="job_postings",
                        to="waap.department",
                    ),
                ),
            ],
        ),
    ]
