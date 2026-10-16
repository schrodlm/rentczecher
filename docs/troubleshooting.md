# Troubleshooting

## A portal suddenly finds nothing

Usually the portal changed its pages or the ids it searches by. A dry run of
the engine shows which portal it is:

```bash
engine/.venv/bin/rentczecher --dry-run
```

If a place that used to return listings now returns none, the portal may have
renumbered its places, and the gazetteer needs a rebuild, see
[development.md](development.md#the-gazetteer).

## Sreality answers 404 to everything

Sreality refuses some networks, datacenter and VPN connections among them,
while its homepage still loads. rentczecher then reports Sreality unreachable
and scans the other portals. It is not a bug, and rentczecher does not try to
get past it. The details are in [portals/sreality.md](portals/sreality.md).
