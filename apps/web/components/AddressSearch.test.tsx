import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AddressResult } from "@/lib/types";
import { AddressSearch } from "./AddressSearch";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

function result(n: number, address = `${n} Example St`): AddressResult {
  return {
    property_id: `900-10000${n}`,
    address,
    suburb: "Exampleville",
    postcode: "2000",
    state: "NSW",
    property_type: "house",
    display: `${address}, Exampleville NSW 2000`,
    last_sale_price: 437000 + n,
    last_sale_date: "2018-12-04",
  };
}

const flush = (ms: number) => act(async () => vi.advanceTimersByTimeAsync(ms));

function setup(search = vi.fn().mockResolvedValue([result(1), result(2), result(3)]), onSelect?: () => void) {
  const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
  render(<AddressSearch search={search} onSelect={onSelect} />);
  return { user, search, input: screen.getByRole("combobox") };
}

beforeEach(() => {
  vi.useFakeTimers();
  push.mockClear();
});
afterEach(() => vi.useRealTimers());

describe("AddressSearch debounce and minimum characters", () => {
  it("does not search below 3 characters", async () => {
    const { user, search, input } = setup();
    await user.type(input, "ab");
    await flush(1000);
    expect(search).not.toHaveBeenCalled();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("debounces by 150ms and searches once with the final text", async () => {
    const { user, search, input } = setup();
    await user.type(input, "exam");
    await flush(149);
    expect(search).not.toHaveBeenCalled();
    await flush(1);
    expect(search).toHaveBeenCalledTimes(1);
    expect(search.mock.calls[0]?.[0]).toBe("exam");
    expect(await screen.findAllByRole("option")).toHaveLength(3);
  });

  it("shows loading, then empty and error states", async () => {
    let resolve!: (v: AddressResult[]) => void;
    const search = vi.fn().mockReturnValue(new Promise<AddressResult[]>((r) => (resolve = r)));
    const { user, input } = setup(search);
    await user.type(input, "zzz");
    await flush(150);
    expect(screen.getByText("Searching…")).toBeInTheDocument();
    await act(async () => resolve([]));
    expect(screen.getByText("No matching addresses found.")).toBeInTheDocument();
  });

  it("shows an error with retry", async () => {
    const search = vi.fn().mockRejectedValueOnce(new Error("boom")).mockResolvedValue([result(1)]);
    const { user, input } = setup(search);
    await user.type(input, "exam");
    await flush(150);
    expect(screen.getByRole("alert")).toHaveTextContent("Couldn’t load suggestions.");
    await user.click(screen.getByRole("button", { name: "Retry" }));
    await flush(150);
    expect(await screen.findByRole("option")).toBeInTheDocument();
  });
});

describe("AddressSearch highlighting", () => {
  it("highlights typed letters case-insensitively", async () => {
    const { user, input } = setup(vi.fn().mockResolvedValue([result(12, "12 Example St")]));
    await user.type(input, "12 exa");
    await flush(150);
    const marks = screen.getAllByText((_, el) => el?.tagName === "MARK").map((m) => m.textContent);
    // address line and suburb line both match "exa"
    expect(marks).toEqual(["12", "Exa", "Exa"]);
  });
});

describe("AddressSearch keyboard navigation", () => {
  it("moves with arrows/home/end, selects with Enter and closes with Escape", async () => {
    const onSelect = vi.fn();
    const { user, input } = setup(undefined, onSelect);
    await user.type(input, "exam");
    await flush(150);
    const options = await screen.findAllByRole("option");

    expect(input).toHaveAttribute("aria-expanded", "true");
    await user.keyboard("{ArrowDown}");
    expect(options[0]).toHaveAttribute("aria-selected", "true");
    expect(input).toHaveAttribute("aria-activedescendant", options[0]!.id);

    await user.keyboard("{ArrowDown}");
    expect(options[1]).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{ArrowUp}");
    expect(options[0]).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{ArrowUp}"); // wraps to last
    expect(options[2]).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{Home}");
    expect(options[0]).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{End}");
    expect(options[2]).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ property_id: "900-100003" }));
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("closes on Escape and navigates to the property on click by default", async () => {
    const { user, input } = setup();
    await user.type(input, "exam");
    await flush(150);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(input).toHaveAttribute("aria-expanded", "false");

    await user.keyboard("{ArrowDown}");
    const options = await screen.findAllByRole("option");
    await user.click(options[1]!);
    expect(push).toHaveBeenCalledWith("/property/900-100002");
  });
});

describe("AddressSearch stale responses", () => {
  function deferred() {
    let resolve!: (v: AddressResult[]) => void;
    const promise = new Promise<AddressResult[]>((r) => (resolve = r));
    return { promise, resolve };
  }

  it("ignores an older response that resolves after a newer one", async () => {
    const first = deferred();
    const second = deferred();
    const search = vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const { user, input } = setup(search);

    await user.type(input, "abc");
    await flush(150);
    await user.type(input, "d");
    await flush(150);
    expect(search).toHaveBeenCalledTimes(2);
    expect((search.mock.calls[0]?.[1] as AbortSignal).aborted).toBe(true);

    await act(async () => second.resolve([result(2, "2 Newer St")]));
    await act(async () => first.resolve([result(1, "1 Older St")]));

    const options = screen.getAllByRole("option");
    expect(options).toHaveLength(1);
    expect(options[0]).toHaveTextContent("Newer St");
    expect(screen.queryByText(/Older St/)).not.toBeInTheDocument();
  });

  it("drops an in-flight response when the input falls below 3 characters", async () => {
    const first = deferred();
    const { user, input } = setup(vi.fn().mockReturnValue(first.promise));
    await user.type(input, "abc");
    await flush(150);
    await user.clear(input);
    await act(async () => first.resolve([result(1)]));
    expect(screen.queryByRole("option")).not.toBeInTheDocument();
  });
});
