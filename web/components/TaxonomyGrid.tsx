import { TAXONOMY } from "@/lib/labels";
import { Icon } from "./icons";

export function TaxonomyGrid() {
  return (
    <div className="mt-8 grid grid-cols-2 gap-x-6 gap-y-7 sm:grid-cols-3 lg:grid-cols-4">
      {TAXONOMY.map((item, i) => (
        <div key={item.key} className="flex items-start gap-3.5">
          <span className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-[10px] bg-block text-paper">
            <Icon name={item.key} className="h-[22px] w-[22px]" />
            <span className="absolute -right-1.5 -top-1.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-accent px-1 font-mono text-micro leading-none text-paper">
              {i + 1}
            </span>
          </span>
          <div>
            <p className="font-serif text-ui leading-snug">{item.label}</p>
            <p className="mt-0.5 text-small leading-snug text-muted">{item.blurb}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
