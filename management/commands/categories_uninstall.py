from django.core.management.base import BaseCommand, CommandError
from polls.models import Question as Poll

class Command(BaseCommand):
    help = 'Uninstalls the category app, as far as possible'

    def add_arguments(self, parser):
        parser.add_argument('poll_id', nargs='+', type=int)

    def drop(self, dbname):
        _DropSQL = "DROP TABLE %s"

        c = connection.cursor()
        try:
            c.execute(_DropSQL, [dbname])
        finally:
            c.close()
            
    def handle(self, *args, **options):
        self.drop(Base._meta.db_table) 
        self.drop(Term._meta.db_table)
        self.drop(TermParent._meta.db_table)
        self.drop(BaseTerm._meta.db_table)
        self.drop(Element._meta.db_table)
        self.stdout.write(self.style.SUCCESS('Uninstalled the category app database tables'))
        self.stdout.write('You will need also to:')
        self.stdout.write(' - remove app registration in settings.py')
        self.stdout.write(' - remove use of taxonomy fields in the forms in other applications')
        self.stdout.write(' - remove use of taxonomy methods in templates or views')
        self.stdout.write('and, optionally:')
        self.stdout.write(' - remove sitewide URLs in url.py')
        self.stdout.write(' - remove the folders and files')
