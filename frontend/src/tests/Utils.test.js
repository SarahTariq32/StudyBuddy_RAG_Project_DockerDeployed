import { describe, it, expect, beforeEach, vi } from "vitest";
import { getSessionId } from "../utils/session";

describe("Session Utils", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("returns an existing session id from localStorage", () => {
    localStorage.setItem("session_id", "existing-session");

    const id = getSessionId();

    expect(id).toBe("existing-session");
  });

  it("creates a new session id when one does not exist", () => {
    vi.spyOn(global.crypto, "randomUUID").mockReturnValue("generated-id");

    const id = getSessionId();

    expect(id).toBe("generated-id");
    expect(localStorage.getItem("session_id")).toBe("generated-id");
  });

  it("calls crypto.randomUUID only once for a new session", () => {
    const uuidSpy = vi
      .spyOn(global.crypto, "randomUUID")
      .mockReturnValue("uuid-123");

    getSessionId();

    expect(uuidSpy).toHaveBeenCalledTimes(1);
  });

  it("does not generate a new UUID when a session already exists", () => {
    localStorage.setItem("session_id", "saved-session");

    const uuidSpy = vi.spyOn(global.crypto, "randomUUID");

    const id = getSessionId();

    expect(id).toBe("saved-session");
    expect(uuidSpy).not.toHaveBeenCalled();
  });

  it("persists the generated session id", () => {
    vi.spyOn(global.crypto, "randomUUID").mockReturnValue("persisted-id");

    getSessionId();

    expect(localStorage.getItem("session_id")).toBe("persisted-id");
  });

  it("returns the same id across multiple calls", () => {
    vi.spyOn(global.crypto, "randomUUID").mockReturnValue("same-id");

    const first = getSessionId();
    const second = getSessionId();

    expect(first).toBe(second);
    expect(second).toBe("same-id");
  });
});