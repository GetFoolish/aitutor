import { beforeEach, describe, expect, it, vi } from "vitest";

import { httpClient } from "../lib/http-client";
import { authAPI } from "../lib/auth-api";
import { apiUtils } from "../lib/api-utils";
import { TutorService, clearTokenCache } from "../features/tutor/tutor-service";


const { googleGenAiSpy, apiUtilsGetSpy } = vi.hoisted(() => ({
  googleGenAiSpy: vi.fn(),
  apiUtilsGetSpy: vi.fn(),
}));

vi.mock("@google/genai", () => ({
  GoogleGenAI: googleGenAiSpy,
}));

vi.mock("../lib/api-utils", () => ({
  apiUtils: {
    get: apiUtilsGetSpy,
  },
}));


describe("frontend auth+tutor smoke contract", () => {
  beforeEach(() => {
    clearTokenCache();
    vi.restoreAllMocks();
    googleGenAiSpy.mockImplementation(() => ({
      live: {
        connect: vi.fn(),
      },
    }));
    apiUtilsGetSpy.mockReset();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("System prompt", {
          status: 200,
          headers: { "Content-Type": "text/plain" },
        }),
      ),
    );
  });

  it("boots the auth current-user call with the provided bearer token", async () => {
    const fetchSpy = vi.spyOn(httpClient, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          user_id: "user-123",
          email: "student@example.com",
          name: "Student",
          age: 11,
          current_grade: "GRADE_5",
          user_type: "student",
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    const user = await authAPI.getCurrentUser("jwt-123");

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8003/auth/me",
      expect.objectContaining({
        headers: {
          Authorization: "Bearer jwt-123",
        },
      }),
    );
    expect(user.user_id).toBe("user-123");
  });

  it("boots tutor initialization through the ephemeral token path", async () => {
    vi.mocked(apiUtils.get).mockResolvedValue(
      new Response(
        JSON.stringify({
          token: "ephemeral-token",
          model: "models/test-live",
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    const tutorService = new TutorService();
    await tutorService.initialize();

    expect(apiUtils.get).toHaveBeenCalledWith(
      "http://localhost:8003/auth/gemini-token",
    );
    expect(global.fetch).toHaveBeenCalledWith("/ai_tutor_system_prompt.md");
    expect(googleGenAiSpy).toHaveBeenCalledWith({
      apiKey: "ephemeral-token",
      apiVersion: "v1alpha",
    });
  });
});
