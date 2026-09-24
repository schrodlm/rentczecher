/* Pulls in jest-dom's Vitest matcher type augmentation. Living under src/
puts it in svelte-check's TS program, which the repo-root vitest-setup.ts
(vitest's own convention for the runtime import) is not part of. */
import '@testing-library/jest-dom/vitest';
