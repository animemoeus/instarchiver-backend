"""Django Unfold Admin Configuration.

This module contains all configuration settings for the Django Unfold admin interface.
For more information about available options, see:
https://unfoldadmin.com/docs/configuration/settings/
"""

UNFOLD = {
    "SITE_TITLE": "Instarchiver Admin",
    "SITE_HEADER": "Instarchiver",
    "SITE_URL": "/",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "STYLES": [
        lambda request: "css/admin-custom.css",
    ],
    "SCRIPTS": [],
    "COLORS": {
        "primary": {
            "50": "250 245 255",
            "100": "243 232 255",
            "200": "233 213 255",
            "300": "216 180 254",
            "400": "196 141 252",
            "500": "168 85 247",
            "600": "147 51 234",
            "700": "126 34 206",
            "800": "107 33 168",
            "900": "88 28 135",
            "950": "59 7 100",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Navigation",
                "separator": True,
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "link": "/admin/",
                    },
                ],
            },
            {
                "title": "User Management",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "people",
                        "link": "/admin/users/user/",
                    },
                    {
                        "title": "Groups",
                        "icon": "group",
                        "link": "/admin/auth/group/",
                    },
                ],
            },
            {
                "title": "Celery Beat",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Periodic Tasks",
                        "icon": "schedule",
                        "link": "/admin/django_celery_beat/periodictask/",
                    },
                    {
                        "title": "Crontab Schedule",
                        "icon": "access_time",
                        "link": "/admin/django_celery_beat/crontabschedule/",
                    },
                    {
                        "title": "Interval Schedule",
                        "icon": "timer",
                        "link": "/admin/django_celery_beat/intervalschedule/",
                    },
                    {
                        "title": "Clocked Schedule",
                        "icon": "alarm",
                        "link": "/admin/django_celery_beat/clockedschedule/",
                    },
                ],
            },
        ],
    },
}
