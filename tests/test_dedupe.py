from leaddesk.dedupe import find_duplicate, is_near_duplicate, similar
from leaddesk.models import lead_id_for, normalize_url


def test_normalize_url_strips_tracking_and_www():
    a = "https://WWW.Example.com/path/?utm_source=x&fbclid=1"
    b = "https://example.com/path"
    assert normalize_url(a) == normalize_url(b)
    assert lead_id_for(a) == lead_id_for(b)


def test_twitter_and_x_share_an_id():
    assert lead_id_for("https://twitter.com/user/status/1") == lead_id_for("https://x.com/user/status/1")


def test_url_duplicate_is_preferred_over_near():
    existing = [
        {
            "lead_id": lead_id_for("https://example.com/a"),
            "source_url": "https://example.com/a",
            "title": "Completely different title about parks",
            "exact_quote": "unrelated",
        }
    ]
    new = {
        "source_url": "https://www.example.com/a?utm_campaign=x",
        "title": "Completely different title about parks",
        "exact_quote": "unrelated",
    }
    kind, match = find_duplicate(new, existing)
    assert kind == "url"
    assert match["source_url"] == "https://example.com/a"


def test_near_duplicate_title():
    old = {"title": "Metra Rail IFB 186323 — replace communications recorder", "exact_quote": "alpha", "source_url": "https://a.example/1"}
    new = {"title": "Metra Rail IFB 186323 - replace communications recorder", "exact_quote": "beta", "source_url": "https://b.example/2"}
    assert is_near_duplicate(new, old)
    kind, _ = find_duplicate(new, [old])
    assert kind == "near"


def test_near_duplicate_quote_only():
    quote = "The county’s current recorder is obsolete and a fuller RFP was needed."
    old = {"title": "One heading", "exact_quote": quote, "source_url": "https://a.example/1"}
    new = {"title": "A totally different heading", "exact_quote": quote, "source_url": "https://b.example/2"}
    assert is_near_duplicate(new, old)


def test_distinct_titles_are_not_duplicates():
    old = {"title": "Chicago OEMC begins rollout of new 911 CAD system", "exact_quote": "one", "source_url": "https://a.example/1"}
    new = {"title": "Madison County Illinois STARCOM21 radio project advances", "exact_quote": "two", "source_url": "https://b.example/2"}
    assert not is_near_duplicate(new, old)
    kind, match = find_duplicate(new, [old])
    assert kind is None and match is None


def test_similar_threshold():
    assert similar("hello world", "hello world")
    assert not similar("hello world", "goodbye moon", threshold=0.85)
