# Phase 1 health metric dictionary

Status: **APPROVED CONTRACT for HS-002; documentation only.** These are technical data semantics, not clinical normal/risk thresholds. No clinical threshold, diagnosis, alert, or prediction is defined here.

## Shared rules

Measurements are user-owned observations. `measured_at` records when the observation occurred; `recorded_at` is the server ingestion time. Submitted `measured_at` values require an RFC 3339 offset and are normalized to UTC. Canonical units are the only accepted MVP input units. A missing value is never represented by zero.

All manual inputs use `source: "manual"`. The accepted numeric precision, plausible technical bounds, future-time tolerance, duplicate policy, and note length are **PENDING HS-008**. Those controls must reject malformed or impossible storage values without claiming a clinical interpretation.

## Dictionary

| Metric | Value shape | Canonical unit | Context | Input/derivation |
|---|---|---|---|---|
| `heart_rate` | integer | `bpm` | null | Manual input |
| `blood_pressure` | `{ "systolic": integer, "diastolic": integer }` | `mmHg` | null | One paired manual observation |
| `weight` | decimal | `kg` | null | Manual input; authoritative weight source |
| `bmi` | decimal | `kg/m2` | null | Read-only derived projection; never accepted as input |
| `blood_glucose` | decimal | `mg/dL` | `fasting`, `postprandial`, `random`, or `unknown` | Manual input; context required |
| `sleep_duration` | integer | `min` | null | Manual input; integer minutes |
| `physical_activity_duration` | integer | `min` | null | Manual input; integer minutes |

Metric and unit pairs are fixed. Clients do not submit a display-unit conversion or an arbitrary unit string. A future expansion requires an approved dictionary revision and coordinated consumer update.

## Typed examples

```json
{
  "metric": "heart_rate",
  "value": 68,
  "unit": "bpm",
  "context": null,
  "measured_at": "2026-09-12T07:30:00.000Z",
  "source": "manual",
  "note": null
}
```

```json
{
  "metric": "blood_pressure",
  "value": { "systolic": 118, "diastolic": 76 },
  "unit": "mmHg",
  "context": null,
  "measured_at": "2026-09-12T07:30:00.000Z",
  "source": "manual",
  "note": null
}
```

```json
{
  "metric": "blood_glucose",
  "value": 92.5,
  "unit": "mg/dL",
  "context": "fasting",
  "measured_at": "2026-09-12T07:30:00.000Z",
  "source": "manual",
  "note": null
}
```

```json
{
  "metric": "sleep_duration",
  "value": 450,
  "unit": "min",
  "context": null,
  "measured_at": "2026-09-12T06:30:00.000Z",
  "source": "manual",
  "note": null
}
```

## Weight and BMI

A `weight` measurement is the authoritative record. Profile and dashboard responses may expose the latest weight as a read-only projection with its observation time. They must not maintain an independently editable profile weight.

BMI is derived from the latest weight and profile height using `weight_kg / (height_m × height_m)`. The result records the source weight measurement ID and is null if either input is absent. The API rounds the projection to two decimal places. `POST /api/v1/measurements` rejects `metric: "bmi"`.

## Collections and nullability

`GET /api/v1/measurements?cursor=` returns:

```json
{
  "items": [],
  "next_cursor": null
}
```

An empty list means no matching observations. Optional scalar metadata can be null. Core discriminator fields (`metric`, `value`, `unit`, `measured_at`, `source`) are required and cannot be null. Observations are immutable in the MVP. Repeated submissions remain distinct observations because the API has no client idempotency key; clients should avoid retrying a successful write. Deletion and correction are outside HS-008. Lists use an opaque cursor, newest observation first, with at most 50 items per page.
