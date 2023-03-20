Added support for static deltas. The static deltas are automatically computed for synced and
imported repositories. This behaviour is enabled by default. Set ``compute_delta`` to ``False``
in a corresponding repository if there is no need to compute the static deltas between the last
two commits.
