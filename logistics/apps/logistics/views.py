#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

from random import randint
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
from rapidsms.contrib.locations.models import Location
from logistics.apps.logistics.models import Facility, ProductStock, \
    ProductReportsHelper, Product, ProductType, ProductReport, \
    get_geography, STOCK_ON_HAND_REPORT_TYPE
from logistics.apps.logistics.view_decorators import filter_context, geography_context

def input_stock(request, facility_code, context={}, template="logistics/input_stock.html"):
    # TODO: replace this with something that depends on the current user
    # QUESTION: is it possible to make a dynamic form?
    errors = ''
    rms = get_object_or_404(Facility, code=facility_code)
    productstocks = [p for p in ProductStock.objects.filter(facility=rms).order_by('product')]
    if request.method == "POST":
        # we need to use the helper/aggregator so that when we update
        # the supervisor on resolved stockouts we can do it all in a
        # single message
        prh = ProductReportsHelper(rms, STOCK_ON_HAND_REPORT_TYPE)
        for stock in productstocks:
            try:
                if stock.product.sms_code in request.POST:
                    quantity = request.POST[stock.product.sms_code]
                    if not quantity.isdigit():
                        errors = ", ".join([errors, stock.product.name])
                        continue
                    prh.add_product_stock(stock.product.sms_code, quantity)
                    if "%s_consumption" % stock.product.sms_code in request.POST:
                        consumption = request.POST["%s_consumption" % stock.product.sms_code]
                        if not consumption.isdigit():
                            errors = ", ".join([errors, stock.product.name])
                            continue
                        prh.add_product_consumption(stock.product, consumption)
                    if "%s_is_active" % stock.product.sms_code in request.POST:
                        rms.activate_product(stock.product)
                    else:
                        rms.deactivate_product(stock.product)
            except ValueError, e:
                errors = errors + unicode(e)
        if not errors:
            prh.save()
            return HttpResponseRedirect(reverse(stockonhand_facility, args=(rms.code,)))
        errors = "Please enter all stock on hand and consumption as integers, for example:'100'. " + \
                 "The following fields had problems: " + errors.strip(', ')
    return render_to_response(
        template, {
                'errors': errors,
                'rms': rms,
                'productstocks': productstocks,
                'date': datetime.now()
            }, context_instance=RequestContext(request)
    )

@geography_context
def stockonhand_facility(request, facility_code, context={}, template="logistics/stockonhand_facility.html"):
    """
     this view currently only shows the current stock on hand for a given facility
    """
    facility = get_object_or_404(Facility, code=facility_code)
    stockonhands = ProductStock.objects.filter(facility=facility).order_by('product')
    last_reports = ProductReport.objects.filter(facility=facility).order_by('-report_date')
    if last_reports:
        context['last_reported'] = last_reports[0].report_date
    context['stockonhands'] = stockonhands
    context['facility'] = facility
    return render_to_response(
        template, context, context_instance=RequestContext(request)
    )

@geography_context
@filter_context
def district(request, location_code, context={}, template="logistics/aggregate.html"):
    """
    The district view is unusual. When we do not receive a filter by individual product,
    we show the aggregate report. When we do receive a filter by individual product, we show
    the 'by product' report. Let's see how this goes. 
    """
    location = get_object_or_404(Location, code=location_code)
    context['location'] = location
    context['stockonhands'] = stockonhands = ProductStock.objects.filter(facility__location=location)
    commodity_filter = None
    commoditytype_filter = None
    if request.method == "POST" or request.method == "GET":
        # We support GETs so that folks can share this report as a url
        filtered_by_commodity = False
        if 'commodity' in request.REQUEST and request.REQUEST['commodity'] != 'all':
            commodity_filter = request.REQUEST['commodity']
            context['commodity_filter'] = commodity_filter
            commodity = Product.objects.get(sms_code=commodity_filter)
            context['commoditytype_filter'] = commodity.type.code
            template="logistics/stockonhand_district.html"
            context['stockonhands'] = stockonhands.filter(product=commodity)
        elif 'commoditytype' in request.REQUEST and request.REQUEST['commoditytype'] != 'all':
            commoditytype_filter = request.REQUEST['commoditytype']
            context['commoditytype_filter'] = commoditytype_filter
            type = ProductType.objects.get(code=commoditytype_filter)
            context['commodities'] = context['commodities'].filter(type=type)
            context['stockonhands'] = stockonhands.filter(product__type=type)
    context['rows'] =_get_location_children(location, commodity_filter, commoditytype_filter)
    return render_to_response(
        template, context, context_instance=RequestContext(request)
    )

@geography_context
def reporting(request, context={}, template="logistics/reporting.html"):
    """ which facilities have reported on time and which haven't """
    seven_days_ago = datetime.now() + relativedelta(days=-7)
    context['late_facilities'] = Facility.objects.filter(Q(last_reported__lt=seven_days_ago) | Q(last_reported=None)).order_by('-last_reported','name')
    context['on_time_facilities'] = Facility.objects.filter(last_reported__gte=seven_days_ago).order_by('-last_reported','name')
    return render_to_response(
        template, context, context_instance=RequestContext(request)
    )

@geography_context
@filter_context
def aggregate(request, location_code, context={}, template="logistics/aggregate.html"):
    """
    The aggregate view of all children within a geographical region
    where 'children' can either be sub-regions
    OR facilities if no sub-region exists
    """
    commodity_filter = None
    commoditytype_filter = None
    if request.method == "POST" or request.method == "GET":
        # We support GETs so that folks can share this report as a url
        filtered_by_commodity = False
        if 'commodity' in request.REQUEST and request.REQUEST['commodity'] != 'all':
            commodity_filter = request.REQUEST['commodity']
            context['commodity_filter'] = commodity_filter
            commodity = Product.objects.get(sms_code=commodity_filter)
            context['commoditytype_filter'] = commodity.type.code
        elif 'commoditytype' in request.REQUEST and request.REQUEST['commoditytype'] != 'all':
            commoditytype_filter = request.REQUEST['commoditytype']
            context['commoditytype_filter'] = commoditytype_filter
            type = ProductType.objects.get(code=commoditytype_filter)
            context['commodities'] = context['commodities'].filter(type=type)
    location = get_object_or_404(Location, code=location_code)
    context['location'] = location
    context['rows'] =_get_location_children(location, commodity_filter, commoditytype_filter)
    return render_to_response(
        template, context, context_instance=RequestContext(request)
    )

def _get_location_children(location, commodity_filter, commoditytype_filter):
    rows = []
    is_facility = False
    children = location.children()
    if not children:
        is_facility = True
        children = location.facilities()
    for child in children:
        row = {}
        row['name'] = child.name
        row['code'] = child.code
        if is_facility:
            row['url'] = reverse('stockonhand_facility', args=[child.code])
        else:
            row['url'] = reverse('aggregate', args=[child.code])
        row['stockout_count'] = child.stockout_count(product=commodity_filter, 
                                                     producttype=commoditytype_filter)
        row['emergency_stock_count'] = child.emergency_stock_count(product=commodity_filter, 
                                                     producttype=commoditytype_filter)
        row['low_stock_count'] = child.low_stock_count(product=commodity_filter, 
                                                     producttype=commoditytype_filter)
        row['good_supply_count'] = child.good_supply_count(product=commodity_filter, 
                                                     producttype=commoditytype_filter)
        row['overstocked_count'] = child.overstocked_count(product=commodity_filter, 
                                                     producttype=commoditytype_filter)
        rows.append(row)
    return rows
