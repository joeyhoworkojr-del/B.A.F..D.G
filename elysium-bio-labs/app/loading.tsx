import { BrandLoader } from "@/components/ui/brand-loader";

export default function Loading() {
  return (
    <div className="pt-[var(--header-height)]">
      <BrandLoader />
    </div>
  );
}
