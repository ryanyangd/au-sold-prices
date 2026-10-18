import type { Metadata } from "next";
import { PropertyView } from "@/components/property/PropertyView";
import { container } from "@/lib/ui";

export const metadata: Metadata = { title: "Property sold-price analytics" };

export default async function PropertyPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className={`${container} py-8`}>
      <PropertyView id={decodeURIComponent(id)} />
    </div>
  );
}
