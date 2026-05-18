import { describe, it, expect, beforeEach } from "vitest";
import { loadLevel, saveLevel, clearLevel, MIN_LEVEL, MAX_LEVEL } from "./level";

describe("level store", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns null when nothing is stored", () => {
    expect(loadLevel()).toBe(null);
  });

  it("round-trips a valid level", () => {
    saveLevel(5);
    expect(loadLevel()).toBe(5);
  });

  it("rejects out-of-range values on save", () => {
    saveLevel(0);
    expect(loadLevel()).toBe(null);
    saveLevel(MAX_LEVEL + 1);
    expect(loadLevel()).toBe(null);
  });

  it("rejects garbage on load", () => {
    localStorage.setItem("gradedGuitar.level", "not-a-number");
    expect(loadLevel()).toBe(null);
  });

  it("clears the stored level", () => {
    saveLevel(7);
    clearLevel();
    expect(loadLevel()).toBe(null);
  });

  it("accepts both bounds", () => {
    saveLevel(MIN_LEVEL);
    expect(loadLevel()).toBe(MIN_LEVEL);
    saveLevel(MAX_LEVEL);
    expect(loadLevel()).toBe(MAX_LEVEL);
  });
});
