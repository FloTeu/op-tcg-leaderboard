# Source for 202-retry pattern: https://stackoverflow.com/a/79812356 (Manu310, CC BY-SA 4.0)

import asyncio
import random
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message

class Retry202Middleware(RetryMiddleware):
    """Retries requests that return HTTP 202 with exponential back-off.

    202 ("Accepted") is used by some anti-bot systems (e.g. Cloudflare) as a
    "please wait and retry" signal rather than a permanent error. This middleware
    detects that, waits an increasing delay, then re-queues the request up to
    MAX_RETRIES times. After exhausting retries it passes the 202 response
    through to the spider callback so the body can be inspected in logs.

    On each retry the proxy URL session ID is rotated so the provider assigns
    a fresh exit IP rather than reusing the blocked one.
    """

    DEFAULT_DELAY = 3   # seconds for first retry
    MAX_RETRIES = 5

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
            return new_request

        return response
