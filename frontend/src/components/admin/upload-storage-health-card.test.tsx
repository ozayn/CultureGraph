import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { UploadStorageHealthCard } from "@/components/admin/upload-storage-health-card";
import type { AdminUploadHealth } from "@/lib/admin-types";

const persistentHealth: AdminUploadHealth = {
  upload_dir: "/app/uploads",
  storage_backend: "filesystem",
  persistent: true,
  missing_count: 0,
  missing_record_count: 0,
  records: [],
};

const ephemeralHealth: AdminUploadHealth = {
  upload_dir: "/tmp/uploads",
  storage_backend: "filesystem",
  persistent: false,
  missing_count: 2,
  missing_record_count: 1,
  records: [
    {
      record_type: "artwork",
      record_id: 12,
      field: "image_url",
      path: "/uploads/artworks/12/display.webp",
      label: "Test artwork",
    },
  ],
};

describe("UploadStorageHealthCard", () => {
  it("shows upload storage fields", () => {
    render(<UploadStorageHealthCard health={persistentHealth} />);

    expect(screen.getByRole("heading", { name: "Upload storage" })).toBeInTheDocument();
    expect(screen.getByText("/app/uploads")).toBeInTheDocument();
    expect(screen.getByText("filesystem")).toBeInTheDocument();
    expect(screen.getByText("true")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
  });

  it("warns when storage is not persistent", () => {
    render(<UploadStorageHealthCard health={ephemeralHealth} />);

    expect(screen.getByText(/not on a persistent volume/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Clear missing file references" })).toBeInTheDocument();
    expect(screen.getByText("false")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });
});
