# -*- coding: utf-8 -*-

import locale
import time
import urllib
import json
import urlparse

import bleach
import jinja2

from django.utils.text import Truncator
from django.db.utils import IntegrityError
from django.contrib.sites.models import RequestSite
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.core.cache import cache

from jingo import register
from sorl.thumbnail import get_thumbnail

from airmozilla.base.utils import unhtml
from airmozilla.main.models import Picture


@register.filter
def js_date(dt, format='ddd, MMM D, YYYY, h:mma UTCZZ', enable_timeago=True,
            autoupdate=False):
    """ Python datetime to a time tag with JS Date.parse-parseable format. """
    dt = dt.replace(microsecond=0)  # we don't need the microseconds
    dt_date = dt.strftime('%m/%d/%Y')
    dt_time = dt.strftime('%H:%M')
    dt_tz = dt.tzname() or 'UTC'
    formatted_datetime = ' '.join([dt_date, dt_time, dt_tz])
    class_ = 'timeago ' if enable_timeago else ''
    if autoupdate:
        class_ += 'autoupdate '
    return jinja2.Markup('<time datetime="%s" class="%sjstime"'
                         ' data-format="%s">%s</time>'
                         % (dt.isoformat(), class_,
                            format, formatted_datetime))


@register.function
def strip_html(text):
    return unhtml(text)


@register.function
def short_desc(event, words=25, strip_html=False):
    """Takes an event object and returns a shortened description."""
    if event.short_description:
        description = event.short_description
    else:
        description = event.description
    if strip_html:
        description = unhtml(description)
    return Truncator(description).words(words)


@register.function
def truncate_words(text, words):
    return Truncator(text).words(words)


@register.function
# def truncate_chars(text, chars, middle=False, left=False, ellipsis=u'…'):
def truncate_chars(text, chars, ellipsis=u'…'):
    assert chars > 4, chars
    if len(text) > chars:
        # if middle:
        #     m = len(text) / 2
        #     left = text[:m]
        #     right = text[m:]
        #     alternate = True
        #     while len(left) + len(right) > chars:
        #         if alternate:
        #             left = left[:-1]
        #         else:
        #             right = right[1:]
        #         alternate = not alternate
        #     text = u'%s%s%s' % (
        #         left,
        #         ellipsis,
        #         right
        #     )
        # elif left:
        #     text = '%s%s' % (
        #         ellipsis,
        #         text[-chars:].strip()
        #     )
        # else:
        #     text = '%s%s' % (
        #         text[:chars - 1].strip(),
        #         ellipsis
        #     )
        text = '%s%s' % (
            text[:chars - 1].strip(),
            ellipsis
        )
    return text


@register.function
def thumbnail(filename, geometry, **options):
    try:
        return get_thumbnail(filename, geometry, **options)
    except IntegrityError:
        # annoyingly, this happens sometimes because kvstore in sorl
        # doesn't check before writing properly
        # see https://bugzilla.mozilla.org/show_bug.cgi?id=817765
        # try again
        time.sleep(1)
        return thumbnail(filename, geometry, **options)


@register.function
def tags_query_string(tags):
    return urllib.urlencode({'tag': [x.name for x in tags]}, True)


@register.filter
def carefulnl2br(string):
    # if the string contains existing paragraphs or line breaks
    # in html...
    if '<p' in string or '<br' in string:
        # ...then dare not
        return string
    return string.replace('\n', '<br>')


@register.function
def thousands(number):
    """AKA ``thousands separator'' - 1000000 becomes 1,000,000 """
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, '')
    return locale.format('%d', number, True)


@register.function
@jinja2.contextfunction
def make_absolute(context, uri):
    if '://' not in uri:
        request = context['request']
        prefix = request.is_secure() and 'https' or 'http'
        if uri.startswith('//'):
            # we only need the prefix
            uri = '%s:%s' % (prefix, uri)
        else:
            uri = '%s://%s%s' % (prefix, RequestSite(request).domain, uri)
    return uri


@register.filter
def pluralize(value, form='s'):
    if value != 1:
        return form
    return ''


@register.function
def json_print(value, indent=0):
    return jinja2.Markup(json.dumps(value, indent=indent))


@register.filter
def safe_html(text):
    """allow some of the text's HTML tags and escape the rest"""
    text = bleach.clean(text, tags=['a', 'p', 'b', 'i', 'em', 'strong', 'br'])
    return jinja2.Markup(text)


@register.function
def show_thumbnail(
    event,
    geometry='160x90',
    crop='center',
    alt=None,
    image=None,
    url_prefix='',
    live=False,
):
    alt = alt or event.title
    if not image:
        image = event.picture and event.picture.file or event.placeholder_img
    thumb = thumbnail(image, geometry, crop=crop)
    data = ''
    if not live and event:
        data = ' data-eventid="%s"' % event.id
    html = (
        '<img src="%(url)s" width="%(width)s" height="%(height)s" '
        'alt="%(alt)s"%(data)s class="wp-post-image">' % {
            'data': data,
            'url': urlparse.urljoin(url_prefix, thumb.url),
            'width': thumb.width,
            'height': thumb.height,
            'alt': escape(alt),
        }
    )
    return mark_safe(html)


@register.function
def show_lazyr_thumbnail(
    event,
    geometry='160x90',
    crop='center',
    alt=None,
    image=None,
    live=False,
):
    placeholder_url = get_default_placeholder_thumb_url(geometry, crop)
    if placeholder_url is None:
        return show_thumbnail(
            event,
            geometry=geometry,
            crop=crop,
            alt=alt,
            image=image
        )

    alt = alt or event.title
    if not image:
        image = event.picture and event.picture.file or event.placeholder_img
    thumb = thumbnail(image, geometry, crop=crop)
    data = ''
    if not live:
        data = ' data-eventid="%s"' % event.id
    html = (
        '<img src="%(placeholder)s" data-layzr="%(url)s" '
        'width="%(width)s" height="%(height)s" '
        'alt="%(alt)s"%(data)s class="wp-post-image">' % {
            'data': data,
            'placeholder': placeholder_url,
            'url': thumb.url,
            'width': thumb.width,
            'height': thumb.height,
            'alt': escape(alt),
        }
    )
    return mark_safe(html)


def get_default_placeholder_thumb_url(geometry, crop):
    cache_key = 'default-placeholder-thumb-{0}-{1}'.format(
        geometry,
        crop,
    )
    url = cache.get(cache_key)
    if url is None:
        qs = Picture.objects.filter(default_placeholder=True)
        for picture in qs.order_by('-modified'):
            thumb = thumbnail(
                picture.file,
                geometry,
                crop=crop
            )
            cache.set(cache_key, thumb.url, 60 * 60)
            url = thumb.url
            break
    return url
