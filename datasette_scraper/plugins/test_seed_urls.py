from datasette_scraper.plugins.seed_urls import get_seed_urls

def test_seed_urls():
    assert get_seed_urls({}) == []

    assert get_seed_urls({'seed-urls': ['foo']}) == ['foo']
