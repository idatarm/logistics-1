#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext as _
from logistics.apps.logistics.models import Location, ProductStock, \
    ProductStockReport, get_geography, STOCK_ON_HAND_REPORT_TYPE

def input_stock(request, template="logistics/input_stock.html"):
    # TODO: replace this with something that depends on the current user
    # QUESTION: is it possible to make a dynamic form?
    rms = Location.objects.filter(type__slug='RMS')[0]
    commodities = [p.product for p in ProductStock.objects.filter(location=rms, is_active=True).order_by('product')]
    if request.method == "POST":
        stock_report = ProductStockReport(rms, STOCK_ON_HAND_REPORT_TYPE)
        for commodity in commodities:
            if commodity.sms_code in request.POST:
                quantity = request.POST[commodity.sms_code]
                if not quantity.isdigit():
                    raise ValueError("Please enter all stock on hand as integer. For example, '1000'.")
                stock_report.add_product_stock(commodity.sms_code, request.POST[commodity.sms_code])
        stock_report.save()
        if stock_report.errors:
            raise ValueError(_('You reported: %(stocks)s, but there were errors: %(err)s'),
                             stocks=", ". join(stock_report.product_stock),
                             err = ", ".join(unicode(e) for e in stock_report.errors))
        return HttpResponseRedirect(reverse(stockonhand, args=(rms.code,)))
    return render_to_response(
        template, {
                'commodities': commodities,
                'date': datetime.now()
            }, context_instance=RequestContext(request)
    )

def stockonhand(request, facility_code, template="logistics/stockonhand.html"):
    """
     TODO: this view currently only shows the current stock on hand
     It would be great to show historical stock on hand
    """
    context = {}
    location = get_object_or_404(Location, code=facility_code)
    stockonhands = ProductStock.objects.filter(location=location, is_active=True).order_by('product')
    context['stockonhands'] = stockonhands
    context['location'] = location
    context['geography'] = get_geography()
    return render_to_response(
        template, context, context_instance=RequestContext(request)
    )

def reporting(request, template="logistics/reporting.html"):
    context = {}
    seven_days_ago = datetime.now() + relativedelta(days=-7)
    context['late_facilities'] = Location.objects.filter(Q(last_reported__lt=seven_days_ago) | Q(last_reported=None)).order_by('-last_reported')
    context['on_time_facilities'] = Location.objects.filter(last_reported__gte=seven_days_ago).order_by('-last_reported')
    return render_to_response(
        template, context, context_instance=RequestContext(request)
    )

def aggregate(request, location_code, template="logistics/aggregate.html"):
    """
     TODO: this view currently only shows the current stock on hand
     It would be great to show historical stock on hand
    """
    context = {}
    location = get_object_or_404(Location, code=location_code)
    stockonhands = ProductStock.objects.filter(location=location, is_active=True).order_by('product')
    context['stockonhands'] = stockonhands
    context['location'] = location
    context['geography'] = get_geography()
    return render_to_response(
        template, context, context_instance=RequestContext(request)
    )

