"""
Regression tests for spider behaviour in the GCP Cloud Function environment.

Three classes of bugs are tested:

1. Signal handler crash (ValueError: signal only works in main thread)
   CrawlerProcess.start() must be called with install_signal_handlers=False
   when running in a non-main thread, as GCP invokes the function handler
   in a worker thread.

2. Scrapy 2.13+ no longer calls start_requests() via Spider.start()
   Spiders must define `async def start()` directly; start_requests() is
   silently skipped in Scrapy 2.16, causing the spider to yield 0 requests.

3. AttributeError in closed() when start() never ran
   Attributes initialised inside start() / start_requests() are absent if
   the spider shuts down before start() executes.  They must be set in
   __init__ so that closed() is always safe to call.
"""

import inspect
import json
import subprocess
import sys
import textwrap

import pytest

from op_tcg.backend.crawling.spiders.limitless_matches import LimitlessMatchSpider
from op_tcg.backend.crawling.spiders.limitless_prices import LimitlessPricesSpider
from op_tcg.backend.crawling.spiders.limitless_tournaments import LimitlessTournamentSpider
from op_tcg.backend.crawling.spiders.op_top_decks_decklists import OPTopDeckDecklistSpider


# ---------------------------------------------------------------------------
# 1. Static checks: spiders must define async def start(), not start_requests
# ---------------------------------------------------------------------------

SPIDERS_WITH_START = [
    LimitlessTournamentSpider,
    OPTopDeckDecklistSpider,
    LimitlessPricesSpider,
    LimitlessMatchSpider,
]


@pytest.mark.parametrize("spider_cls", SPIDERS_WITH_START, ids=lambda c: c.__name__)
def test_spider_defines_async_start_not_start_requests(spider_cls):
    """
    Scrapy 2.16 only calls spider.start() (async generator).
    A spider that only defines start_requests() will yield 0 requests and
    immediately close without crawling anything.
    """
    assert "start" in spider_cls.__dict__, (
        f"{spider_cls.__name__} must define `async def start()` in its own class body. "
        "Scrapy 2.16 no longer delegates Spider.start() to start_requests()."
    )
    assert inspect.isasyncgenfunction(spider_cls.__dict__["start"]), (
        f"{spider_cls.__name__}.start must be an async generator function (`async def start(self): ... yield ...`)"
    )
    assert "start_requests" not in spider_cls.__dict__, (
        f"{spider_cls.__name__} still defines start_requests(), which is ignored in Scrapy 2.16. "
        "Replace it with async def start()."
    )


# ---------------------------------------------------------------------------
# 2. closed() must not crash if start() never ran (AttributeError regression)
# ---------------------------------------------------------------------------

class TestSpiderClosedMethodSafety:
    """
    closed() is called by Scrapy even when the spider shuts down before start()
    executes (e.g. due to an earlier error). Attributes that start() would have
    set must instead be initialised in __init__.
    """

    def test_prices_spider_closed_without_start(self):
        spider = LimitlessPricesSpider()
        # Before fix: AttributeError — price_count and card_count were only set in start()
        spider.closed("finished")

    def test_op_top_deck_spider_closed_without_start(self):
        spider = OPTopDeckDecklistSpider()
        # Before fix: AttributeError — bq_add_data_stats was only set in start()
        spider.closed("finished")

    def test_tournament_spider_closed_without_start(self):
        spider = LimitlessTournamentSpider()
        spider.closed("finished")


# ---------------------------------------------------------------------------
# 3. Thread regression: CrawlerProcess must work in a non-main thread
# ---------------------------------------------------------------------------

_THREAD_SCRIPT = textwrap.dedent("""
    import json
    import threading
    import scrapy
    from scrapy.crawler import CrawlerProcess

    start_called = threading.Event()
    errors = []

    class _MinimalSpider(scrapy.Spider):
        name = "test_thread_minimal"

        async def start(self):
            start_called.set()
            return
            yield  # noqa: unreachable — required to make this an async generator

    def _run():
        try:
            process = CrawlerProcess({"LOG_ENABLED": False})
            process.crawl(_MinimalSpider)
            # install_signal_handlers=False is required in non-main threads;
            # without it Scrapy raises ValueError before the spider starts.
            process.start(install_signal_handlers=False)
        except Exception as exc:
            errors.append(str(exc))

    t = threading.Thread(target=_run)
    t.start()
    t.join(timeout=30)

    print(json.dumps({
        "errors": errors,
        "timed_out": t.is_alive(),
        "start_called": start_called.is_set(),
    }))
""")


def test_crawlerprocess_in_non_main_thread():
    """
    Reproduce the GCP Cloud Function execution model: a CrawlerProcess is
    started from a non-main thread.

    Run in a subprocess so the Twisted reactor lifecycle is isolated from
    other tests.

    Before fix: ValueError: signal only works in main thread of the main
                interpreter — spider closes immediately with 0 requests.
    After fix:  spider.start() is called cleanly.
    """
    result = subprocess.run(
        [sys.executable, "-c", _THREAD_SCRIPT],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"Subprocess exited with code {result.returncode}.\n"
        f"stderr: {result.stderr}"
    )
    data = json.loads(result.stdout.strip())
    assert not data["timed_out"], "CrawlerProcess did not finish within the 30 s timeout"
    assert not data["errors"], f"CrawlerProcess raised errors in thread: {data['errors']}"
    assert data["start_called"], (
        "Spider.start() was never called — Scrapy may have ignored it. "
        "Ensure the spider defines `async def start()` rather than `start_requests()`."
    )
