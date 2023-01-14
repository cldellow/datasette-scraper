from datasette_scraper.plugins.discover_allow import canonicalize_url

def test_allow():
    assert canonicalize_url({}, 'from', 'to', 0) == None
    assert canonicalize_url({'discover-allow': []}, 'from', 'to', 0) == None

    assert canonicalize_url(
        {
            'discover-allow': [
                {
                    'from-url-regex': 'blah'
                }
            ]
        },
        'https://from.com/',
        'https://to.com/',
        0
    ) == False

    assert canonicalize_url(
        {
            'discover-allow': [
                {
                    'from-url-regex': 'from.com'
                }
            ]
        },
        'https://from.com/',
        'https://to.com/',
        0
    ) == True

    assert canonicalize_url(
        {
            'discover-allow': [
                {
                    'from-url-regex': 'from.com',
                    'depth': 3
                }
            ]
        },
        'https://from.com/',
        'https://to.com/',
        0
    ) == ('https://to.com/', 3)
