/* SSE payload types for GET /v1/events, re-exported from the generated
schema types under their wire names. OpenAPI cannot describe what flows
inside an SSE stream, so the export script folds these models into
components.schemas and the pairing of event name to payload lives at the
addEventListener call sites. */

import type { components } from './types.gen';

export type RunStartedEvent = components['schemas']['RunStartedEvent'];
export type RunProgressEvent = components['schemas']['RunProgressEvent'];

/* A run that died before producing a result carries error with null
counts. A completed run carries counts with null error, even when its own
status is "failed". The two paths are told apart by which field is set,
never by the status string. */
export type RunFinishedEvent = components['schemas']['RunFinishedEvent'];
