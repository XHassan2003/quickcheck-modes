# Intentional QuickCheck demonstration defects

This practice website intentionally contains seeded defects for a testing demonstration.
It is not intended for production use.

## Functional defects
1. Catalogue navigation and the homepage primary CTA point to `/demo/borrow`, a route that does not exist (404).
2. Login rejects the documented demo credentials `student / library123`.
3. Catalogue search always reports no results, including for known titles.

## UI / browser defects
4. Homepage book illustration points to a missing image (`/demo/books-missing.svg`).
5. Newsletter section has a fixed minimum width, causing horizontal overflow on narrow screens.
6. Contact page runs JavaScript against a missing element, producing a browser runtime error.

## Suggested demo sequence
- Open `http://127.0.0.1:8080/demo/` and run QuickCheck in **Both** mode.
- Test the broken Borrow a book link and inspect the failed navigation.
- Search for `Silent Sea` on the Catalogue page.
- Try the demo login credentials shown on the sign-in page.
- Open the homepage at a narrow viewport to show horizontal scrolling.
- Open Contact and inspect the browser console / QuickCheck findings.

To restore a clean version, use the previous redesigned ZIP or remove the intentional changes listed above.
