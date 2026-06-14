# Source for 202-retry pattern: https://stackoverflow.com/a/79812356 (Manu310, CC BY-SA 4.0)

import asyncio
import random

from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message


class Retry202Middleware(RetryMiddleware):
    """Retries requests that return HTTP 202 with exponential back-off.

    202 ("Accepted") is used by some anti-bot systems (e.g. Sucuri) as a
    "please wait and retry" signal rather than a permanent error. This middleware
    detects that, waits an increasing delay, then re-queues the request up to
    MAX_RETRIES times. After exhausting retries it passes the 202 response
    through to the spider callback so the body can be inspected in logs.

    On each retry a 'Connection: close' header is added to force Twisted to
    tear down the TCP socket to the proxy. Rotating proxy providers (e.g.
    Webshare backbone) tie the exit IP to the TCP session, so a new connection
    guarantees a fresh exit IP rather than reusing the blocked one.
    """

    DEFAULT_DELAY = 3   # seconds for first retry
    MAX_RETRIES = 5

    def __init__(self, settings):
        super().__init__(settings)
        # Override the base class limit so _retry() honours MAX_RETRIES,
        # not the global RETRY_TIMES setting (default: 2).
        self.max_retry_times = self.MAX_RETRIES

    async def process_response(self, request, response, spider):
        if response.status != 202:
            return response

        retries = request.meta.get('retry_times', 0)
        if retries >= self.MAX_RETRIES:
            spider.logger.warning(
                f"Retry202Middleware: gave up on {response.url} after "
                f"{self.MAX_RETRIES} consecutive 202 responses — "
                f"passing response through (body length: {len(response.body)})"
            )
            return response

        delay = self.DEFAULT_DELAY * (2 ** retries) + random.uniform(0, 2)
        spider.logger.info(f"Body: {response.body}")
        spider.logger.info(
            f"Retry202Middleware: 202 on {response.url}, "
            f"ip address {response.ip_address}, "
            f"retry {retries + 1}/{self.MAX_RETRIES} in {delay:.1f}s"
        )

        await asyncio.sleep(delay)

        reason = response_status_message(response.status)
        new_request = self._retry(request, reason)
        if new_request:
            # Force Twisted to close the TCP connection to the proxy after this
            # response. Rotating proxies tie exit IPs to TCP sessions, so
            # tearing down the socket ensures the next retry opens a fresh
            # connection and receives a new exit IP from the proxy pool.
            new_request.headers['Connection'] = 'close'
            return new_request

        return response