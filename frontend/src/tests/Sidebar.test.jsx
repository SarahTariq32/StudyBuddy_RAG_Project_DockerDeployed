import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Sidebar from "../components/Sidebar";

vi.mock("../api/documents", () => ({
  listPDFs: vi.fn(),
  uploadPDF: vi.fn(),
}));

import { listPDFs, uploadPDF } from "../api/documents";

describe("Sidebar Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it("renders sidebar title", async () => {
    listPDFs.mockResolvedValue([]);

    render(<Sidebar />);

    expect(screen.getByText("Your PDFs")).toBeInTheDocument();
  });

  it("loads PDFs on mount", async () => {
    listPDFs.mockResolvedValue([
      {
        id: 1,
        filename: "AI.pdf",
        status: "ready",
      },
    ]);

    render(<Sidebar />);

    await waitFor(() => {
      expect(listPDFs).toHaveBeenCalled();
    });

    expect(screen.getByText("AI.pdf")).toBeInTheDocument();
  });

  it("shows loading initially", () => {
    listPDFs.mockImplementation(() => new Promise(() => {}));

    render(<Sidebar />);

    expect(
      screen.getByText(/Loading PDFs/i)
    ).toBeInTheDocument();
  });

  it("shows upload button", () => {
    listPDFs.mockResolvedValue([]);

    render(<Sidebar />);

    expect(
      screen.getByText("Upload PDF")
    ).toBeInTheDocument();
  });

  it("shows PDF count", async () => {
    listPDFs.mockResolvedValue([
      { id: 1, filename: "AI.pdf", status: "ready" },
      { id: 2, filename: "ML.pdf", status: "ready" },
    ]);

    render(<Sidebar />);

    await waitFor(() => {
      expect(screen.getByText("2/5")).toBeInTheDocument();
    });
  });

  it("calls upload when file selected", async () => {
    uploadPDF.mockResolvedValue({
      id: 3,
      filename: "New.pdf",
      status: "processing",
    });

    listPDFs.mockResolvedValue([]);

    const { container } = render(<Sidebar />);

    const input = container.querySelector(
      'input[type="file"]'
    );

    const file = new File(
      ["abc"],
      "New.pdf",
      {
        type: "application/pdf",
      }
    );

    await userEvent.upload(input, file);

    await waitFor(() => {
      expect(uploadPDF).toHaveBeenCalled();
    });
  });

  it("renders close button on mobile", () => {
    listPDFs.mockResolvedValue([]);

    render(
      <Sidebar
        isMobile={true}
        isOpen={true}
      />
    );

    expect(
      screen.getByLabelText(
        "Close PDFs sidebar"
      )
    ).toBeInTheDocument();
  });

  it("calls onClose when close button clicked", async () => {
    listPDFs.mockResolvedValue([]);

    const onClose = vi.fn();

    render(
      <Sidebar
        isMobile={true}
        isOpen={true}
        onClose={onClose}
      />
    );

    await userEvent.click(
      screen.getByLabelText(
        "Close PDFs sidebar"
      )
    );

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders notification after duplicate upload", async () => {
    listPDFs.mockResolvedValue([]);

    uploadPDF.mockResolvedValue({
      duplicate: true,
      message: "Already uploaded",
    });

    const { container } = render(<Sidebar />);

    const input = container.querySelector(
      'input[type="file"]'
    );

    const file = new File(
      ["abc"],
      "AI.pdf",
      {
        type: "application/pdf",
      }
    );

    await userEvent.upload(input, file);

    await waitFor(() => {
      expect(
        screen.getByText("Already uploaded")
      ).toBeInTheDocument();
    });
  });

  it("renders uploaded notification", async () => {
    listPDFs.mockResolvedValue([]);

    uploadPDF.mockResolvedValue({
      id: 1,
      filename: "AI.pdf",
      status: "processing",
    });

    const { container } = render(<Sidebar />);

    const input = container.querySelector(
      'input[type="file"]'
    );

    const file = new File(
      ["abc"],
      "AI.pdf",
      {
        type: "application/pdf",
      }
    );

    await userEvent.upload(input, file);

    await waitFor(() => {
      expect(
        screen.getByText(/Indexing/i)
      ).toBeInTheDocument();
    });
  });
});