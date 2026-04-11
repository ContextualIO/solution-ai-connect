---
name: solai-data-modeler
description: Design and validate Contextual.io Object Type schemas. Use when creating new object types, adding properties, defining relations, or reviewing schema correctness. Do NOT use for flow changes — use solai-flow-editor for those.
---

# SolAI Data Modeler

Use this skill to design, validate, and deploy Object Type schemas on the Contextual.io platform.

## Schema rules (non-negotiable)

### Structure
- All schemas must have a top-level `primaryKey` property whose value is the name of the primary key field
- ALL schemas must have at least one non-generated required property (e.g. `name`)
- Do NOT mark auto-generated fields (UUIDs, timestamps) as required — they don't exist at validation time
- Do not use JS-style comments (`//`) — use `description` properties or `$comment` instead
- All object type IDs must use only lowercase letters, numbers, and dashes — suggest a corrected alternative if the user requests otherwise
- Only generate valid schemas — if asked to produce something invalid, decline politely and explain why

### Primary keys
- Unless told otherwise, ALL new schemas use an auto-generated UUID for the primary key:
  ```json
  "id": { "type": "string", "generate": { "type": "uuid", "format": "v4" } }
  ```
- Auto-generated primary keys must NOT appear in the `required` array
- You CANNOT propose changes to a primary key for an object type that already exists or has been saved — only the default (unsaved) schema may have its primaryKey changed

### Default schema baseline
When starting from scratch:
```json
{
  "primaryKey": "id",
  "type": "object",
  "$comment": "Purpose of this object type",
  "properties": {
    "id": { "type": "string", "generate": { "type": "uuid", "format": "short" } },
    "name": { "type": "string", "minLength": 1 },
    "description": { "type": "string", "minLength": 1 }
  },
  "required": ["name"]
}
```

### Platform-provided `_metaData` (do not replicate in schema)

Every record automatically receives a `_metaData` envelope from the platform — it is never part of the schema definition:

```json
"_metaData": {
  "createdAt": "...",
  "updatedAt": "...",
  "hash": "...",
  "id": "...",
  "schema": "native-object:<type-id>",
  "type": "custom",
  "version": 1,
  "secrets": []
}
```

**Never add `createdAt`, `updatedAt`, `hash`, `version`, or `secrets` to a schema** — they are already present on every record via `_metaData`. Reference them in flow logic as `msg.payload._metaData.createdAt` etc.

### Schema-defined auto-generated fields
Only add these when you need a generated value *inside* the record body itself (separate from `_metaData`), for example a secondary timestamp or a display-facing date:
```json
"publishedAt": { "type": "string", "generate": { "type": "date-time" } }
```
Do not mark these as required.

### Relations
- The `relations` section is ALWAYS a top-level schema property — never nested inside a property definition
- Relations are defined on the CHILD object pointing TO the parent — never on the parent
- `typeRef` must ONLY reference the primaryKey path of the parent: `"native-object:<type-id>/<primaryKey>"`
- Do not allow `typeRef` to be set to anything other than the parent's primaryKey
- Example:
  ```json
  "relations": {
    "customer": {
      "typeRef": "native-object:customer/id",
      "localField": "customerId",
      "displayField": "name"
    }
  }
  ```

### Secret fields
- Designate sensitive string properties with `"secret": true` to encrypt and store in the key store
- Example:
  ```json
  "apiKey": { "type": "string", "description": "Encrypted API credential", "secret": true }
  ```

### Not supported
- Contextual does not support indexed/index fields — if a user asks about indexing, decline to add it and suggest they contact Contextual if indexing is a needed feature

## Documentation references

Use the `solai-knowledge` skill to verify platform behaviour before proposing anything uncertain. Prefer these specific doc paths:

| Topic | Doc path |
|-------|----------|
| Schema structure and JSON Schema features | `components-and-data/object-types/object-type-details/data-schema/README.md` |
| UUID generation formats and options | `components-and-data/object-types/object-type-details/data-schema/generated-properties/uuids.md` |
| Auto-generated date/time fields | `components-and-data/object-types/object-type-details/data-schema/generated-properties/dates-and-times.md` |
| primaryKey immutability rules | `components-and-data/object-types/object-type-details/data-schema/id-and-primarykey-permanence.md` |
| Secret fields | `components-and-data/object-types/object-type-details/data-schema/secret.md` |
| Validation patterns (enums, booleans, etc.) | `components-and-data/object-types/object-type-details/data-schema/frequently-used-validation.md` |
| Object type definition and relations | `components-and-data/object-types/object-type-details/definition.md` |
| Worked schema examples | `components-and-data/object-types/examples.md` |

## Workflow

1. Before proposing a schema, check if the object type already exists using `ctxl types get --type <type-id>` — this determines whether primaryKey changes are allowed
2. For any schema feature you are uncertain about, look it up in the docs above before proposing
3. Present the full proposed JSON schema for user review before any deployment
4. Once the user approves, hand off to the `/solai-cli` skill for deployment — do not attempt to run `ctxl` commands directly via Bash
5. After creation, confirm with `ctxl types get --type <type-id>` to verify the deployed schema matches intent
6. When designing related types, present all schemas together so relations can be reviewed as a set before any are deployed
