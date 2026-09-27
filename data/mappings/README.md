# Field dictionaries and private configuration

A field dictionary declares how department columns map to entities and measures, which entities may be joined, and how values are aggregated. A missing declaration is a configuration question; a model must not invent it.

## Dictionary files

`field-dictionary.example.yaml` and the industry-specific examples are demonstration configurations. The default live path is `data/mappings/field-dictionary.yaml`, which is ignored by Git. Override it with `FIELD_DICTIONARY_PATH` when storing configuration elsewhere.

The native dictionary tools support two drafting routes: import a structured dictionary table, or propose entries from bounded column-profile statistics. A person must accept, amend or reject each entry before publication. Publishing creates a version for later imports; existing batches keep their frozen dictionary snapshots.

## Main sections

| Section | Meaning |
| --- | --- |
| `columns` | Department column names mapped to declared entity kinds |
| `relations` | Explicit relations between entity identifiers |
| `measures` | Numeric column names mapped to measure names |
| `rollups` | Aggregation rules such as `sum`, `average` or `period_end` |
| `derived` | Declared calculations from existing measures |
| `account_classes` | Explicit classification of revenue and cost accounts |

```yaml
columns:
  production:
    sku: sku
  procurement:
    material: raw_material
relations:
  - source: sku:sku-a1
    target: raw_material:rm-alu-6061
    relation: consumes
    note: Example material mapping
measures:
  procurement:
    unit_price: unit_price
    qty: purchase_quantity
rollups:
  purchase_quantity: sum
derived:
  purchase_amount:
    product: [unit_price, purchase_quantity]
```

Use the complete checked-in examples as a starting point. Review field names, units, currencies, dates, joining keys and aggregation with the data owner. A unit price is not an amount, and unconfigured currency conversion must not be guessed.

## Access policy and seats

`access-control.example.yaml` declares the role structure using placeholder wiki-space IDs. Copy it to the ignored `access-control.yaml`, fill in your own IDs and review role grants. Alternatively set `ACCESS_CONTROL_PATH` to a private external path. Missing or invalid access policy fails closed.

`seats.example.yaml` illustrates the seat registry. Generate actual paths and ports on the host with `scripts/provision_seat.sh --init N`; keep the resulting `seats.yaml` and person-to-seat assignments private.

See [Deployment](../../docs/deployment.md) for instance configuration and [Architecture](../../docs/architecture.md) for authorization boundaries.
