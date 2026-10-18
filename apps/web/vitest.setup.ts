import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(() => cleanup());

// jsdom lacks scrollIntoView
Element.prototype.scrollIntoView = () => {};

// Lets Testing Library detect vitest fake timers (it only looks for a `jest` global).
(globalThis as Record<string, unknown>).jest = { advanceTimersByTime: (ms: number) => vi.advanceTimersByTime(ms) };
