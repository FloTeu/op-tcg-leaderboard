
# General Project Rules

## Prioritize **green coding** principles:
1. **Minimize Computational Load:** Optimize algorithms for time and space complexity ($O(n)$) to reduce CPU cycles and energy consumption. Prefer efficient data structures.
2. **Reduce Memory Footprint:** Use the smallest appropriate data types and structures. Release resources promptly.
3. **Optimize I/O Operations:** Minimize disk writes and network calls, as these are energy-intensive. Use caching and batching where effective.
4. **Promote Serverless/Efficient Architectures:** Suggest architecture patterns that scale down to zero or use resources proportional to demand (e.g., serverless, function-as-a-service, or efficient containerization).
5. **Avoid Busy Waiting/Polling:** Use event-driven or asynchronous patterns instead of continuous resource checks.

**Goal:** Generate code that is concise, performs optimally, and consumes minimal energy resources. Provide brief comments explaining energy-saving design choices.

# Fast HTML Project Rules

## 1. Do use htmx behavior

- **Rule:** If data intensive views are created, try to implement them via htmx behaivor. The api can be found in
  `api/`.

## 2. Testing behavior

- **Rule:** Do not test frontend code by starting a local server. Use unit tests instead. You can find existing tests in
  `tests/`.

## 3. JavaScript behavior

- **Rule:** HTMX includes javascript already. If possible, try to use the htmx features, before including custom
  javascript code.

## 3. Styling behavior

- **Rule:** Use existing styled filter components. You can find the styling options in `/public/css`. Styled select
  components, need a `id` for the javascript code to work correctly.

## 3. UI/UX behavior

- **Rule:** If you design new frontend components, try to make them visually appealing. Think from the perspective of an
  UI/UX senior specialist. Ensure mobile friendliness and think mobile first.

# General Project Rules
- **Rule**: Always follow best practices for code quality, readability, and maintainability.
- **Rule**: Do not read files multiple time if you have already read it.
- **Rule**:  If you add new code, check if  existing code might need to be refactored to improve overall quality and maintainability.
- **Rule**:  Do not write a final markdown report at the end of a task.