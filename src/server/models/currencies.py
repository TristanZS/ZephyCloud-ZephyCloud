# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libs
import logging
import json

# Third party libs
import requests

# Project libs
from lib import pg_util
from lib import util
import core.api_util

log = logging.getLogger("aziugo")


def symbol_to_name(currency_symbol):
    if currency_symbol.upper() == "USD":
        return "dollar"
    elif currency_symbol.upper() == "EUR":
        return "euro"
    elif currency_symbol.upper() == "CNY":
        return "yuan"
    else:
        raise RuntimeError("Unknown currency symbol "+str(currency_symbol))


def name_to_symbol(currency_name):
    if currency_name.lower() == "dollar":
        return "USD"
    elif currency_name.lower() == "euro":
        return "EUR"
    elif currency_name.lower() == "yuan":
        return "CNY"
    else:
        raise RuntimeError("Unknown currency "+str(currency_name))


def all():
    return ["dollar", "euro", "yuan"]


@core.api_util.need_db_context
def get_currencies_to_zc():
    g_db = core.api_util.DatabaseContext.get_conn()
    currencies = pg_util.all_to_dict(g_db.execute("SELECT * FROM currency_exchange_rates").fetchall())
    return dict({c["currency"]: c["to_zcoins"] for c in currencies})


@core.api_util.need_db_context
def get_currencies_ratio(to_currency):
    currencies = get_currencies_to_zc()
    results = {}
    for currency, ratio in currencies.items():
        if currency == to_currency:
            pass
        results[currency] = ratio / currencies[to_currency]
    return results


@core.api_util.need_db_context
def update_currency_exchange_rates(currency_api_url, currency_api_token):
    # Load existing values
    g_db = core.api_util.DatabaseContext.get_conn()
    curr_tmp = pg_util.all_to_dict(g_db.execute("""SELECT DISTINCT currency, is_fixed, to_zcoins
                                                     FROM currency_exchange_rates""").fetchall())
    currencies = []
    fixed_currencies_values = {}
    ref_currency = None
    for currency_info in curr_tmp:
        currencies.append(currency_info["currency"])
        if currency_info["is_fixed"] == True:
            ref_currency = currency_info["currency"]
            fixed_currencies_values[currency_info["currency"]] = currency_info["to_zcoins"]
    if ref_currency is None:
        raise RuntimeError("No fixed currency in database !!!")

    # Format params for api call
    if "://" in currency_api_url:
        currency_api_url = str(currency_api_url).split("://", 1)[1]
    currency_api_url = "http://" + currency_api_url.rstrip("/") + "/api/live"
    currency_param = ",".join([name_to_symbol(c) for c in currencies])

    # Do the api call and check the result
    result = requests.get(currency_api_url, params={"access_key": currency_api_token,
                                                    "currencies": currency_param})
    if result.status_code < 200 or result.status_code > 299:
        raise RuntimeError("Unable to get the currency exchange rates: api call failed")
    result = result.json()
    if result['success'] != True:
        raise RuntimeError("Unable to get the currency exchange rates: api call failed")

    # map back the result
    source_symbol = result['source']
    source = symbol_to_name(source_symbol)
    api_result = {}
    for key, value in result['quotes'].items():
        api_result[symbol_to_name(key[len(source_symbol):])] = value

    # calculate the new values
    currencies_to_zcoins = {}
    for currency, to_source in api_result.items():
        if currency in fixed_currencies_values.keys():
            currencies_to_zcoins[currency] = fixed_currencies_values[currency]
    if source not in fixed_currencies_values.keys():
        currencies_to_zcoins[source] = fixed_currencies_values[ref_currency] * api_result[ref_currency]
    for currency, to_source in api_result.items():
        if currency == source or currency in fixed_currencies_values.keys():
            continue
        currencies_to_zcoins[currency] = currencies_to_zcoins[source] / api_result[currency]

    # Save the results
    for currency, to_zcoins in currencies_to_zcoins.items():
        if util.float_equals(to_zcoins, 0) or to_zcoins < 0:
            log.error("A currency should never be zero or less:")
            log.error("DEBUG currencies: "+json.dumps(currencies, indent=4, sort_keys=True))
            log.error("DEBUG fixed_currencies_values: " + json.dumps(fixed_currencies_values, indent=4, sort_keys=True))
            log.error("DEBUG api_result: " + json.dumps(api_result, indent=4, sort_keys=True))
            log.error("DEBUG currencies_to_zcoins: " + json.dumps(currencies_to_zcoins, indent=4, sort_keys=True))
            log.error("DEBUG source: " + json.dumps(source, indent=4, sort_keys=True))
            log.error("DEBUG currency: " + json.dumps(currency, indent=4, sort_keys=True))
            log.error("DEBUG to_zcoins: " + json.dumps(to_zcoins, indent=4, sort_keys=True))
            raise RuntimeError("A currency should never be zero or less")
        g_db.execute("UPDATE currency_exchange_rates SET to_zcoins = %s WHERE currency = %s", [to_zcoins, currency])
