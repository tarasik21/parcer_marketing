# Static RSS source configuration for the digest bot.
#
# PRIMARY_SOURCES: confirmed SaaS-marketing authors the bot prefers.
# FALLBACK_SOURCES: bootstrapped-SaaS-founder feeds used when the primary
# sources have nothing new to report (see Task 7's orchestrator).
#
# All URLs below were fetched and confirmed to return valid RSS/Atom XML
# with recent (non-stale) entries as of 2026-07-28.

PRIMARY_SOURCES = [
    {"name": "Arvid Kahl", "feed_url": "https://thebootstrappedfounder.com/feed"},
    {"name": "Jason Lemkin", "feed_url": "https://www.saastr.com/feed/"},
    {"name": "Elena Verna", "feed_url": "https://www.elenaverna.com/feed"},
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
