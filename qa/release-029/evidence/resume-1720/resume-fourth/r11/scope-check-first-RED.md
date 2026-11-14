# R11 scope observer first check failed — preserved

The parent first scope-check one-liner exited1 with StopIteration before writing a receipt. It assumed a For node directly inside harvest_palettes; the actual source has the raw-wire observation Try directly in the function body at line105. No product/test/harvest bytes were modified to resolve this verifier-only AST locator.

Continuation uses the actual precise Try (containing Import) and still requires inverse byte-for-byte equality against the saved original harvest file, plus unchanged all37 product/App old tests/old Python source SHA. The original failed tool output is retained in this conversation; this note is attribution, not a substituted success receipt.
