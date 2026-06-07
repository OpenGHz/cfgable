"""Small vendored helpers, kept here to avoid extra runtime dependencies."""


def get_in(keys, coll, default=None, no_default=False):
    """Return ``coll[k0][k1][...]`` following the sequence ``keys``.

    Vendored equivalent of ``toolz.dicttoolz.get_in``. On a missing key/index
    (``KeyError``, ``IndexError``, ``TypeError``) return ``default`` — unless
    ``no_default`` is set, in which case the original exception propagates.
    """
    try:
        out = coll
        for key in keys:
            out = out[key]
        return out
    except (KeyError, IndexError, TypeError):
        if no_default:
            raise
        return default
