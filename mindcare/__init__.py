# GabAI Application
import pymysql

pymysql.install_as_MySQLdb()

# Allow MariaDB 10.4.32 compatibility with Django 5.x on XAMPP
from django.db.backends.mysql.base import DatabaseWrapper
from django.db.backends.mysql.features import DatabaseFeatures

DatabaseWrapper.check_database_version_supported = lambda self: None
DatabaseFeatures.can_return_columns_from_insert = False
