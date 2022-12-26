# jsonforms-bundle

We'd like to render a UI to let the user configure their crawl. This UI is powered
by JSON-Schema metadata, and rendered as a React component using the [JSONForms](https://jsonforms.io/)
library.

Datasette itself isn't React-based, so we build a standalone JS bundle that has a
well-defined API surface area. This bundle will get included in our plugin as
a static file.

It's all rather Rube Goldberg-y.

# Dev

`yarn build` to get a dev bundle, `NODE_ENV=production yarn build` to get a minified prod bundle.

`yarn watch` is useful in dev.
