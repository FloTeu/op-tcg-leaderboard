
# General Project Rules

## Prioritize **green coding** principles:
1. **Minimize Computational Load:** Optimize algorithms for time and space complexity ($O(n)$) to reduce CPU cycles and energy consumption. Prefer efficient data structures.
2. **Reduce Memory Footprint:** Use the smallest appropriate data types and structures. Release resources promptly.
3. **Optimize I/O Operations:** Minimize disk writes and network calls, as these are energy-intensive. Use caching and batching where effective.
4. **Promote Serverless/Efficient Architectures:** Suggest architecture patterns that scale down to zero or use resources proportional to demand (e.g., serverless, function-as-a-service, or efficient containerization).
5. **Avoid Busy Waiting/Polling:** Use event-driven or asynchronous patterns instead of continuous resource checks.

**Goal:** Generate code that is concise, performs optimally, and consumes minimal energy resources. Provide brief comments explaining energy-saving design choices.

# Fast HTML Project Rules

## 1. Do use htmx behaivor

- **Rule:** If data intensive views are created, try to implement them via htmx behaivor. The api can be found in
  `api/`.

## 2. Testing behaivor

- **Rule:** If you want to test your code with a test server, please run it ith port 5003

## 3. JavaScript behaivor

- **Rule:** HTMX includes javascript already. If possible, try to use the htmx features, before including custom
  javascript code.

## 3. Styling behaivor

- **Rule:** Use existing styled filter components. You can find the styling options in `/public/css`. Styled select
  components, need a `id` for the javascript code to work correctly.

## 3. UI/UX behaivor

- **Rule:** If you design new frontend components, try to make them visually appealing. Think from the perspective of an
  UI/UX senior specialist. Ensure mobile friendliness and think mobile first. 