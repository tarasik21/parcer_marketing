# Static RSS source configuration for the digest bot.
#
# PRIMARY_SOURCES: confirmed SaaS-marketing authors the bot prefers.
# FALLBACK_SOURCES: bootstrapped-SaaS-founder feeds used when the primary
# sources have nothing new to report (see Task 7's orchestrator).
#
# All URLs below were fetched and confirmed to return valid RSS/Atom XML
# with recent (non-stale) entries as of 2026-07-28.

# NOTE: Kyle Poyar's newsletter "Growth Unhinged" moved from Substack to
# Beehiiv around January 2026. His old Substack feed
# (kylepoyar.substack.com/feed) is dead. Extensive research (raw HTML head
# inspection, sitemap.xml, robots.txt, wayback machine, full-page JSON
# payload search, per-post pages) found NO public RSS feed currently
# exposed on https://www.growthunhinged.com/ -- unlike other Beehiiv
# publications (e.g. Marc Lou's newsletter below), Growth Unhinged does not
# appear to have the "RSS on website" feature enabled. All standard paths
# (/feed, /feed/, /rss, /rss.xml, /feed.xml, /atom.xml, /index.xml) 404.
# Kyle Poyar is intentionally omitted from PRIMARY_SOURCES rather than
# shipping a URL that isn't verified to work -- see task-2-report.md.
PRIMARY_SOURCES = [
    {"name": "Arvid Kahl", "feed_url": "https://thebootstrappedfounder.com/feed"},
    {"name": "Jason Lemkin", "feed_url": "https://www.saastr.com/feed/"},
    {"name": "Emily Kramer & Kathleen Estreich", "feed_url": "https://newsletter.mkt1.co/feed"},
    {"name": "Lenny Rachitsky", "feed_url": "https://www.lennysnewsletter.com/feed"},
    {"name": "Rand Fishkin", "feed_url": "https://sparktoro.com/blog/feed"},
    {"name": "Pieter Levels", "feed_url": "https://levels.io/rss/"},
]

FALLBACK_SOURCES = [
    {"name": "Marc Lou", "feed_url": "https://rss.beehiiv.com/feeds/eFrYnr889a.xml"},
    {"name": "Tony Dinh", "feed_url": "https://news.tonydinh.com/feed"},
    {"name": "Indie Hackers", "feed_url": "https://feed.indiehackers.world/posts.rss"},
    {"name": "Justin Jackson", "feed_url": "https://justinjackson.ca/feed"},
    {"name": "Nathan Barry", "feed_url": "https://nathanbarry.com/feed"},
]
