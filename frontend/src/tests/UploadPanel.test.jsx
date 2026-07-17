import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import UploadButton from "../components/UploadButton";

describe("UploadButton Component", () => {
  it("renders upload label", () => {
    render(<UploadButton onUpload={vi.fn()} disabled={false} />);

    expect(screen.getByText("Upload PDF")).toBeInTheDocument();
  });

  it("renders hidden file input", () => {
    const { container } = render(
      <UploadButton onUpload={vi.fn()} disabled={false} />
    );

    const input = container.querySelector('input[type="file"]');

    expect(input).toBeInTheDocument();
    expect(input.accept).toBe(".pdf");
  });

  it("calls onUpload when a PDF is selected", async () => {
    const onUpload = vi.fn().mockResolvedValue();
    const { container } = render(
      <UploadButton onUpload={onUpload} disabled={false} />
    );

    const input = container.querySelector('input[type="file"]');

    const file = new File(["dummy"], "test.pdf", {
      type: "application/pdf",
    });

    fireEvent.change(input, {
      target: {
        files: [file],
      },
    });

    await waitFor(() => {
      expect(onUpload).toHaveBeenCalledTimes(1);
    });

    expect(onUpload).toHaveBeenCalledWith(file);
  });

  it("does nothing when no file is selected", () => {
    const onUpload = vi.fn();

    const { container } = render(
      <UploadButton onUpload={onUpload} disabled={false} />
    );

    const input = container.querySelector('input[type="file"]');

    fireEvent.change(input, {
      target: {
        files: [],
      },
    });

    expect(onUpload).not.toHaveBeenCalled();
  });

  it("disables input when disabled prop is true", () => {
    const { container } = render(
      <UploadButton onUpload={vi.fn()} disabled={true} />
    );

    const input = container.querySelector('input[type="file"]');

    expect(input.disabled).toBe(true);
  });

  it("shows Limit Reached when disabled", () => {
    render(<UploadButton onUpload={vi.fn()} disabled={true} />);

    expect(screen.getByText("Limit Reached")).toBeInTheDocument();
  });

  it("shows Uploading while upload is in progress", async () => {
    let resolveUpload;

    const promise = new Promise((resolve) => {
      resolveUpload = resolve;
    });

    const onUpload = vi.fn(() => promise);

    const { container } = render(
      <UploadButton onUpload={onUpload} disabled={false} />
    );

    const input = container.querySelector('input[type="file"]');

    const file = new File(["abc"], "demo.pdf", {
      type: "application/pdf",
    });

    fireEvent.change(input, {
      target: {
        files: [file],
      },
    });

    expect(screen.getByText("Uploading...")).toBeInTheDocument();

    resolveUpload();

    await waitFor(() => {
      expect(
        screen.getByText("Upload PDF")
      ).toBeInTheDocument();
    });
  });

  it("resets after upload finishes", async () => {
    const onUpload = vi.fn().mockResolvedValue();

    const { container } = render(
      <UploadButton onUpload={onUpload} disabled={false} />
    );

    const input = container.querySelector('input[type="file"]');

    const file = new File(["pdf"], "doc.pdf", {
      type: "application/pdf",
    });

    fireEvent.change(input, {
      target: {
        files: [file],
      },
    });

    await waitFor(() => {
      expect(
        screen.getByText("Upload PDF")
      ).toBeInTheDocument();
    });
  });
});