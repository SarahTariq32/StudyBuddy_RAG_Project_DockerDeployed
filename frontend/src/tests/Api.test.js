// import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// import { askQuestion } from "../api/chat";
// import {
//   listPDFs,
//   uploadPDF,
//   deletePDF,
//   renamePDF,
// } from "../api/documents";
// import {
//   fetchOpsDashboard,
//   fetchOpsTraces,
// } from "../api/ops";

// describe("API Tests", () => {
//   beforeEach(() => {
//     vi.restoreAllMocks();
//     localStorage.clear();
//     global.fetch = vi.fn();
//   });

//   afterEach(() => {
//     vi.restoreAllMocks();
//   });

//   // ---------------- CHAT ----------------

//   it("asks a question successfully", async () => {
//     fetch.mockResolvedValueOnce({
//       ok: true,
//       json: async () => ({
//         answer: "AI Answer",
//       }),
//     });

//     const res = await askQuestion("Hello", "session1");

//     expect(res.answer).toBe("AI Answer");
//     expect(fetch).toHaveBeenCalled();
//   });

//   it("throws when ask endpoint returns error", async () => {
//     fetch.mockResolvedValueOnce({
//       ok: false,
//       status: 500,
//       statusText: "Server Error",
//       json: async () => ({
//         detail: "Something failed",
//       }),
//     });

//     await expect(
//       askQuestion("Hello", "session1")
//     ).rejects.toThrow();
//   });

//   // ---------------- DOCUMENTS ----------------

//   it("lists PDFs", async () => {
//     fetch.mockResolvedValueOnce({
//       ok: true,
//       json: async () => [
//         { id: 1, filename: "AI.pdf" },
//       ],
//     });

//     const docs = await listPDFs();

//     expect(docs).toHaveLength(1);
//     expect(docs[0].filename).toBe("AI.pdf");
//   });

//   it("uploads PDF successfully", async () => {
//     fetch.mockResolvedValueOnce({
//       ok: true,
//       json: async () => ({
//         success: true,
//       }),
//     });

//     const file = new File(
//       ["dummy"],
//       "sample.pdf",
//       {
//         type: "application/pdf",
//       }
//     );

//     const res = await uploadPDF(file);

//     expect(res.success).toBe(true);
//   });

//   it("returns duplicate upload response", async () => {
//     fetch.mockResolvedValueOnce({
//       ok: false,
//       status: 409,
//       json: async () => ({
//         detail: "Duplicate",
//       }),
//     });

//     const file = new File(
//       ["dummy"],
//       "sample.pdf",
//       {
//         type: "application/pdf",
//       }
//     );

//     const res = await uploadPDF(file);

//     expect(res.duplicate).toBe(true);
//   });

//   it("deletes PDF", async () => {
//     fetch.mockResolvedValueOnce({
//       ok: true,
//     });

//     await expect(
//       deletePDF(5)
//     ).resolves.toBeUndefined();
//   });

//   it("renames PDF successfully", async () => {
//     fetch.mockResolvedValueOnce({
//       ok: true,
//       headers: {
//         get: () => "application/json",
//       },
//       json: async () => ({
//         success: true,
//       }),
//     });

//     const res = await renamePDF(
//       1,
//       "New Name.pdf"
//     );

//     expect(res.success).toBe(true);
//   });

//   // ---------------- OPS ----------------

//   it("loads operations dashboard", async () => {
//     fetch.mockResolvedValueOnce({
//       ok: true,
//       json: async () => ({
//         enabled: true,
//       }),
//     });

//     const data =
//       await fetchOpsDashboard();

//     expect(data.enabled).toBe(true);
//   });

//   it("loads traces", async () => {
//     fetch.mockResolvedValueOnce({
//       ok: true,
//       json: async () => ({
//         traces: [],
//       }),
//     });

//     const data =
//       await fetchOpsTraces();

//     expect(data.traces).toEqual([]);
//   });
// });



import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import { askQuestion } from "../api/chat";
import {
  listPDFs,
  uploadPDF,
  deletePDF,
  renamePDF,
} from "../api/documents";
import {
  fetchOpsDashboard,
  fetchOpsTraces,
} from "../api/ops";

describe("Frontend API Tests", () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    global.fetch = vi.fn();

    localStorage.clear();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ===================================================
  // CHAT API
  // ===================================================

  it("should send a question successfully", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        answer: "Artificial Intelligence",
        sources: [],
      }),
    });

    const result = await askQuestion(
      "What is AI?",
      "session-1"
    );

    expect(fetch).toHaveBeenCalledTimes(1);

    expect(result.answer).toBe(
      "Artificial Intelligence"
    );
  });

  it("should send POST request", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        answer: "OK",
      }),
    });

    await askQuestion(
      "Hello",
      "session-1"
    );

    expect(fetch.mock.calls[0][1].method)
      .toBe("POST");
  });

  it("should send JSON body", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        answer: "OK",
      }),
    });

    await askQuestion(
      "Hello",
      "session-1"
    );

    const options = fetch.mock.calls[0][1];

    expect(options.headers["Content-Type"])
      .toContain("application/json");
  });

  it("should reject on server error", async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({
        detail: "Internal Error",
      }),
    });

    await expect(
      askQuestion("Hello", "session")
    ).rejects.toThrow();
  });

  it("should reject on network failure", async () => {
    fetch.mockRejectedValueOnce(
      new Error("Network Error")
    );

    await expect(
      askQuestion("Hello", "session")
    ).rejects.toThrow("Network Error");
  });

  it("should return parsed response", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        answer: "Paris",
        confidence: 0.95,
      }),
    });

    const result = await askQuestion(
      "Capital?",
      "abc"
    );

    expect(result.confidence).toBe(0.95);
  });

  it("should call fetch once", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        answer: "Done",
      }),
    });

    await askQuestion(
      "Hello",
      "session"
    );

    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("should preserve answer text", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        answer:
          "Machine learning is a subset of AI.",
      }),
    });

    const res = await askQuestion(
      "ML?",
      "1"
    );

    expect(res.answer).toContain(
      "Machine learning"
    );
  });

  // ===================================================
  // DOCUMENTS API
  // ===================================================

  it("should list PDFs", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [
        {
          id: 1,
          filename: "AI.pdf",
        },
      ],
    });

    const docs = await listPDFs();

    expect(docs.length).toBe(1);

    expect(docs[0].filename).toBe(
      "AI.pdf"
    );
  });

  it("should return empty array", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    });

    const docs = await listPDFs();

    expect(docs).toEqual([]);
  });

  it("should upload PDF", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        id: 15,
      }),
    });

    const file = new File(
      ["pdf"],
      "book.pdf",
      {
        type: "application/pdf",
      }
    );

    const result =
      await uploadPDF(file);

    expect(result.success).toBe(true);
  });

  it("should send FormData while uploading", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
      }),
    });

    const file = new File(
      ["abc"],
      "sample.pdf",
      {
        type: "application/pdf",
      }
    );

    await uploadPDF(file);

    const body = fetch.mock.calls[0][1].body;

    expect(body instanceof FormData).toBe(true);
  });
    it("should detect duplicate upload", async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: async () => ({
        detail: "Document already exists",
      }),
    });

    const file = new File(
      ["pdf"],
      "duplicate.pdf",
      { type: "application/pdf" }
    );

    const result = await uploadPDF(file);

    expect(result.duplicate).toBe(true);
  });

  it("should throw upload error", async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({
        detail: "Upload failed",
      }),
    });

    const file = new File(
      ["pdf"],
      "book.pdf",
      { type: "application/pdf" }
    );

    await expect(
      uploadPDF(file)
    ).rejects.toThrow();
  });

  it("should delete a PDF", async () => {
    fetch.mockResolvedValueOnce({
        ok: true,
    });

    await expect(
        deletePDF(12)
    ).resolves.toBeUndefined();

    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("should call DELETE request", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
      }),
    });

    await deletePDF(5);

    expect(fetch.mock.calls[0][1].method)
      .toBe("DELETE");
  });

  it("should reject delete failures", async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({
        detail: "Not Found",
      }),
    });

    await expect(
      deletePDF(100)
    ).rejects.toThrow();
  });

  it("should rename PDF", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      headers: {
        get: () => "application/json",
      },
      json: async () => ({
        success: true,
      }),
    });

    const result = await renamePDF(
      1,
      "NewName.pdf"
    );

    expect(result.success).toBe(true);
  });

  it("should send PATCH or PUT request while renaming", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      headers: {
        get: () => "application/json",
      },
      json: async () => ({
        success: true,
      }),
    });

    await renamePDF(
      10,
      "Updated.pdf"
    );

    const method =
      fetch.mock.calls[0][1].method;

    expect(
      ["PATCH", "PUT", "POST"].includes(method)
    ).toBe(true);
  });

  it("should reject invalid rename", async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({
        detail: "Invalid filename",
      }),
    });

    await expect(
      renamePDF(1, "")
    ).rejects.toThrow();
  });

  it("should reject rename server error", async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({
        detail: "Internal Error",
      }),
    });

    await expect(
      renamePDF(
        1,
        "abc.pdf"
      )
    ).rejects.toThrow();
  });

  it("should preserve renamed filename", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      headers: {
        get: () => "application/json",
      },
      json: async () => ({
        filename: "Updated.pdf",
      }),
    });

    const result = await renamePDF(
      1,
      "Updated.pdf"
    );

    expect(result.filename)
      .toBe("Updated.pdf");
  });

  it("should call fetch during rename", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      headers: {
        get: () => "application/json",
      },
      json: async () => ({
        success: true,
      }),
    });

    await renamePDF(
      1,
      "Book.pdf"
    );

    expect(fetch)
      .toHaveBeenCalledTimes(1);
  });

  // ===================================================
  // OPERATIONS API
  // ===================================================

  it("should fetch operations dashboard", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        enabled: true,
      }),
    });

    const result =
      await fetchOpsDashboard();

    expect(result.enabled)
      .toBe(true);
  });

  it("should fetch traces", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        traces: [],
      }),
    });

    const result =
      await fetchOpsTraces();

    expect(result.traces)
      .toEqual([]);
  });

  it("should reject dashboard errors", async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({
        detail: "Dashboard Error",
      }),
    });

    await expect(
      fetchOpsDashboard()
    ).rejects.toThrow();
  });
    it("should call fetch while loading dashboard", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        enabled: true,
      }),
    });

    await fetchOpsDashboard();

    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("should preserve dashboard data", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        enabled: true,
        total_requests: 120,
      }),
    });

    const result = await fetchOpsDashboard();

    expect(result.total_requests).toBe(120);
  });

  it("should preserve traces", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        traces: [
          {
            id: 1,
            question: "Hello",
          },
        ],
      }),
    });

    const result = await fetchOpsTraces();

    expect(result.traces.length).toBe(1);
    expect(result.traces[0].question).toBe("Hello");
  });

  it("should reject trace errors", async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({
        detail: "Trace Error",
      }),
    });

    await expect(
      fetchOpsTraces()
    ).rejects.toThrow();
  });

  it("should reject network failures", async () => {
    fetch.mockRejectedValueOnce(
      new Error("Network Failure")
    );

    await expect(
      fetchOpsDashboard()
    ).rejects.toThrow("Network Failure");
  });

  it("should return parsed dashboard json", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        requests: 55,
        latency: 120,
      }),
    });

    const result = await fetchOpsDashboard();

    expect(result.requests).toBe(55);
    expect(result.latency).toBe(120);
  });

  it("should return parsed traces json", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        traces: [],
      }),
    });

    const result = await fetchOpsTraces();

    expect(Array.isArray(result.traces)).toBe(true);
  });

  it("should call fetch exactly once for traces", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        traces: [],
      }),
    });

    await fetchOpsTraces();

    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("should handle empty dashboard response", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    const result = await fetchOpsDashboard();

    expect(result).toEqual({});
  });

  it("should handle empty traces response", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    const result = await fetchOpsTraces();

    expect(result).toEqual({});
  });

  it("should reject malformed server response", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => {
        throw new Error("Invalid JSON");
      },
    });

    await expect(
      fetchOpsDashboard()
    ).rejects.toThrow("Invalid JSON");
  });

  it("should reject malformed traces response", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => {
        throw new Error("Invalid JSON");
      },
    });

    await expect(
      fetchOpsTraces()
    ).rejects.toThrow("Invalid JSON");
  });
});