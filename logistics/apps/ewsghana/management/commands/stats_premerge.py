import sys
from django.core.management.base import BaseCommand
from django.conf import settings
from dimagi.utils.couch.database import get_db

class Command(BaseCommand):
    help = "Print vital statistics"

    def handle(self, *args, **options):
        from locations.models import *
        from messagelog.models import Message
        from logistics.apps.logistics.models import * 
        print "ProductStock"
        for p in ProductStock.objects.all().order_by('pk'):
            print "   %s %s %s" % (p.product, p.quantity, p.monthly_consumption)
        print "Location"
        for p in Location.objects.all().order_by('pk'):
            print "   %s %s" % (p.name, p.code)
        print "Facilities"
        for p in Facility.objects.all().order_by('pk'):
            print "   %s %s %s %s" % (p.name, p.code, p.type, p.supplied_by)
        print "ProductReports %s" % ProductReport.objects.all().count()
        print "RequisitionReports %s" % RequisitionReport.objects.all().count()
        print "StockTransactions %s" % StockTransaction.objects.all().count()
        print "Messages %s" % Message.objects.all().count()
