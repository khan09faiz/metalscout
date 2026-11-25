# CI

`github-actions-tests.yml` runs the test suite on GitHub Actions. To enable it, move it to `.github/workflows/tests.yml`.
That push needs a token with the `workflow` scope: `gh auth refresh -s workflow`.
